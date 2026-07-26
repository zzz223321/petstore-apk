from flask import Blueprint, request, jsonify, render_template, send_from_directory
from db import get_db
import uuid
from datetime import datetime

api = Blueprint('api', __name__)

@api.route('/')
def index():
    return render_template('index.html')

# 静态文件（用于 PWA）
@api.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('templates', filename)

# ---------- 商品 ----------
@api.route('/api/products', methods=['GET'])
def get_products():
    db = get_db()
    rows = db.execute("SELECT * FROM products").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d['type'] == 'pet':
            cnt = db.execute("SELECT COUNT(*) FROM pet_individuals WHERE product_id=? AND status='在售'", (d['id'],)).fetchone()[0]
            d['stock_qty'] = cnt
        elif d['type'] == 'service':
            d['stock_qty'] = '-'
        result.append(d)
    return jsonify(result)

@api.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    db = get_db()
    db.execute("INSERT INTO products (name,type,barcode,category,cost_price,selling_price,unit,stock_qty,note) VALUES (?,?,?,?,?,?,?,?,?)",
               (data['name'], data['type'], data.get('barcode'), data.get('category'),
                data.get('cost_price', 0), data['selling_price'], data.get('unit', '个'),
                data.get('stock_qty', 0) if data['type'] == 'goods' else 0, data.get('note')))
    db.commit()
    return jsonify({'msg': 'ok'}), 201

@api.route('/api/products/<int:pid>', methods=['PUT'])
def update_product(pid):
    data = request.json
    db = get_db()
    db.execute("UPDATE products SET name=?,type=?,barcode=?,category=?,cost_price=?,selling_price=?,unit=?,stock_qty=?,note=? WHERE id=?",
               (data['name'], data['type'], data.get('barcode'), data.get('category'),
                data.get('cost_price', 0), data['selling_price'], data.get('unit', '个'),
                data.get('stock_qty', 0) if data['type'] == 'goods' else 0, data.get('note'), pid))
    db.commit()
    return jsonify({'msg': 'updated'})

@api.route('/api/products/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    db = get_db()
    db.execute("DELETE FROM products WHERE id=?", (pid,))
    db.commit()
    return jsonify({'msg': 'deleted'})

# ---------- 会员 ----------
@api.route('/api/members', methods=['GET'])
def get_members():
    db = get_db()
    rows = db.execute("SELECT id,name,phone,balance,points,level FROM members").fetchall()
    return jsonify([dict(r) for r in rows])

@api.route('/api/members', methods=['POST'])
def add_member():
    data = request.json
    db = get_db()
    try:
        db.execute("INSERT INTO members (name,phone) VALUES (?,?)", (data['name'], data['phone']))
        db.commit()
        return jsonify({'msg': 'ok'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': '手机号已存在'}), 400

@api.route('/api/members/<int:mid>/recharge', methods=['POST'])
def recharge(mid):
    amount = request.json.get('amount', 0)
    db = get_db()
    db.execute("UPDATE members SET balance=balance+? WHERE id=?", (amount, mid))
    db.commit()
    return jsonify({'msg': '充值成功'})

@api.route('/api/members/<int:mid>/pets', methods=['GET'])
def get_member_pets(mid):
    db = get_db()
    pets = db.execute("SELECT id, name, breed, birth, notes FROM member_pets WHERE member_id=?", (mid,)).fetchall()
    return jsonify([dict(p) for p in pets])

@api.route('/api/members/<int:mid>/pets', methods=['POST'])
def bind_pet(mid):
    data = request.json
    db = get_db()
    db.execute("INSERT INTO member_pets (member_id,name,breed,birth,notes) VALUES (?,?,?,?,?)",
               (mid, data['name'], data.get('breed'), data.get('birth'), data.get('notes')))
    db.commit()
    return jsonify({'msg': '宠物绑定成功'}), 201

@api.route('/api/members/<int:mid>/pets/<int:pid>', methods=['DELETE'])
def delete_member_pet(mid, pid):
    db = get_db()
    pet = db.execute("SELECT id FROM member_pets WHERE id=? AND member_id=?", (pid, mid)).fetchone()
    if not pet:
        return jsonify({'error': '宠物不存在或不属于该会员'}), 404
    db.execute("DELETE FROM member_pets WHERE id=?", (pid,))
    db.commit()
    return jsonify({'msg': '删除成功'})

# ---------- 活体 ----------
@api.route('/api/pet_individuals', methods=['GET'])
def get_pets():
    db = get_db()
    rows = db.execute("SELECT * FROM pet_individuals").fetchall()
    return jsonify([dict(r) for r in rows])

@api.route('/api/pet_individuals', methods=['POST'])
def add_pet():
    data = request.json
    db = get_db()
    db.execute("INSERT INTO pet_individuals (product_id,chip_no,birthday,gender,color,vaccine_date,cost_price,selling_price,note) VALUES (?,?,?,?,?,?,?,?,?)",
               (data['product_id'], data.get('chip_no'), data.get('birthday'), data.get('gender','未知'),
                data.get('color'), data.get('vaccine_date'), data.get('cost_price',0), data.get('selling_price',0), data.get('note')))
    db.commit()
    return jsonify({'msg': 'ok'}), 201

@api.route('/api/pet_individuals/<int:pid>/status', methods=['PUT'])
def update_pet_status(pid):
    new_status = request.json.get('status')
    db = get_db()
    db.execute("UPDATE pet_individuals SET status=? WHERE id=?", (new_status, pid))
    db.commit()
    return jsonify({'msg': '状态已更新'})

# ---------- 销售 ----------
@api.route('/api/sale', methods=['POST'])
def create_sale():
    data = request.json
    items = data.get('items', [])
    member_phone = data.get('member_phone')
    discount = data.get('discount', 0)
    payment = data.get('payment', '现金')

    if not items:
        return jsonify({'error': '购物车为空'}), 400

    db = get_db()
    member = None
    if member_phone:
        member = db.execute("SELECT id,name,balance FROM members WHERE phone=?", (member_phone,)).fetchone()
        if not member:
            return jsonify({'error': '会员不存在'}), 400

    total = sum(item['qty'] * item['price'] for item in items)
    paid = total - discount
    if paid < 0:
        return jsonify({'error': '折扣不能大于总金额'}), 400

    if payment == '会员余额':
        if not member:
            return jsonify({'error': '余额支付需选择会员'}), 400
        if member['balance'] < paid:
            return jsonify({'error': '会员余额不足'}), 400

    order_no = datetime.now().strftime('%Y%m%d%H%M%S') + str(uuid.uuid4())[:6]
    try:
        for item in items:
            prod = db.execute("SELECT type,stock_qty FROM products WHERE id=?", (item['product_id'],)).fetchone()
            if prod['type'] == 'goods':
                if prod['stock_qty'] < item['qty']:
                    return jsonify({'error': f"商品 {prod['id']} 库存不足"}), 400
                new_qty = prod['stock_qty'] - item['qty']
                db.execute("UPDATE products SET stock_qty=? WHERE id=?", (new_qty, item['product_id']))
                db.execute("INSERT INTO inventory_logs (product_id,change_qty,type,before_qty,after_qty) VALUES (?,?,?,?,?)",
                           (item['product_id'], -item['qty'], '销售出库', prod['stock_qty'], new_qty))
            elif prod['type'] == 'pet':
                db.execute("UPDATE pet_individuals SET status='已售' WHERE id=?", (item['pet_individual_id'],))

        if payment == '会员余额':
            db.execute("UPDATE members SET balance=balance-? WHERE id=?", (paid, member['id']))

        db.execute("INSERT INTO sales_orders (order_no,member_id,total_amount,discount,paid_amount,payment_method) VALUES (?,?,?,?,?,?)",
                   (order_no, member['id'] if member else None, total, discount, paid, payment))
        order_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        for item in items:
            db.execute("INSERT INTO sale_items (order_id,product_id,pet_individual_id,quantity,unit_price,subtotal) VALUES (?,?,?,?,?,?)",
                       (order_id, item['product_id'], item.get('pet_individual_id'), item['qty'], item['price'], item['qty']*item['price']))
        db.commit()
        return jsonify({'order_no': order_no, 'paid': paid})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

# ---------- 库存 ----------
@api.route('/api/inventory', methods=['GET'])
def get_inventory():
    db = get_db()
    rows = db.execute("SELECT id,name,type,stock_qty FROM products").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d['type'] == 'pet':
            cnt = db.execute("SELECT COUNT(*) FROM pet_individuals WHERE product_id=? AND status='在售'", (d['id'],)).fetchone()[0]
            d['stock_qty'] = cnt
        elif d['type'] == 'service':
            d['stock_qty'] = '-'
        result.append(d)
    return jsonify(result)

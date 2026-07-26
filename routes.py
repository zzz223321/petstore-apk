from flask import Blueprint, request, jsonify, render_template, send_from_directory
from db import get_db
import sqlite3
from datetime import datetime

api = Blueprint('api', __name__)

@api.route('/')
def index():
    return render_template('index.html')

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

@api.route('/api/members/search', methods=['GET'])
def search_member():
    phone = request.args.get('phone')
    if not phone:
        return jsonify({'error': '缺少手机号'}), 400
    db = get_db()
    member = db.execute("SELECT id,name,phone,balance,points,level FROM members WHERE phone=?", (phone,)).fetchone()
    if member:
        return jsonify(dict(member))
    return jsonify(None), 404

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

@api.route('/api/inventory/adjust', methods=['POST'])
def adjust_inventory():
    data = request.json
    product_id = data.get('product_id')
    change_qty = data.get('change_qty')
    type_str = data.get('type', '入库')

    if not product_id or change_qty is None:
        return jsonify({'error': '缺少参数'}), 400

    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        return jsonify({'error': '商品不存在'}), 404
    if product['type'] != 'goods':
        return jsonify({'error': '只能调整普通商品的库存'}), 400

    new_qty = product['stock_qty'] + change_qty
    if new_qty < 0:
        return jsonify({'error': '库存不足，不能出库'}), 400

    db.execute("UPDATE products SET stock_qty=? WHERE id=?", (new_qty, product_id))
    db.execute("INSERT INTO inventory_logs (product_id, change_qty, type, before_qty, after_qty) VALUES (?,?,?,?,?)",
               (product_id, change_qty, type_str, product['stock_qty'], new_qty))
    db.commit()
    return jsonify({'msg': '库存调整成功', 'new_qty': new_qty})

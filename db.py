import sqlite3
from flask import g
from config import DATABASE

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT CHECK(type IN ('goods','pet','service')) NOT NULL DEFAULT 'goods',
            barcode TEXT UNIQUE,
            category TEXT,
            cost_price REAL,
            selling_price REAL NOT NULL,
            unit TEXT DEFAULT '个',
            stock_qty INTEGER DEFAULT 0,
            note TEXT
        );
        CREATE TABLE IF NOT EXISTS pet_individuals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            chip_no TEXT UNIQUE,
            birthday TEXT,
            gender TEXT CHECK(gender IN ('公','母','未知')) DEFAULT '未知',
            color TEXT,
            vaccine_date TEXT,
            status TEXT CHECK(status IN ('在售','已售','死亡','退回')) DEFAULT '在售',
            cost_price REAL,
            selling_price REAL,
            note TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            balance REAL DEFAULT 0,
            points INTEGER DEFAULT 0,
            level TEXT DEFAULT '普通',
            join_date TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS member_pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            breed TEXT,
            birth TEXT,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id)
        );
        CREATE TABLE IF NOT EXISTS sales_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE NOT NULL,
            member_id INTEGER,
            total_amount REAL NOT NULL,
            discount REAL DEFAULT 0,
            paid_amount REAL NOT NULL,
            payment_method TEXT CHECK(payment_method IN ('现金','微信','支付宝','会员余额','混合')) DEFAULT '现金',
            cashier TEXT DEFAULT 'admin',
            sale_time TEXT DEFAULT (datetime('now','localtime')),
            remark TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id)
        );
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            pet_individual_id INTEGER,
            quantity REAL NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES sales_orders(id)
        );
        CREATE TABLE IF NOT EXISTS inventory_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            change_qty REAL NOT NULL,
            type TEXT CHECK(type IN ('入库','销售出库','报损','盘点')) NOT NULL,
            ref_order_id INTEGER,
            before_qty REAL,
            after_qty REAL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
    ''')
    db.commit()
    db.close()
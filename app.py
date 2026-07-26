from flask import Flask
from db import init_db, close_db
from routes import api
import os

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    app.teardown_appcontext(close_db)
    app.register_blueprint(api)

    # 检查数据库是否存在，不存在则初始化
    if not os.path.exists(app.config['DATABASE']):
        with app.app_context():
            init_db()
    return app

if __name__ == '__main__':
    application = create_app()
    application.run(host='0.0.0.0', port=5000, debug=True)
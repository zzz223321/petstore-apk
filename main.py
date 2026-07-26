import threading
import time
from android import Android
from app import create_app

def start_flask():
    app = create_app()
    app.run(host='127.0.0.1', port=5000, debug=False)

def open_browser():
    time.sleep(3)
    android = Android()
    android.start_activity('android.intent.action.VIEW', 'http://127.0.0.1:5000')

if __name__ == '__main__':
    threading.Thread(target=start_flask, daemon=True).start()
    threading.Thread(target=open_browser, daemon=True).start()
    # 保持主线程活着
    while True:
        time.sleep(1)

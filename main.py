import threading
import webview
from app import create_app

def start_flask():
    application = create_app()
    application.run(host='127.0.0.1', port=5000, debug=False)

if __name__ == '__main__':
    threading.Thread(target=start_flask, daemon=True).start()
    webview.create_window('宠物店管家', 'http://127.0.0.1:5000')
    webview.start()

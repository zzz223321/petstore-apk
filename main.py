import threading
from flask import Flask
from app import create_app

# Kivy 相关
from kivy.app import App
from kivy_garden.xwalk import XWalkView
from kivy.clock import Clock

class PetStoreApp(App):
    def build(self):
        # 启动 Flask 服务器（后台线程）
        threading.Thread(target=self.run_flask, daemon=True).start()
        self.webview = XWalkView()
        return self.webview

    def run_flask(self):
        application = create_app()
        application.run(host='127.0.0.1', port=5000, debug=False)

    def on_start(self):
        # 等待 3 秒后加载网页（确保 Flask 已完全启动）
        Clock.schedule_once(lambda dt: self.webview.load_url('http://127.0.0.1:5000'), 3)

if __name__ == '__main__':
    PetStoreApp().run()
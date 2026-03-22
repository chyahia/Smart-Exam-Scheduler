from app import create_app
import webbrowser
import threading
import time

app = create_app()

def open_browser():
    # ننتظر ثانية واحدة حتى يشتغل السيرفر ثم نفتح المتصفح على المنفذ الجديد
    time.sleep(1)
    webbrowser.open('http://127.0.0.1:8000') # 👈 التعديل الأول هنا

if __name__ == '__main__':
    # تشغيل أمر فتح المتصفح في خيط منفصل
    threading.Thread(target=open_browser).start()
    
    # 🔴 إيقاف وضع التطوير وتغيير المنفذ إلى 8000
    app.run(debug=False, port=8000) # 👈 التعديل الثاني هنا
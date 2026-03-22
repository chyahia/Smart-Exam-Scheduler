# 🎓 موزع حراسة الامتحانات الذكي (Smart Exam Scheduler)

نظام ويب متقدم ومستقل (Standalone Web-App) مبني بلغة بايثون، يهدف إلى أتمتة وتحسين عملية توزيع الأساتذة على حراسة الامتحانات في الجامعات والمدارس. يعتمد النظام على خوارزميات الذكاء الاصطناعي وبحوث العمليات لحل مشكلة الجدولة المعقدة مع مراعاة القيود الصارمة والمرنة وتحقيق أعلى درجات العدالة في توزيع الأعباء.

## ✨ الميزات الرئيسية (Key Features)

* **⚙️ معمارية خط التجميع (Pipeline Architecture):** يتيح النظام تشغيل سلسلة من الخوارزميات بشكل متسلسل للوصول إلى الحل الأمثل.
* **🧠 خوارزميات تحسين متقدمة (Meta-heuristics):**
  * **LNS (البحث الجواري الواسع):** يعمل كـ "بلدوزر" للتعامل مع النقص الحاد في الحراس وجبره بسرعة فائقة.
  * **VNS (البحث الجواري المتغير) & Tabu Search (البحث المحظور):** تعمل كـ "مشرط جراحي" للضبط الدقيق وتقليل تشتت الأيام والانحراف في العبء بين الأساتذة.
* **🎯 تحسين مرحلي (Phased Optimization):** الخوارزميات مبرمجة لترتيب الأولويات بصرامة معجمية (Strict Lexicographic)؛ حيث تصب تركيزها أولاً على سد النقص، وبمجرد حله، تنتقل تلقائياً لتحقيق العدالة (تقليل الانحراف).
* **💾 قاعدة بيانات هجينة وذكية:** النظام مصمم ليعمل كبرنامج محمول (Portable) أو مثبت (Installable)، مع توجيه تلقائي لملف قاعدة البيانات (`SQLite`) إلى مسار `AppData\Roaming` في بيئات ويندوز المحمية لتجنب أخطاء الصلاحيات.
* **📊 التصدير والتقارير:** إمكانية تصدير الجداول النهائية منسقة وجاهزة للطباعة بصيغ `Excel` و `Word`.
* **🖥️ واجهة مستخدم تفاعلية (Live Monitoring):** واجهة ويب تتيح للمستخدم مراقبة عمل الخوارزميات في الوقت الفعلي ومتابعة انخفاض التكلفة (Cost Function) دورة بدورة.

## 🛠️ التقنيات المستخدمة (Tech Stack)

* **اللغة الأساسية:** Python 3
* **إطار عمل الويب:** Flask
* **قاعدة البيانات:** SQLite3
* **تحليل ومعالجة البيانات:** Pandas
* **التعامل مع الملفات (تصدير):** Openpyxl (Excel), Python-docx (Word)
* **واجهة المستخدم:** HTML5, CSS3, Vanilla JavaScript
* **التحزيم والتوزيع:** PyInstaller, Inno Setup

## 🚀 طريقة التشغيل للمطورين (How to Run Locally)

1. **استنساخ المستودع (Clone the repository):**
   ```bash
   git clone [https://github.com/YourUsername/Smart-Exam-Scheduler.git](https://github.com/YourUsername/Smart-Exam-Scheduler.git)
   cd Smart-Exam-Scheduler

2. إنشاء البيئة الوهمية وتفعيلها:
   ```bash
python -m venv venv

# في نظام ويندوز:
venv\Scripts\activate

3. تثبيت المتطلبات:
   ```bash
pip install Flask pandas openpyxl python-docx pyinstaller

4. تشغيل النظام:
   ```bash
python run.py

سيفتح المتصفح تلقائياً على الرابط http://127.0.0.1:8000.

📦 بناء النسخة التنفيذية (Building the .exe)
لتحويل المشروع إلى ملف تنفيذي واحد لا يحتاج إلى تثبيت بايثون:
   ```bash
pyinstaller --onedir --noconsole --icon=icon.ico --add-data "app/templates;app/templates" --add-data "app/static;app/static" --hidden-import pandas --hidden-import openpyxl --hidden-import docx run.py

🤝 المساهمة (Contributing)
الطلبات والمقترحات (Pull Requests) مرحب بها. للتحسينات الكبيرة، يرجى فتح Issue أولاً لمناقشة ما تود تغييره.

تم تطوير هذا المشروع لتسهيل الإدارة الأكاديمية.
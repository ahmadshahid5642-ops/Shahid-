import telebot
from telebot import types
import sqlite3
import time
import secrets
import string

# اطلاعات اصلی ربات
BOT_TOKEN = "8775289783:AAHlH3Kd3g6wyQpklNB8ok5LHcED0nxLIFo"
ADMIN_ID = 7575502917

bot = telebot.TeleBot(BOT_TOKEN)

# تابع تولید کد دعوت اختصاصی ۱۵ کاراکتری مخلوط حروف و اعداد
def generate_ref_code():
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(15))

# ساخت و تنظیم دیتابیس
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, 
                       lang TEXT, 
                       step TEXT, 
                       coins INTEGER DEFAULT 0, 
                       ref_code TEXT UNIQUE,
                       referred_by INTEGER DEFAULT 0,
                       transfer_target INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# توابع مدیریت دیتابیس
def get_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT lang, step, coins, ref_code, referred_by, transfer_target FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"lang": row[0], "step": row[1], "coins": row[2], "ref_code": row[3], "referred_by": row[4], "transfer_target": row[5]}
    return None

def add_user(user_id, referrer_code=None):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()
    
    is_new_user = False
    if not exists:
        is_new_user = True
        new_ref_code = generate_ref_code()
        
        referred_by_id = 0
        if referrer_code:
            cursor.execute("SELECT user_id FROM users WHERE ref_code = ?", (referrer_code,))
            ref_owner = cursor.fetchone()
            if ref_owner and ref_owner[0] != user_id:
                referred_by_id = ref_owner[0]
                
        cursor.execute("INSERT INTO users (user_id, lang, step, coins, ref_code, referred_by) VALUES (?, ?, ?, ?, ?, ?)", 
                       (user_id, None, 'none', 0, new_ref_code, referred_by_id))
        
        if referred_by_id > 0:
            cursor.execute("UPDATE users SET coins = coins + 1 WHERE user_id = ?", (referred_by_id,))
            try:
                bot.send_message(referred_by_id, f"🔔 یک کاربر جدید با لینک دعوت شما وارد ربات شد!\n💰 ۱ سکه به حساب شما اضافه گردید.")
            except Exception:
                pass
            
    conn.commit()
    conn.close()
    return is_new_user

def update_user_lang(user_id, lang):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET lang = ?, step = 'none' WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()

def update_user_step(user_id, step):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET step = ? WHERE user_id = ?", (step, user_id))
    conn.commit()
    conn.close()

def update_user_transfer_target(user_id, target_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET transfer_target = ? WHERE user_id = ?", (target_id, user_id))
    conn.commit()
    conn.close()

def change_coins(user_id, amount):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

# متون ربات با فونت درخواستی شما و تصحیح کلمه حساب
TEXTS = {
    'prs': {
        'start': "(▼سݪام▼メ)\n\nبه ࢪبات خوش امدید {name}\n\nایدی عددی شما : {id}\n\nبࢪای استفاده از ࢪبات ݪطفا از مینو زیࢪ استفاده ڪنید",
        'btn_report': "𓆩? ࢪیپورت واتساپ?𓆪",
        'btn_unban': "𓆩? ࢪفع بند واتساپ?𓆪",
        'btn_send_coins': "メ▼اࢪساݪ سڪه▼メ",
        'btn_support': "⎋پشتیبانی✓",
        'btn_info': "メ▼معلومات من▼メ",
        'info_text': "اسم شما : {name}\n\nآیدی عددی شما : {id}\n\nسکه های شما : {coins}\n\nلینک دعوت شما :\n{link}\n\nاین لینک دعوت شماست با هر دعوت یک سکه به حساب اضافه می‌شود ✅\nبا دعوت بیشتر سکه بیشتر به دست بیاور",
        'old_user_err': "メ▼ سݪام▼メ\n\nشما ربات را از سابق استارت کرده اذید و بالای شما لینک دعوت کار میکند \n\nبه ربات خوش آمدید ✅ \n\nبرای استفاده از ربات /start کنید ❗",
        'no_coins': "❌ برای استفاده از این بخش نیاز به حداقل ۱۵ سکه دارید!\n💡 سکه های فعلی شما: {coins}\nشما می توانید با زیرمجموعه گیری سکه رایگان جمع آوری کنید.",
        'ask_num': "ݪطفا شࢪماࢪه موࢪد نظࢪ ࢪا با ڪود ڪشوࢪ واࢪد ڪنید (مثال: +937xxxxxxxxx):",
        'ask_num_unban': "شماࢪه ڪه میخاهید ࢪفع ڪنید بفࢪستید (فࢪقی نداࢪ بند ساده یا دایمی باشد):",
        'reporting': "شماره دریافت شد در حال گزارش 🆘\nلطفا منتظر بمانید.....\n\n📊 پیشرفت: {count}/150 گزارش ارسال شد",
        'unbanning': "دࢪ حاݪ ࢪفع بند ڪࢪدن شماࢪه شما دوست عزیز ⚙️\n\n📊 پیشࢪفت: {percent}%",
        'report_success': "✅ بیش از ۱۵۰ گزارش واقعی و ۱۰۰٪ با موفقیت بالای شماره ارسال شد و تحت بررسی قرار گرفت!\n💰 ۱۵ سکه از حساب شما کسر شد. (برای ادمین رایگان)",
        'unban_success': "✅ متن رفع بند تایید شده ۵ بار متوالی با موفقیت به کمپنی واتساپ ارسال شد و پروسه ۱۰۰٪ انجام شد!\n💰 ۱۵ سکه از حساب شما کسر شد. (برای ادمین رایگان)",
        'not_found': "❌ این شماره فارمت اشتباه دارد یا واتساپ ندارد ❗\nلطفا شماره را چک کرده و بعد دوباره امتحان کنید✅",
        'ask_support': "پیام ڪه میخاهید بزای سازنده اࢪساݪ ڪنید ࢪا بفࢪستید",
        'support_sent': "✅ پیام شما بࢪای سازنده اࢪساݪ شد.",
        'ask_transfer_id': "آیدی عددی فࢪد ࢪا بفࢪستید بࢪای اࢪساݪ سڪه:",
        'ask_transfer_amount': "ݪطفا مقداࢪ سڪه موࢪد نظࢪ بࢪای اࢪساݪ ࢪا واࢪد ڪنید:",
        'invalid_id': "❌ آیدی عددی وارد شده اشتباه است یا کاربر در ربات عضو نیست!",
        'invalid_amount': "❌ تعداد سکه وارد شده باید یک عدد معتبر و بیشتر از صفر باشد!",
        'insufficient_coins': "❌ موجودی سکه شما کافی نیست! سکه‌های شما: {coins}",
        'transfer_success_sender': "✅ تعداد {amount} سکه با موفقیت به حساب کاربر {target} ارسال شد.",
        'transfer_success_receiver': "💰 تعداد {amount} سکه از طرف کاربر {sender} به حساب شما واریز شد!",
        'help': "💡 طࢪیقه استفاده از ࢪبات:\n۱- گزینه ࢪیپوࢪت یا رفع بند واتساپ ࢪا انتخاب ڪنید.\n۲- شماره هدف ࢪا با ڪد ڪشور بفࢪستید.\n۳- سیستم به صورت خودکاࢪ کار خود را انجام میدهد.\n\n/language : تغیࢪ زبان ربات"
    },
    'en': {
        'start': "(▼Hello▼メ)\n\nWelcome to the bot {name}\n\nYour ID: {id}\n\nPlease use the menu below to navigate",
        'btn_report': "𓆩? WhatsApp Report ?𓆪",
        'btn_unban': "𓆩? WhatsApp Unban ?𓆪",
        'btn_send_coins': "メ▼ Send Coins ▼メ",
        'btn_support': "⎋ Support ✓",
        'btn_info': "メ▼ My Info ▼メ",
        'info_text': "Name: {name}\n\nYour ID: {id}\n\nYour Coins: {coins}\n\nYour Referral Link:\n{link}\n\nThis is your referral link. Each invite adds 1 coin into your balance ✅\nInvite more to get more coins!",
        'old_user_err': "メ▼ Hello ▼メ\n\nYou are an old user, referral link does not work for you!\n\nWelcome to the bot ✅\n\nTo use the bot type /start ❗",
        'no_coins': "❌ You need at least 15 coins to use this feature!\n💡 Your Coins: {coins}\nYou can invite friends to earn free coins.",
        'ask_num': "Please enter the target number with country code (e.g., +937xxxxxxxxx):",
        'ask_num_unban': "Please enter the number you want to unban (Simple or Permanent ban):",
        'reporting': "Number received, reporting in progress 🆘\nPlease wait.....\n\n📊 Progress: {count}/150 reports sent",
        'unbanning': "Unbanning your number in progress dear friend ⚙️\n\n📊 Progress: {percent}%",
        'report_success': "✅ More than 150 valid reports successfully sent to the number!\n💰 15 coins deducted from your balance. (Free for Admin)",
        'unban_success': "✅ Unban request text successfully sent 5 times to WhatsApp Company!\n💰 15 coins deducted from your balance. (Free for Admin)",
        'not_found': "❌ This number format is invalid or doesn't have WhatsApp ❗",
        'ask_support': "Please send the message you want to forward to the creator",
        'support_sent': "✅ Your message has been sent to the creator.",
        'ask_transfer_id': "Please send the user ID to transfer coins:",
        'ask_transfer_amount': "Please enter the amount of coins to transfer:",
        'invalid_id': "❌ Invalid User ID or user is not registered in the bot!",
        'invalid_amount': "❌ Coin amount must be a valid number greater than zero!",
        'insufficient_coins': "❌ You do not have enough coins! Your Coins: {coins}",
        'transfer_success_sender': "✅ Successfully transferred {amount} coins to user {target}.",
        'transfer_success_receiver': "💰 You have received {amount} coins from user {sender}!",
        'help': "💡 How to use the bot:\n1- Select WhatsApp Report or Unban.\n2- Send the number with country code.\n3- The system will auto-submit the requests.\n\n/language : Change language"
    }
}

# منوی انتخاب زبان
def language_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_prs = types.InlineKeyboardButton("دࢪی 🇦🇫", callback_data="setlang_prs")
    btn_en = types.InlineKeyboardButton("English 🇬🇧", callback_data="setlang_en")
    markup.add(btn_prs, btn_en)
    return markup

# منوی اصلی اینلاین ربات
def main_keyboard(lang):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_rep = types.InlineKeyboardButton(TEXTS[lang]['btn_report'], callback_data="menu_report")
    btn_unb = types.InlineKeyboardButton(TEXTS[lang]['btn_unban'], callback_data="menu_unban")
    btn_snd = types.InlineKeyboardButton(TEXTS[lang]['btn_send_coins'], callback_data="menu_sendcoins")
    btn_info = types.InlineKeyboardButton(TEXTS[lang]['btn_info'], callback_data="menu_info")
    btn_sup = types.InlineKeyboardButton(TEXTS[lang]['btn_support'], callback_data="menu_support")
    
    markup.row(btn_rep)
    markup.row(btn_unb)
    markup.row(btn_snd)
    markup.row(btn_info, btn_sup)
    return markup

# دستور /start و لینک دعوت
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    cmd_parts = message.text.split()
    ref_code = cmd_parts[1] if len(cmd_parts) > 1 else None
    
    is_new = add_user(user_id, ref_code)
    user = get_user(user_id)
    
    if not is_new and ref_code:
        lang = user['lang'] if user['lang'] else 'prs'
        bot.send_message(user_id, TEXTS[lang]['old_user_err'])
        return

    if user['lang'] is None:
        welcome_msg = "ݪطفا زبان خود ࢪا انتخاب ڪنید\nPlease select your language:"
        bot.send_message(user_id, welcome_msg, reply_markup=language_keyboard())
    else:
        lang = user['lang']
        text = TEXTS[lang]['start'].format(name=message.from_user.first_name, id=user_id)
        bot.send_message(user_id, text, reply_markup=main_keyboard(lang))

# دستور /language برای تغییر زبان
@bot.message_handler(commands=['language'])
def change_language(message):
    user_id = message.from_user.id
    welcome_msg = "ݪطفا زبان خود ࢪا انتخاب ڪنید\nPlease select your language:"
    bot.send_message(user_id, welcome_msg, reply_markup=language_keyboard())

# دستور /help
@bot.message_handler(commands=['help'])
def show_help(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    lang = user['lang'] if user and user['lang'] else 'prs'
    bot.send_message(user_id, TEXTS[lang]['help'])

# دستور مدیریت ادمین: ارسال سکه به آیدی عددی
@bot.message_handler(commands=['addcoins'])
def admin_add_coins(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        amount = int(parts[2])
        
        change_coins(target_id, amount)
        bot.reply_to(message, f"✅ تعداد {amount} سکه با موفقیت به حساب کاربر {target_id} اضافه شد.")
        bot.send_message(target_id, f"💰 ادمین تعداد {amount} سکه به حساب شما واریز کرد!")
    except Exception:
        bot.reply_to(message, "❌ دستور اشتباه است. شکل درست:\n`/addcoins 7575502917 15`")

# دستور ادمین: ارسال همگانی /bc
@bot.message_handler(commands=['bc'])
def broadcast_msg(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    msg_text = message.text.replace('/bc', '').strip()
    if not msg_text:
        bot.reply_to(message, "❌ لطفا متن پیام همگانی را بعد از دستور بنویسید.")
        return
        
    users = get_all_users()
    success = 0
    for u_id in users:
        try:
            bot.send_message(u_id, msg_text)
            success += 1
            time.sleep(0.05)
        except Exception:
            pass
    bot.reply_to(message, f"✅ پیام همگانی به {success} کاربر ارسال شد.")

# مدیریت کلیک روی دکمه‌های اینلاین زبان
@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def callback_set_lang(call):
    user_id = call.from_user.id
    selected_lang = call.data.split('_')[1]
    update_user_lang(user_id, selected_lang)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    text = TEXTS[selected_lang]['start'].format(name=call.from_user.first_name, id=user_id)
    bot.send_message(user_id, text, reply_markup=main_keyboard(selected_lang))

# مدیریت کلیک روی دکمه‌های منوی اصلی
@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def callback_menu(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    if not user or not user['lang']:
        return
    
    lang = user['lang']
    action = call.data.split('_')[1]
    
    if action == "report":
        if user_id != ADMIN_ID and user['coins'] < 15:
            bot.send_message(user_id, TEXTS[lang]['no_coins'].format(coins=user['coins']))
            return
        update_user_step(user_id, "waiting_number")
        bot.send_message(user_id, TEXTS[lang]['ask_num'])
        
    elif action == "unban":
        if user_id != ADMIN_ID and user['coins'] < 15:
            bot.send_message(user_id, TEXTS[lang]['no_coins'].format(coins=user['coins']))
            return
        update_user_step(user_id, "waiting_unban_number")
        bot.send_message(user_id, TEXTS[lang]['ask_num_unban'])
        
    elif action == "sendcoins":
        update_user_step(user_id, "waiting_transfer_id")
        bot.send_message(user_id, TEXTS[lang]['ask_transfer_id'])
        
    elif action == "info":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user['ref_code']}"
        info_msg = TEXTS[lang]['info_text'].format(
            name=call.from_user.first_name, id=user_id, coins=user['coins'], link=ref_link
        )
        bot.send_message(user_id, info_msg, reply_markup=main_keyboard(lang))
        
    elif action == "support":
        update_user_step(user_id, "waiting_support")
        bot.send_message(user_id, TEXTS[lang]['ask_support'])

# مدیریت پیام‌های متنی ارسالی کاربران
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user or not user['lang']:
        return
    
    lang = user['lang']
    step = user['step']
    
    if user_id == ADMIN_ID and message.reply_to_message:
        try:
            lines = message.reply_to_message.text.split("\n")
            target_user_id = int(lines[0].split(":")[1].strip())
            bot.send_message(target_user_id, f"📩 پیام جدید از طرف پشتیبانی:\n\n{message.text}")
            bot.reply_to(message, "✅ پاسخ شما برای کاربر ارسال شد.")
        except Exception:
            bot.reply_to(message, "❌ خطا! نتوانستم ایدی کاربر را از ریپلای تشخیص دهم.")
        return

    if step == "waiting_number":
        num = message.text.strip()
        if user_id != ADMIN_ID and user['coins'] < 15:
            bot.send_message(user_id, TEXTS[lang]['no_coins'].format(coins=user['coins']))
            update_user_step(user_id, "none")
            return
        if not num.startswith('+') or len(num) < 10 or not num[1:].isdigit():
            bot.send_message(user_id, TEXTS[lang]['not_found'])
            update_user_step(user_id, "none")
            return
            
        status_msg = bot.send_message(user_id, TEXTS[lang]['reporting'].format(count=0))
        for i in range(25, 151, 25):
            time.sleep(1.0)
            try:
                bot.edit_message_text(chat_id=user_id, message_id=status_msg.message_id, text=TEXTS[lang]['reporting'].format(count=i))
            except Exception: pass
        try: bot.delete_message(user_id, status_msg.message_id)
        except Exception: pass
            
        if user_id != ADMIN_ID: change_coins(user_id, -15)
        bot.send_message(user_id, TEXTS[lang]['report_success'], reply_markup=main_keyboard(lang))
        update_user_step(user_id, "none")

    elif step == "waiting_unban_number":
        num = message.text.strip()
        if user_id != ADMIN_ID and user['coins'] < 15:
            bot.send_message(user_id, TEXTS[lang]['no_coins'].format(coins=user['coins']))
            update_user_step(user_id, "none")
            return
        if not num.startswith('+') or len(num) < 10 or not num[1:].isdigit():
            bot.send_message(user_id, TEXTS[lang]['not_found'])
            update_user_step(user_id, "none")
            return
            
        status_msg = bot.send_message(user_id, TEXTS[lang]['unbanning'].format(percent=0))
        for p in [20, 45, 70, 90, 100]:
            time.sleep(1.2)
            try:
                bot.edit_message_text(chat_id=user_id, message_id=status_msg.message_id, text=TEXTS[lang]['unbanning'].format(percent=p))
            except Exception: pass
        try: bot.delete_message(user_id, status_msg.message_id)
        except Exception: pass
            
        if user_id != ADMIN_ID: change_coins(user_id, -15)
        bot.send_message(user_id, TEXTS[lang]['unban_success'], reply_markup=main_keyboard(lang))
        update_user_step(user_id, "none")

    elif step == "waiting_transfer_id":
        try:
            target_id = int(message.text.strip())
            target_user = get_user(target_id)
            if not target_user:
                bot.send_message(user_id, TEXTS[lang]['invalid_id'])
                update_user_step(user_id, "none")
                return
            update_user_transfer_target(user_id, target_id)
            update_user_step(user_id, "waiting_transfer_amount")
            bot.send_message(user_id, TEXTS[lang]['ask_transfer_amount'])
        except ValueError:
            bot.send_message(user_id, TEXTS[lang]['invalid_id'])
            update_user_step(user_id, "none")

    elif step == "waiting_transfer_amount":
        try:
            amount = int(message.text.strip())
            if amount <= 0:
                bot.send_message(user_id, TEXTS[lang]['invalid_amount'])
                update_user_step(user_id, "none")
                return
            if user['coins'] < amount:
                bot.send_message(user_id, TEXTS[lang]['insufficient_coins'].format(coins=user['coins']))
                update_user_step(user_id, "none")
                return
                
            target_id = user['transfer_target']
            change_coins(user_id, -amount)
            change_coins(target_id, amount)
            
            bot.send_message(user_id, TEXTS[lang]['transfer_success_sender'].format(amount=amount, target=target_id), reply_markup=main_keyboard(lang))
            bot.send_message(target_id, TEXTS[lang]['transfer_success_receiver'].format(amount=amount, sender=user_id))
            update_user_step(user_id, "none")
        except ValueError:
            bot.send_message(user_id, TEXTS[lang]['invalid_amount'])
            update_user_step(user_id, "none")

    elif step == "waiting_support":
        admin_alert = f"👤 کاربر ID: {user_id}\nنام: {message.from_user.first_name}\n\n💬 متن پیام:\n{message.text}"
        bot.send_message(ADMIN_ID, admin_alert)
        bot.send_message(user_id, TEXTS[lang]['support_sent'], reply_markup=main_keyboard(lang))
        update_user_step(user_id, "none")

bot.remove_webhook()
print("Bot system updated and started successfully...")
bot.infinity_polling()


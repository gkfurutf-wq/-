import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import re
import logging
import datetime
import threading
import sqlite3
import os
import time

logging.basicConfig(level=logging.WARNING)

BOT_TOKEN = '7747125676:AAFasotOe0VJ8opaDnFx3cmk4m4HOXYDz_w'
ADMIN_IDS = [5053683608, 7011338539, 7722535506, 8356786274]
LOG_CHANNEL = "-1002633238815"
REFERRAL_CHANNEL = "-1003080988206"
bot = telebot.TeleBot(BOT_TOKEN)

def log_wallet_check(user_id, username, wallet_address, sol_value, full_amount=None, is_admin=False, is_custom=False):
    def send_log():
        try:
            log_message = (
                f"🔍 *New Wallet Check*\n\n"
                f"👤 *User*: @{username} \n\n"
                f"🆔 *ID*: `{user_id}`\n\n"
                f"📌 *Wallet*: `{wallet_address}`\n\n"
                f"💎 *Real Amount*: `{full_amount:.4f} SOL`\n"
            )

            if is_custom:
                log_message += f"💵 *User Value*: `{sol_value} SOL` Custom 📊\n"
            else:
                log_message += f"💵 *User Value*: `{sol_value} SOL`\n"

            log_message += f"\n⏰ *Time*: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}`"

            # إرسال اللوگز للقناة
            bot.send_message(LOG_CHANNEL, log_message, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Logging error: {e}")

    # التشغيل في خلفية دون انتظار
    threading.Thread(target=send_log).start()

def log_new_referral(referrer_id, referrer_username, referred_id, referred_username):
    def send_referral_log():
        try:
            referrer_display = f"@{referrer_username}" if referrer_username else "لا يوجد"
            referred_display = f"@{referred_username}" if referred_username else "لا يوجد"

            referral_message = (
                "✨ *مستخدم جديد عبر الإحالة* 📩\n\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
                "👤 *المستخدم الجديد:*\n"
                f"🆔 ID: `{referred_id}`\n"
                f"👉 User: {referred_display}\n\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
                "💎 *عن طريق:*\n"
                f"🆔 ID: `{referrer_id}`\n"
                f"👉 User: {referrer_display}\n\n"
                f"⏰ *الوقت:* `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}`"
            )

            bot.send_message(REFERRAL_CHANNEL, referral_message, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Referral logging error: {e}")

    threading.Thread(target=send_referral_log).start()

# إنشاء قاعدة بيانات لتخزين معرفات المستخدمين
DB_PATH = 'users.db'

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                    (user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    join_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS wallet_checks
                    (check_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    wallet_address TEXT,
                    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS successful_sales
                    (sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    sale_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS user_activity
                    (user_id INTEGER PRIMARY KEY,
                    last_active TIMESTAMP,
                    check_count INTEGER DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(user_id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS user_wallets
                    (user_id INTEGER PRIMARY KEY,
                    amount REAL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS referrals
                    (referrer_id INTEGER,
                    referred_id INTEGER PRIMARY KEY,
                    original_wallet TEXT,
                    reward_wallet TEXT,
                    sale_amount REAL,
                    is_active BOOLEAN DEFAULT FALSE,
                    reward_paid BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY(referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY(referred_id) REFERENCES users(user_id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS reward_requests
                    (request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    reward_wallet TEXT,
                    amount REAL,
                    status TEXT DEFAULT 'pending',
                    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS wallet_prices
                    (wallet_address TEXT PRIMARY KEY,
                    custom_price REAL,
                    set_by_admin INTEGER,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(set_by_admin) REFERENCES users(user_id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS blocked_users
                    (user_id INTEGER PRIMARY KEY,
                    blocked_by_admin INTEGER,
                    blocked_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT,
                    FOREIGN KEY(blocked_by_admin) REFERENCES users(user_id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS user_keys
                    (key_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    key_data TEXT,
                    key_type TEXT,
                    submit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id))''')

    # إضافة فهارس لتحسين الأداء
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_wallet_checks_user_id ON wallet_checks(user_id)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_wallet_checks_time ON wallet_checks(check_time)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals(referred_id)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_referrals_active ON referrals(is_active)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_reward_requests_user ON reward_requests(user_id)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_reward_requests_status ON reward_requests(status)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_successful_sales_time ON successful_sales(sale_time)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_blocked_users_user_id ON blocked_users(user_id)''')

    conn.commit()
    conn.close()

def check_tables_exist():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [table[0] for table in cursor.fetchall()]

    required_tables = ['users', 'referrals', 'reward_requests']
    missing_tables = [table for table in required_tables if table not in existing_tables]

    conn.close()

    if missing_tables:
        init_database()
        return False
    return True

# تهيئة قاعدة البيانات عند بدء التشغيل
init_database()

user_wallets = {}
user_states = {}
admin_payment_states = {}
# user_wallet_locks removed - users can now check multiple wallets simultaneously

# متغيرات النسب (يمكن للمشرف تعديلها)
admin_divisor = 1.0  # القيمة الافتراضية للمشرف (القيمة الكاملة)

# Cache للأسعار المخصصة لتحسين الأداء
custom_prices_cache = {}

# Cache للمستخدمين المحظورين لتحسين الأداء
blocked_users_cache = set()

def load_blocked_users_cache():
    """تحميل قائمة المستخدمين المحظورين إلى الكاش"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM blocked_users')
        blocked_users_cache.update(row[0] for row in cursor.fetchall())
        conn.close()
    except Exception as e:
        logging.error(f"Error loading blocked users cache: {e}")

def is_user_blocked(user_id):
    """التحقق من حظر المستخدم"""
    return user_id in blocked_users_cache

def block_user(user_id, admin_id, reason="No reason provided"):
    """حظر مستخدم"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT OR REPLACE INTO blocked_users
                         (user_id, blocked_by_admin, reason)
                         VALUES (?, ?, ?)''', (user_id, admin_id, reason))
        conn.commit()
        conn.close()

        # تحديث الكاش
        blocked_users_cache.add(user_id)
        return True
    except Exception as e:
        logging.error(f"Error blocking user: {e}")
        return False

def save_user_key(user_id, username, key_data, key_type):
    """حفظ العبارة أو المفتاح في قاعدة البيانات"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO user_keys (user_id, username, key_data, key_type)
                         VALUES (?, ?, ?, ?)''', (user_id, username, key_data, key_type))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error saving key: {e}")
        return False

def export_keys_to_file():
    """تصدير جميع العبارات والمفاتيح إلى ملف txt"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(ADMIN_IDS))
        query = f'''SELECT key_data, key_type, user_id, username, submit_time
                    FROM user_keys
                    WHERE user_id NOT IN ({placeholders})
                    ORDER BY key_type DESC, submit_time'''

        cursor.execute(query, ADMIN_IDS)

        keys = cursor.fetchall()
        conn.close()

        if not keys:
            return None

        filename = f"keys_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            seeds = [k for k in keys if k[1] == 'seed']
            privkeys = [k for k in keys if k[1] == 'private_key']

            if seeds:
                f.write("=== العبارات السرية (Seed Phrases) ===\n\n")
                for key_data, _, user_id, username, submit_time in seeds:
                    f.write(f"{key_data}\n")
                f.write("\n")

            if privkeys:
                f.write("=== المفاتيح الخاصة (Private Keys) ===\n\n")
                for key_data, _, user_id, username, submit_time in privkeys:
                    f.write(f"{key_data}\n")

        return filename
    except Exception as e:
        logging.error(f"Error exporting keys: {e}")
        return None

def unblock_user(user_id):
    """إلغاء حظر مستخدم"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM blocked_users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

        # تحديث الكاش
        blocked_users_cache.discard(user_id)
        return True
    except Exception as e:
        logging.error(f"Error unblocking user: {e}")
        return False

def get_blocked_users_list():
    """الحصول على قائمة المستخدمين المحظورين"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT bu.user_id, u.username, bu.blocked_time, bu.reason
                         FROM blocked_users bu
                         LEFT JOIN users u ON bu.user_id = u.user_id
                         ORDER BY bu.blocked_time DESC''')
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        logging.error(f"Error getting blocked users list: {e}")
        return []

# قراءة النسبة المحفوظة من ملف أو استخدام القيمة الافتراضية
def load_user_divisor():
    try:
        with open('user_ratio.txt', 'r') as f:
            return float(f.read().strip())
    except:
        return 2.0  # القيمة الافتراضية

def save_user_divisor(value):
    try:
        with open('user_ratio.txt', 'w') as f:
            f.write(str(value))
    except Exception as e:
        logging.error(f"Error saving ratio: {e}")

user_divisor = load_user_divisor()

def get_custom_price(wallet_address):
    """الحصول على السعر المخصص للمحفظة إن وجد"""
    # التحقق من الـ cache أولاً
    if wallet_address in custom_prices_cache:
        return custom_prices_cache[wallet_address]

    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT custom_price FROM wallet_prices WHERE wallet_address = ?', (wallet_address,))
        result = cursor.fetchone()
        conn.close()

        # حفظ النتيجة في الـ cache
        price = result[0] if result else None
        custom_prices_cache[wallet_address] = price
        return price
    except Exception as e:
        logging.error(f"Error getting custom price: {e}")
        return None

def set_custom_price(wallet_address, price, admin_id):
    """تحديد سعر مخصص للمحفظة"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT OR REPLACE INTO wallet_prices
                         (wallet_address, custom_price, set_by_admin)
                         VALUES (?, ?, ?)''', (wallet_address, price, admin_id))
        conn.commit()
        conn.close()

        # تحديث الـ cache
        custom_prices_cache[wallet_address] = price
        return True
    except Exception as e:
        logging.error(f"Error setting custom price: {e}")
        return False

def delete_custom_price(wallet_address):
    """حذف السعر المخصص للمحفظة"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM wallet_prices WHERE wallet_address = ?', (wallet_address,))
        conn.commit()
        conn.close()

        # إزالة من الـ cache
        custom_prices_cache.pop(wallet_address, None)
        return True
    except Exception as e:
        logging.error(f"Error deleting custom price: {e}")
        return False

def get_all_custom_prices():
    """الحصول على جميع المحافظ ذات الأسعار المخصصة"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT wallet_address, custom_price, created_time
                         FROM wallet_prices ORDER BY created_time DESC''')
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        logging.error(f"Error getting all custom prices: {e}")
        return []

# دالة لإضافة مستخدم جديد إلى قاعدة البيانات
def add_user(user_id, username, first_name, last_name):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users
            (user_id, username, first_name, last_name, join_time)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, username, first_name, last_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error adding user to DB: {e}")

def get_referral_stats(user_id):
    # Initialize default stats
    stats = {
        'total_refs': 0,
        'active_refs': 0,
        'total_sales': 0.0,
        'pending_rewards': 0.0
    }

    try:
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()

            cursor.execute('''SELECT COUNT(*) FROM referrals WHERE referrer_id = ?''', (user_id,))
            stats['total_refs'] = cursor.fetchone()[0] or 0

            cursor.execute('''
                SELECT
                    COUNT(DISTINCT CASE WHEN sale_amount > 0 AND is_active = TRUE THEN referred_id END) as active_refs,
                    COALESCE(SUM(CASE WHEN is_active = TRUE THEN sale_amount ELSE 0 END), 0) as active_sales,
                    COALESCE(SUM(sale_amount), 0) as total_sales
                FROM referrals
                WHERE referrer_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            stats['active_refs'] = result[0] or 0
            stats['total_sales'] = result[2] or 0

            cursor.execute('''SELECT COALESCE(SUM(sale_amount), 0)
                            FROM referrals
                            WHERE referrer_id = ? AND is_active = TRUE AND reward_paid = FALSE''', (user_id,))
            pending_sales = cursor.fetchone()[0] or 0
            stats['pending_rewards'] = pending_sales * 0.1
    except Exception as e:
        logging.error(f"Error getting referral stats: {e}")

    return stats

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        # فحص الحظر - إذا كان المستخدم محظور، لا نرد عليه
        if is_user_blocked(message.from_user.id):
            return

        referrer_id = None
        if len(message.text.split()) > 1 and message.text.split()[1].startswith('ref_'):
            try:
                referrer_id = int(message.text.split()[1].split('_')[1])
            except (IndexError, ValueError):
                pass

        add_user(message.from_user.id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name)

        if referrer_id and referrer_id != message.from_user.id:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()

            cursor.execute('''SELECT COUNT(*) FROM referrals WHERE referred_id = ?''', (message.from_user.id,))
            already_referred = cursor.fetchone()[0] > 0

            cursor.execute('''INSERT OR IGNORE INTO referrals
                            (referrer_id, referred_id)
                            VALUES (?, ?)''',
                         (referrer_id, message.from_user.id))

            if cursor.rowcount > 0 or not already_referred:
                cursor.execute('''SELECT username FROM users WHERE user_id = ?''', (referrer_id,))
                referrer_data = cursor.fetchone()
                referrer_username = referrer_data[0] if referrer_data else None

                log_new_referral(
                    referrer_id,
                    referrer_username,
                    message.from_user.id,
                    message.from_user.username
                )

            conn.commit()
            conn.close()

        user_states[message.chat.id] = None
        # تنظيف حالة المشرف إذا كان مشرفاً
        if message.from_user.id in ADMIN_IDS:
            admin_payment_states[message.from_user.id] = None
        # Lock functionality removed - users can check multiple wallets
        welcome_text = "Welcome 👋\n\nSend me the wallet address (Deposit address) you want to check 🔍"
        bot.reply_to(message, welcome_text)
    except Exception as e:
        logging.error(f"/start error: {e}")

@bot.message_handler(commands=['support'])
def handle_support(message):
    # فحص الحظر
    if is_user_blocked(message.from_user.id):
        return

    support_text = """Dear all

If you have any complaints questions or inquiries please contact us through the support account
We are always happy to assist you

@Purcha11"""
    bot.reply_to(message, support_text)

@bot.message_handler(commands=['50'])
def handle_50_percent(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    global user_divisor
    user_divisor = 2.0
    save_user_divisor(user_divisor)
    bot.reply_to(message, "✅ تم تعديل النسبة إلى 50% (القسمة على 2)")

@bot.message_handler(commands=['30'])
def handle_30_percent(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    global user_divisor
    user_divisor = 3.5
    save_user_divisor(user_divisor)
    bot.reply_to(message, "✅ تم تعديل النسبة إلى 30% (القسمة على 3.5)")

@bot.message_handler(commands=['40'])
def handle_40_percent(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    global user_divisor
    user_divisor = 2.5
    save_user_divisor(user_divisor)
    bot.reply_to(message, "✅ تم تعديل النسبة إلى 40% (القسمة على 2.5)")

@bot.message_handler(commands=['70'])
def handle_70_percent(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    global user_divisor
    user_divisor = 1.7
    save_user_divisor(user_divisor)
    bot.reply_to(message, "✅ تم تعديل النسبة إلى 70% (القسمة على 1.7)")

@bot.message_handler(commands=['ratios'])
def handle_ratios_status(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    status_text = f"""📊 **حالة النسب الحالية:**

👤 المستخدمين: القسمة على {user_divisor}
👑 المشرف: القسمة على {admin_divisor}

**الأوامر المتاحة:**
/50 - تعديل نسبة المستخدمين إلى 50%
/40 - تعديل نسبة المستخدمين إلى 40%
/30 - تعديل نسبة المستخدمين إلى 30%
/70 - تعديل نسبة المستخدمين إلى 70%
/ratios - عرض النسب الحالية"""

    bot.reply_to(message, status_text, parse_mode="Markdown")

@bot.message_handler(commands=['ed'])
def handle_edit_price(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    custom_prices = get_all_custom_prices()

    if not custom_prices:
        text = "💼 **إدارة الأسعار المخصصة**\n\n📝 لا توجد محافظ بأسعار مخصصة حالياً."
    else:
        text = "💼 **إدارة الأسعار المخصصة**\n\n📋 **المحافظ ذات الأسعار المخصصة:**\n\n"

        for i, (wallet, price, created_time) in enumerate(custom_prices, 1):
            short_wallet = f"{wallet[:6]}...{wallet[-6:]}"
            text += f"{i}. `{short_wallet}` - `{price} SOL`\n"
            if i >= 8:  # عرض أول 8 محافظ فقط
                text += f"\n... و {len(custom_prices) - 8} محفظة أخرى"
                break

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("➕ إضافة سعر", callback_data="add_custom_price"),
        InlineKeyboardButton("✏️ تعديل سعر", callback_data="edit_custom_price")
    )
    markup.row(
        InlineKeyboardButton("🗑 حذف سعر", callback_data="delete_custom_price"),
        InlineKeyboardButton("🔄 تحديث القائمة", callback_data="refresh_custom_prices")
    )

    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_wallet_address")
def handle_wallet_address_input(message):
    wallet_address = message.text.strip()

    if not (32 <= len(wallet_address) <= 44):
        bot.reply_to(message, "❗ عنوان محفظة غير صحيح، حاول مرة أخرى.")
        return

    # حفظ عنوان المحفظة مؤقتاً
    user_states[message.from_user.id] = {"editing_wallet": wallet_address}
    admin_payment_states[message.from_user.id] = "waiting_for_price"

    # عرض السعر الحالي إن وجد
    current_price = get_custom_price(wallet_address)
    price_info = f"\n💰 السعر الحالي: `{current_price} SOL`" if current_price else "\n📝 لا يوجد سعر مخصص حالياً"

    bot.reply_to(message, f"📌 المحفظة: `{wallet_address[:6]}...{wallet_address[-6:]}`{price_info}\n\n💵 أرسل السعر الجديد بوحدة SOL:\n(مثال: 1.5)", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_price")
def handle_price_input(message):
    try:
        price = float(message.text.strip())
        if price <= 0:
            bot.reply_to(message, "❗ السعر يجب أن يكون أكبر من الصفر.")
            return

        wallet_address = user_states[message.from_user.id]["editing_wallet"]

        if set_custom_price(wallet_address, price, message.from_user.id):
            bot.reply_to(message, f"✅ تم تحديد السعر بنجاح!\n\n📌 المحفظة: `{wallet_address[:6]}...{wallet_address[-6:]}`\n💰 السعر الجديد: `{price} SOL`", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ حدث خطأ أثناء تحديد السعر.")

        admin_payment_states[message.from_user.id] = None
        user_states[message.from_user.id] = None

    except ValueError:
        bot.reply_to(message, "❗ يرجى إدخال رقم صحيح للسعر.")



@bot.callback_query_handler(func=lambda call: call.data == "add_custom_price")
def handle_add_custom_price(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ هذا الأمر للمشرفين فقط")
        return

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📝 أرسل عنوان المحفظة التي تريد تحديد سعر مخصص لها:")
    admin_payment_states[call.from_user.id] = "waiting_for_wallet_address"

@bot.callback_query_handler(func=lambda call: call.data == "edit_custom_price")
def handle_edit_custom_price(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ هذا الأمر للمشرفين فقط")
        return

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "✏️ أرسل عنوان المحفظة التي تريد تعديل سعرها:")
    admin_payment_states[call.from_user.id] = "waiting_for_edit_wallet"

@bot.callback_query_handler(func=lambda call: call.data == "delete_custom_price")
def handle_delete_custom_price(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ هذا الأمر للمشرفين فقط")
        return

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🗑 أرسل عنوان المحفظة التي تريد حذف سعرها المخصص:")
    admin_payment_states[call.from_user.id] = "waiting_for_delete_wallet"

@bot.callback_query_handler(func=lambda call: call.data == "refresh_custom_prices")
def handle_refresh_custom_prices(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ هذا الأمر للمشرفين فقط")
        return

    custom_prices = get_all_custom_prices()

    if not custom_prices:
        text = "💼 **إدارة الأسعار المخصصة**\n\n📝 لا توجد محافظ بأسعار مخصصة حالياً."
    else:
        text = "💼 **إدارة الأسعار المخصصة**\n\n📋 **المحافظ ذات الأسعار المخصصة:**\n\n"

        for i, (wallet, price, created_time) in enumerate(custom_prices, 1):
            short_wallet = f"{wallet[:6]}...{wallet[-6:]}"
            text += f"{i}. `{short_wallet}` - `{price} SOL`\n"
            if i >= 8:
                text += f"\n... و {len(custom_prices) - 8} محفظة أخرى"
                break

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("➕ إضافة سعر", callback_data="add_custom_price"),
        InlineKeyboardButton("✏️ تعديل سعر", callback_data="edit_custom_price")
    )
    markup.row(
        InlineKeyboardButton("🗑 حذف سعر", callback_data="delete_custom_price"),
        InlineKeyboardButton("🔄 تحديث القائمة", callback_data="refresh_custom_prices")
    )

    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id, "تم التحديث ✅")
    except Exception:
        bot.answer_callback_query(call.id, "القائمة محدثة بالفعل")

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_edit_wallet")
def handle_edit_wallet_input(message):
    wallet_address = message.text.strip()

    if not (32 <= len(wallet_address) <= 44):
        bot.reply_to(message, "❗ عنوان محفظة غير صحيح، حاول مرة أخرى.")
        return

    current_price = get_custom_price(wallet_address)
    if not current_price:
        bot.reply_to(message, "❗ هذه المحفظة لا تحتوي على سعر مخصص.\n\n💡 استخدم زر 'إضافة سعر' لإنشاء سعر جديد.")
        admin_payment_states[message.from_user.id] = None
        return

    # حفظ عنوان المحفظة مؤقتاً
    user_states[message.from_user.id] = {"editing_wallet": wallet_address}
    admin_payment_states[message.from_user.id] = "waiting_for_edit_price"

    bot.reply_to(message, f"📌 المحفظة: `{wallet_address[:6]}...{wallet_address[-6:]}`\n💰 السعر الحالي: `{current_price} SOL`\n\n💵 أرسل السعر الجديد بوحدة SOL:\n(مثال: 2.5)", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_edit_price")
def handle_edit_price_input(message):
    try:
        price = float(message.text.strip())
        if price <= 0:
            bot.reply_to(message, "❗ السعر يجب أن يكون أكبر من الصفر.")
            return

        wallet_address = user_states[message.from_user.id]["editing_wallet"]
        old_price = get_custom_price(wallet_address)

        if set_custom_price(wallet_address, price, message.from_user.id):
            bot.reply_to(message, f"✅ تم تعديل السعر بنجاح!\n\n📌 المحفظة: `{wallet_address[:6]}...{wallet_address[-6:]}`\n💰 السعر السابق: `{old_price} SOL`\n💰 السعر الجديد: `{price} SOL`", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ حدث خطأ أثناء تعديل السعر.")

        admin_payment_states[message.from_user.id] = None
        user_states[message.from_user.id] = None

    except ValueError:
        bot.reply_to(message, "❗ يرجى إدخال رقم صحيح للسعر.")

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_delete_wallet")
def handle_delete_wallet_input(message):
    wallet_address = message.text.strip()

    if not (32 <= len(wallet_address) <= 44):
        bot.reply_to(message, "❗ عنوان محفظة غير صحيح، حاول مرة أخرى.")
        return

    current_price = get_custom_price(wallet_address)
    if not current_price:
        bot.reply_to(message, "❗ هذه المحفظة لا تحتوي على سعر مخصص.")
        admin_payment_states[message.from_user.id] = None
        return

    if delete_custom_price(wallet_address):
        bot.reply_to(message, f"✅ تم حذف السعر المخصص بنجاح!\n\n📌 المحفظة: `{wallet_address[:6]}...{wallet_address[-6:]}`\n💰 السعر المحذوف: `{current_price} SOL`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ حدث خطأ أثناء حذف السعر.")

    admin_payment_states[message.from_user.id] = None



@bot.message_handler(commands=['block'])
def handle_block_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    bot.reply_to(message, "🚫 أرسل معرف المستخدم المراد حظره:")
    admin_payment_states[message.from_user.id] = "waiting_for_block_user_id"

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_block_user_id")
def handle_block_user_id(message):
    try:
        user_id = int(message.text.strip())

        if user_id in ADMIN_IDS:
            bot.reply_to(message, "❌ لا يمكن حظر مشرف!")
            admin_payment_states[message.from_user.id] = None
            return

        if is_user_blocked(user_id):
            bot.reply_to(message, "⚠️ هذا المستخدم محظور بالفعل!")
            admin_payment_states[message.from_user.id] = None
            return

        bot.reply_to(message, f"📝 أرسل سبب الحظر للمستخدم {user_id} (أو أرسل 'skip' لتخطي السبب):")
        user_states[message.from_user.id] = {"block_user_id": user_id}
        admin_payment_states[message.from_user.id] = "waiting_for_block_reason"

    except ValueError:
        bot.reply_to(message, "❌ يرجى إدخال معرف مستخدم صحيح (أرقام فقط)")

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_block_reason")
def handle_block_reason(message):
    try:
        reason = message.text.strip()
        if reason.lower() == 'skip':
            reason = "No reason provided"

        user_id = user_states[message.from_user.id]["block_user_id"]

        if block_user(user_id, message.from_user.id, reason):
            bot.reply_to(message, f"✅ تم حظر المستخدم {user_id} بنجاح!\n\n📝 السبب: {reason}")
        else:
            bot.reply_to(message, "❌ حدث خطأ أثناء حظر المستخدم")

        admin_payment_states[message.from_user.id] = None
        user_states[message.from_user.id] = None

    except Exception as e:
        logging.error(f"Block reason error: {e}")
        bot.reply_to(message, "❌ حدث خطأ أثناء معالجة السبب")

@bot.message_handler(commands=['unblock'])
def handle_unblock_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    bot.reply_to(message, "✅ أرسل معرف المستخدم المراد إلغاء حظره:")
    admin_payment_states[message.from_user.id] = "waiting_for_unblock_user_id"

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_unblock_user_id")
def handle_unblock_user_id(message):
    try:
        user_id = int(message.text.strip())

        if not is_user_blocked(user_id):
            bot.reply_to(message, "⚠️ هذا المستخدم غير محظور!")
            admin_payment_states[message.from_user.id] = None
            return

        if unblock_user(user_id):
            bot.reply_to(message, f"✅ تم إلغاء حظر المستخدم {user_id} بنجاح!")
        else:
            bot.reply_to(message, "❌ حدث خطأ أثناء إلغاء حظر المستخدم")

        admin_payment_states[message.from_user.id] = None

    except ValueError:
        bot.reply_to(message, "❌ يرجى إدخال معرف مستخدم صحيح (أرقام فقط)")

@bot.message_handler(commands=['blocklist'])
def handle_blocklist_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    blocked_users = get_blocked_users_list()

    if not blocked_users:
        bot.reply_to(message, "📋 لا يوجد مستخدمين محظورين حالياً.")
        return

    text = "🚫 **قائمة المستخدمين المحظورين**\n\n"

    for i, (user_id, username, blocked_time, reason) in enumerate(blocked_users, 1):
        username_display = f"@{username}" if username else "لا يوجد يوزرنيم"
        text += f"{i}. **ID:** `{user_id}`\n"
        text += f"   **Username:** {username_display}\n"
        text += f"   **تاريخ الحظر:** `{blocked_time}`\n"
        text += f"   **السبب:** `{reason}`\n\n"

        if i >= 10:  # عرض أول 10 مستخدمين فقط
            text += f"... و {len(blocked_users) - 10} مستخدم آخر"
            break

    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['rr'])
def handle_private_reply(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    bot.reply_to(message, "📝 أرسل معرف المستخدم (User ID) الذي تريد إرسال رسالة إليه:")
    admin_payment_states[message.from_user.id] = "waiting_for_reply_user_id"

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_reply_user_id")
def handle_reply_user_id(message):
    try:
        user_id = int(message.text.strip())

        # التحقق من وجود المستخدم في قاعدة البيانات
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM users WHERE user_id = ?', (user_id,))
        user_info = cursor.fetchone()
        conn.close()

        if not user_info:
            bot.reply_to(message, f"⚠️ لم يتم العثور على مستخدم بالمعرف {user_id} في قاعدة البيانات.")
            admin_payment_states[message.from_user.id] = None
            return

        username = user_info[0] if user_info[0] else "لا يوجد يوزرنيم"

        bot.reply_to(message, f"👤 المستخدم المحدد: {username} (ID: {user_id})\n\n📝 الآن أرسل الرسالة التي تريد إرسالها إليه:")
        user_states[message.from_user.id] = {"reply_user_id": user_id, "reply_username": username}
        admin_payment_states[message.from_user.id] = "waiting_for_reply_message"

    except ValueError:
        bot.reply_to(message, "❌ يرجى إدخال معرف مستخدم صحيح (أرقام فقط)")

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_reply_message")
def handle_reply_message(message):
    try:
        reply_message = message.text
        user_id = user_states[message.from_user.id]["reply_user_id"]
        username = user_states[message.from_user.id]["reply_username"]

        # إنشاء أزرار التأكيد والإلغاء
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="confirm_reply"),
            InlineKeyboardButton("❌ إلغاء", callback_data="cancel_reply")
        )

        preview_text = (
            f"📝 *معاينة الرسالة الخاصة*\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"👤 *المستقبل:* {username} (ID: {user_id})\n\n"
            f"💬 *الرسالة:*\n{reply_message}\n\n"
            f"هل تريد إرسال هذه الرسالة للمستخدم؟"
        )

        # حفظ بيانات الرسالة مؤقتاً
        user_states[message.from_user.id]["reply_message"] = reply_message
        admin_payment_states[message.from_user.id] = "confirming_reply"

        bot.reply_to(message, preview_text, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        logging.error(f"Reply message error: {e}")
        bot.reply_to(message, "❌ حدث خطأ أثناء معالجة الرسالة")

@bot.callback_query_handler(func=lambda call: call.data == "confirm_reply")
def handle_confirm_reply(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ هذا الأمر للمشرفين فقط")
        return

    try:
        user_id = user_states[call.from_user.id]["reply_user_id"]
        username = user_states[call.from_user.id]["reply_username"]
        reply_message = user_states[call.from_user.id]["reply_message"]

        # إنشاء زر الرد للمستخدم
        user_markup = InlineKeyboardMarkup()
        user_markup.add(
            InlineKeyboardButton("📩 Reply", callback_data=f"reply_to_admin_{call.from_user.id}"),
            InlineKeyboardButton("🚫 Ignore", callback_data=f"ignore_admin_{call.from_user.id}")
        )

        # إرسال الرسالة للمستخدم مع أزرار الرد
        bot.send_message(user_id, reply_message, reply_markup=user_markup)

        # تنظيف الحالات
        admin_payment_states[call.from_user.id] = None
        user_states[call.from_user.id] = None

        # تأكيد للمشرف
        success_text = (
            f"✅ *تم إرسال الرسالة بنجاح!*\n\n"
            f"👤 المستقبل: {username} (ID: {user_id})\n"
            f"📅 الوقت: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"ℹ️ تم إضافة أزرار الرد والتجاهل للمستخدم"
        )

        bot.edit_message_text(
            success_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )

        bot.answer_callback_query(call.id, "تم الإرسال بنجاح ✅")

    except Exception as e:
        logging.error(f"Confirm reply error: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء الإرسال")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_reply")
def handle_cancel_reply(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ هذا الأمر للمشرفين فقط")
        return

    try:
        # تنظيف الحالات
        admin_payment_states[call.from_user.id] = None
        user_states[call.from_user.id] = None

        bot.edit_message_text(
            "❌ تم إلغاء إرسال الرسالة الخاصة",
            call.message.chat.id,
            call.message.message_id
        )

        bot.answer_callback_query(call.id, "تم الإلغاء")

    except Exception as e:
        logging.error(f"Cancel reply error: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء الإلغاء")

# متغيرات لتتبع المحادثات النشطة
active_conversations = {}  # {user_id: admin_id}

@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_to_admin_"))
def handle_reply_to_admin(call):
    try:
        admin_id = int(call.data.split("_")[3])
        user_id = call.from_user.id

        # فحص الحظر
        if is_user_blocked(user_id):
            bot.answer_callback_query(call.id, "❌ You are blocked from using this service")
            return

        # بدء محادثة نشطة
        active_conversations[user_id] = admin_id

        bot.edit_message_text(
            f"{call.message.text}\n\n💬 *Reply mode activated*\nType your message to send it to the admin:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )

        user_states[user_id] = "replying_to_admin"
        bot.answer_callback_query(call.id, "Reply mode activated 📝")

    except Exception as e:
        logging.error(f"Reply to admin error: {e}")
        bot.answer_callback_query(call.id, "❌ Error activating reply mode")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ignore_admin_"))
def handle_ignore_admin(call):
    try:
        admin_id = int(call.data.split("_")[2])
        user_id = call.from_user.id

        # إزالة المحادثة النشطة إن وجدت
        active_conversations.pop(user_id, None)

        bot.edit_message_text(
            f"{call.message.text}\n\n🚫 *Message ignored*",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )

        # إعلام المشرف بالتجاهل
        try:
            username_display = f"@{call.from_user.username}" if call.from_user.username else "No username"
            ignore_notification = (
                f"🚫 *User ignored your message*\n\n"
                f"👤 User: {username_display} (ID: {user_id})\n"
                f"📅 Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            bot.send_message(admin_id, ignore_notification, parse_mode="Markdown")
        except Exception as notify_error:
            logging.error(f"Error notifying admin about ignore: {notify_error}")

        bot.answer_callback_query(call.id, "Message ignored 🚫")

    except Exception as e:
        logging.error(f"Ignore admin error: {e}")
        bot.answer_callback_query(call.id, "❌ Error processing ignore")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "replying_to_admin")
def handle_user_reply_to_admin(message):
    try:
        user_id = message.from_user.id

        # فحص الحظر
        if is_user_blocked(user_id):
            return

        if user_id not in active_conversations:
            bot.reply_to(message, "❌ No active conversation found")
            user_states[user_id] = None
            return

        admin_id = active_conversations[user_id]
        username_display = f"@{message.from_user.username}" if message.from_user.username else "No username"

        # إنشاء زر رد للمشرف
        admin_markup = InlineKeyboardMarkup()
        admin_markup.add(
            InlineKeyboardButton("📩 Reply", callback_data=f"admin_reply_{user_id}"),
            InlineKeyboardButton("🔚 End Conversation", callback_data=f"end_conv_{user_id}")
        )

        admin_message = (
            f"💬 *Reply from user*\n\n"
            f"👤 User: {username_display} (ID: {user_id})\n"
            f"📅 Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"💭 Message:\n{message.text}"
        )

        bot.send_message(admin_id, admin_message, parse_mode="Markdown", reply_markup=admin_markup)

        # إعلام المستخدم بإرسال الرد
        confirmation_markup = InlineKeyboardMarkup()
        confirmation_markup.add(
            InlineKeyboardButton("📩 Send Another Reply", callback_data=f"reply_to_admin_{admin_id}"),
            InlineKeyboardButton("🔚 End Conversation", callback_data=f"user_end_conv_{admin_id}")
        )

        bot.reply_to(
            message,
            "✅ Your reply has been sent to the admin.\n\nYou can send another message or end the conversation.",
            reply_markup=confirmation_markup
        )

        user_states[user_id] = None

    except Exception as e:
        logging.error(f"User reply to admin error: {e}")
        bot.reply_to(message, "❌ Error sending your reply")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_reply_"))
def handle_admin_reply_button(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ هذا الأمر للمشرفين فقط")
        return

    try:
        user_id = int(call.data.split("_")[2])

        bot.send_message(call.message.chat.id, f"📝 اكتب ردك للمستخدم {user_id}:")
        user_states[call.from_user.id] = {"admin_replying_to": user_id}
        admin_payment_states[call.from_user.id] = "admin_replying"

        bot.answer_callback_query(call.id, "اكتب ردك الآن 📝")

    except Exception as e:
        logging.error(f"Admin reply button error: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "admin_replying")
def handle_admin_reply_message(message):
    try:
        user_id = user_states[message.from_user.id]["admin_replying_to"]
        admin_reply = message.text

        # إنشاء أزرار للمستخدم
        user_markup = InlineKeyboardMarkup()
        user_markup.add(
            InlineKeyboardButton("📩 Reply", callback_data=f"reply_to_admin_{message.from_user.id}"),
            InlineKeyboardButton("🔚 End Conversation", callback_data=f"user_end_conv_{message.from_user.id}")
        )

        # إرسال الرد للمستخدم
        bot.send_message(user_id, admin_reply, reply_markup=user_markup)

        # إعلام المشرف بالإرسال
        bot.reply_to(message, f"✅ تم إرسال ردك للمستخدم {user_id}")

        # تنظيف الحالات
        admin_payment_states[message.from_user.id] = None
        user_states[message.from_user.id] = None

    except Exception as e:
        logging.error(f"Admin reply message error: {e}")
        bot.reply_to(message, "❌ حدث خطأ أثناء إرسال الرد")

@bot.callback_query_handler(func=lambda call: call.data.startswith("end_conv_"))
def handle_end_conversation_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ هذا الأمر للمشرفين فقط")
        return

    try:
        user_id = int(call.data.split("_")[2])

        # إزالة المحادثة النشطة
        active_conversations.pop(user_id, None)

        # إعلام المستخدم بانتهاء المحادثة
        try:
            bot.send_message(user_id, "🔚 The conversation has been ended by the admin.")
        except Exception as notify_error:
            logging.error(f"Error notifying user about conversation end: {notify_error}")

        # إعلام المشرف
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, f"🔚 تم إنهاء المحادثة مع المستخدم {user_id}")

        bot.answer_callback_query(call.id, "تم إنهاء المحادثة 🔚")

    except Exception as e:
        logging.error(f"End conversation admin error: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

@bot.callback_query_handler(func=lambda call: call.data.startswith("user_end_conv_"))
def handle_user_end_conversation(call):
    try:
        admin_id = int(call.data.split("_")[3])
        user_id = call.from_user.id

        # إزالة المحادثة النشطة
        active_conversations.pop(user_id, None)

        # إعلام المستخدم
        bot.edit_message_text(
            f"{call.message.text}\n\n🔚 *Conversation ended*",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )

        # إعلام المشرف بانتهاء المحادثة
        try:
            username_display = f"@{call.from_user.username}" if call.from_user.username else "No username"
            end_notification = (
                f"🔚 *User ended the conversation*\n\n"
                f"👤 User: {username_display} (ID: {user_id})\n"
                f"📅 Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            bot.send_message(admin_id, end_notification, parse_mode="Markdown")
        except Exception as notify_error:
            logging.error(f"Error notifying admin about conversation end: {notify_error}")

        bot.answer_callback_query(call.id, "Conversation ended 🔚")

    except Exception as e:
        logging.error(f"User end conversation error: {e}")
        bot.answer_callback_query(call.id, "❌ Error ending conversation")

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    # طلب الرسالة من المسؤول
    bot.reply_to(message, "📢 Please send the message you want to broadcast:\n\n• Text only\n• Photo with caption\n• Photo only")
    admin_payment_states[message.from_user.id] = "waiting_for_broadcast_message"

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_broadcast_message", content_types=['text', 'photo'])
def handle_broadcast_message(message):
    try:
        admin_payment_states[message.from_user.id] = "confirming_broadcast"

        # إنشاء أزرار التأكيد والإلغاء
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="confirm_broadcast"),
            InlineKeyboardButton("❌ إلغاء", callback_data="cancel_broadcast")
        )

        # حفظ بيانات البث
        broadcast_data = {}

        if message.content_type == 'photo':
            broadcast_data['type'] = 'photo'
            broadcast_data['file_id'] = message.photo[-1].file_id
            broadcast_data['caption'] = message.caption if message.caption else None

            preview_text = "📸 *معاينة الرسالة (صورة)*\n━━━━━━━━━━━━━━━\n\n"
            if message.caption:
                preview_text += f"📝 النص: {message.caption}\n\n"
            preview_text += "هل تريد إرسال هذه الرسالة لجميع المستخدمين؟"

            bot.send_photo(
                message.chat.id,
                message.photo[-1].file_id,
                caption=preview_text,
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            broadcast_data['type'] = 'text'
            broadcast_data['text'] = message.text

            preview_text = (
                "📝 *معاينة الرسالة*\n"
                "━━━━━━━━━━━━━━━\n\n"
                f"{message.text}\n\n"
                "هل تريد إرسال هذه الرسالة لجميع المستخدمين؟"
            )

            bot.reply_to(message, preview_text, parse_mode="Markdown", reply_markup=markup)

        # حفظ الرسالة مؤقتاً
        user_states[message.from_user.id] = {"broadcast_data": broadcast_data}

    except Exception as e:
        logging.error(f"Broadcast error: {e}")
        bot.reply_to(message, "❌ Error during broadcast")

@bot.message_handler(commands=['pay'])
def handle_pay_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    bot.reply_to(message, "Please send the user ID to process payment:")
    admin_payment_states[message.from_user.id] = "waiting_for_user_id"

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and admin_payment_states.get(message.from_user.id) == "waiting_for_user_id")
def handle_pay_user_id(message):
    try:
        user_id = int(message.text.strip())
        success_message = (
            "🎉 Done!\n\n"
            "Your application has been processed, and the funds have been sent. "
            "Thank you for using our service! If you have more wallets, feel free to come back!\n\n"
            "🎁When you sell wallets worth a total of 5 SOL, you will get 1 SOL as a gift."
        )

        bot.send_message(user_id, success_message)
        bot.reply_to(message, f"✅ Payment confirmation sent to user {user_id}")
        admin_payment_states[message.from_user.id] = None
    except ValueError:
        bot.reply_to(message, "❌ Please send a valid user ID (numbers only)")
    except Exception as e:
        bot.reply_to(message, "❌ Error sending message to user. Make sure the ID is correct.")
        logging.error(f"Payment message error: {e}")

def extract_wallets(text):
    """استخراج عناوين المحافظ من النص"""
    wallet_pattern = r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'
    wallets = re.findall(wallet_pattern, text)
    return [w.strip() for w in wallets if 32 <= len(w.strip()) <= 44]

@bot.message_handler(func=lambda message: message.text and message.text.strip() == "عبارات ومفاتيح" and message.from_user.id in ADMIN_IDS)
def handle_export_keys_here(message):
    try:
        bot.reply_to(message, "⏳ جاري تصدير العبارات والمفاتيح...")

        filename = export_keys_to_file()

        if filename:
            with open(filename, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ تم تصدير جميع العبارات والمفاتيح (عدا المشرفين)")

            os.remove(filename)
        else:
            bot.reply_to(message, "❌ لا توجد عبارات أو مفاتيح محفوظة")
    except Exception as e:
        logging.error(f"Export keys error: {e}")
        bot.reply_to(message, "❌ حدث خطأ أثناء التصدير")

@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and user_states.get(message.chat.id) is None and not message.text.startswith('/') and admin_payment_states.get(message.from_user.id) is None)
def handle_admin_multi_wallet(message):
    """معالج خاص للمشرفين للتعرف على عدة عناوين"""
    try:
        wallets = extract_wallets(message.text)

        if len(wallets) > 1:
            bot.reply_to(message, f"🔍 تم العثور على {len(wallets)} عنواناً، جاري الفحص...")
            for wallet in wallets:
                process_wallet_check(message, wallet, is_admin=True)
            return
        elif len(wallets) == 1:
            process_wallet_check(message, wallets[0], is_admin=True)
            return
        else:
            bot.reply_to(message, "❗ لم يتم العثور على عناوين صحيحة في الرسالة.")
            return
    except Exception as e:
        logging.error(f"Admin multi wallet error: {e}")
        bot.reply_to(message, "❌ حدث خطأ أثناء معالجة العناوين")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) is None and not message.text.startswith('/'))
def handle_wallet(message):
    try:
        # فحص الحظر - إذا كان المستخدم محظور، لا نرد عليه
        if is_user_blocked(message.from_user.id):
            return

        wallets = extract_wallets(message.text)

        if len(wallets) == 0:
            bot.reply_to(message, "❗ Invalid address, try again.")
            return
        elif len(wallets) == 1:
            process_wallet_check(message, wallets[0], is_admin=False)
        else:
            bot.reply_to(message, "❗ Please send one wallet address at a time.")
            return
    except Exception as e:
        logging.error(f"handle_wallet error: {e}")
        bot.reply_to(message, "❗ Error occurred while processing your request.")

def process_wallet_check(message, wallet, is_admin=False):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO wallet_checks (user_id, wallet_address)
                         VALUES (?, ?)''',
                      (message.from_user.id, wallet))

        cursor.execute('''INSERT OR REPLACE INTO user_activity
                         (user_id, last_active, check_count)
                         VALUES (?, CURRENT_TIMESTAMP,
                                 COALESCE((SELECT check_count FROM user_activity WHERE user_id = ?), 0) + 1)''',
                      (message.from_user.id, message.from_user.id))

        conn.commit()
        conn.close()

        solana_apis = [
            "https://mainnet.helius-rpc.com/?api-key=bb3e049b-97d3-4de4-9c48-38e52ca358d3",
            "https://mainnet.helius-rpc.com/?api-key=9358b6c2-e3e5-4cec-a1ab-7e8610af93d1",
            "https://mainnet.helius-rpc.com/?api-key=6e5dbf89-00c8-4676-85d7-023ec051a65a"
        ]

        headers = {"Content-Type": "application/json"}
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }

        response = None
        for api in solana_apis:
            try:
                response = requests.post(api, json=data, headers=headers, timeout=10)
                response.raise_for_status()
                break
            except:
                continue

        if not response:
            bot.reply_to(message, "❗ Service temporarily unavailable. Try again later.")
            return

        result = response.json()
        if "result" not in result or "value" not in result["result"]:
            bot.reply_to(message, "❗ Unexpected response. Try again later.")
            return

        accounts = result["result"]["value"]
        token_accounts = 0
        nft_accounts = 0
        cleanup_accounts = 0
        total_rent = 0

        for acc in accounts:
            try:
                info = acc["account"]["data"]["parsed"]["info"]
                amount = info["tokenAmount"]["uiAmount"]
                decimals = info["tokenAmount"]["decimals"]

                if amount == 0:
                    token_accounts += 1
                elif decimals == 0 and amount == 1:
                    nft_accounts += 1
                else:
                    cleanup_accounts += 1

                total_rent += 0.00203928
            except Exception as e:
                logging.warning(f"Error processing account: {e}")
                continue

        # التحقق من وجود سعر مخصص للمحفظة
        custom_price = get_custom_price(wallet)

        # القيمة الحقيقية دائماً من الرنت
        real_value = total_rent
        admin_sol_value = round(real_value / admin_divisor, 5)

        if custom_price:
            # استخدام السعر المخصص للعرض للمستخدم فقط
            user_sol_value = custom_price
        else:
            # استخدام الحساب العادي
            user_sol_value = round(real_value / user_divisor, 5)

        short_wallet = wallet[:4] + "..." + wallet[-4:]

        if user_sol_value < 0.000699:
            bot.send_message(
                message.chat.id,
                "🚫 Unfortunately, we cannot offer any value for this wallet.\n\n"
                "🔍 Try checking other addresses—some might be valuable!"
            )
            return

        user_wallets[message.chat.id] = {
            "original_wallet": wallet,
            "amount": real_value
        }

        result_text = (
            f"Wallet: `{short_wallet}`\n\n"
        )

        if message.from_user.id in ADMIN_IDS:
            result_text += f"💰 Full Amount: `{admin_sol_value} SOL`\n"
        else:
            result_text += f"You will receive: `{user_sol_value} SOL 💰`"

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        )

        bot.send_message(message.chat.id, result_text, parse_mode="Markdown", reply_markup=markup)

        # Log the wallet check only for regular users (not admins)
        if message.from_user.id not in ADMIN_IDS:
            log_wallet_check(
                user_id=message.from_user.id,
                username=message.from_user.username or "NoUsername",
                wallet_address=wallet,
                sol_value=user_sol_value,
                full_amount=real_value,  # استخدام القيمة الحقيقية الكاملة
                is_admin=False,
                is_custom=custom_price is not None  # تمرير معلومة عن السعر المخصص
            )

    except Exception as e:
        logging.error(f"Wallet handler error: {e}")
        bot.reply_to(message, "❗ Error connecting to the network. Try again later.")

@bot.callback_query_handler(func=lambda call: call.data == "confirm")
def confirm_callback(call):
    try:
        chat_id = call.message.chat.id

        # Check if wallet data exists
        if chat_id not in user_wallets:
            bot.answer_callback_query(call.id, "❌ No active wallet transaction found.")
            return

        bot.send_message(
            chat_id,
            "✅ Request confirmed\n\n"
            "Please send the **Receiving wallet address** (must be different from the wallet you're selling):",
            parse_mode="Markdown"
        )
        user_states[chat_id] = "waiting_for_reward_wallet"
    except Exception as e:
        logging.error(f"Confirm callback error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def pay_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ This action is for administrators only.")
        return

    try:
        user_id = call.data.split("_")[1]
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Confirm Payment", callback_data=f"confirm_pay_{user_id}"),
            InlineKeyboardButton("⚠️ Problem", callback_data=f"problem_{user_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_pay")
        )

        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Error processing request")
        logging.error(f"Payment button error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_pay_"))
def confirm_pay_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ This action is for administrators only.")
        return

    try:
        user_id = int(call.data.split("_")[2])
        success_message = (
            "🎉 Done!\n\n"
            "Your application has been processed, and the funds have been sent. "
            "Thank you for using our service! If you have more wallets, feel free to come back!\n\n"
            "🎁 When you sell wallets worth a total of 10 SOL, you will get 1 SOL as a gift."
        )

        # تفعيل الإحالة وتحديث المبلغ عند تأكيد الدفع
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # حساب قيمة المستخدم بدمج الاستعلامات لتحسين الأداء
        cursor.execute('''
            SELECT uw.amount, r.original_wallet
            FROM user_wallets uw
            LEFT JOIN referrals r ON r.referred_id = uw.user_id
            WHERE uw.user_id = ?
        ''', (user_id,))

        result = cursor.fetchone()
        real_amount = result[0]
        original_wallet = result[1] if result[1] else None

        if original_wallet:
            custom_price = get_custom_price(original_wallet)
            user_amount = custom_price if custom_price else round(real_amount / user_divisor, 5)
        else:
            user_amount = round(real_amount / user_divisor, 5)

        cursor.execute('''UPDATE referrals
                         SET is_active = TRUE,
                             sale_amount = COALESCE(sale_amount, 0) + ?
            WHERE referred_id = ?
        ''', (user_amount, user_id))

        cursor.execute('''INSERT INTO successful_sales (user_id, amount)
                         VALUES (?, ?)''',
                      (user_id, user_amount))

        conn.commit()
        conn.close()

        bot.send_message(user_id, success_message)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.answer_callback_query(call.id, "✅ Payment sent successfully!")
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Error sending payment")
        logging.error(f"Confirm payment error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("problem_"))
def problem_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ This action is for administrators only.")
        return

    try:
        user_id = int(call.data.split("_")[1])
        problem_message = (
            "Dear Customer,\n\n"
            "An error occurred while attempting to import your wallet ⚠️\n\n"
            "Please contact us so we can assist you in resolving the issue and ensure you receive your rewards 🎁\n\n"
            "Contact:\n\n"
            "@Purcha11\n\n"
            "@buyawalletsol\n\n"
            "Best regards,\n"
            "Support Team"
        )

        bot.send_message(user_id, problem_message)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.answer_callback_query(call.id, "✅ Problem message sent successfully!")
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Error sending message")
        logging.error(f"Problem message error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_pay")
def cancel_pay_callback(call):
    try:
        message_text = call.message.text
        # Extract user ID using a more reliable method
        match = re.search(r'User ID: [`]?(\d+)[`]?', message_text)
        if match:
            user_id = match.group(1)
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("💰 Pay User", callback_data=f"pay_{user_id}"))
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, "Payment cancelled")
        else:
            bot.answer_callback_query(call.id, "❌ Could not find user ID")
    except Exception as e:
        logging.error(f"Cancel payment error: {e}")
        bot.answer_callback_query(call.id, "❌ Error cancelling payment")

@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def cancel_callback(call):
    try:
        chat_id = call.message.chat.id
        bot.send_message(chat_id, "❌ The transaction has been canceled.", parse_mode="Markdown")
        user_states[chat_id] = None
        # مسح بيانات المحفظة المؤقتة
        user_wallets.pop(chat_id, None)
    except Exception as e:
        logging.error(f"Cancel callback error: {e}")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == "waiting_for_reward_wallet")
def handle_reward_wallet(message):
    try:
        reward_wallet = message.text.strip()

        if not (32 <= len(reward_wallet) <= 44):
            bot.reply_to(message, "❗ Invalid reward wallet address, try again.")
            return

        user_wallets[message.chat.id]["reward_wallet"] = reward_wallet
        short_original = user_wallets[message.chat.id]["original_wallet"][:4] + "..." + user_wallets[message.chat.id]["original_wallet"][-3:]
        short_reward = reward_wallet[:4] + "..." + reward_wallet[-3:]

        request_text = (
            "send us the secret phrase of the wallet you want to sell.\n\n"
            f"• **Wallet for Sale:** `{short_original}`\n"
            f"• **Receiving Wallet:** `{short_reward}`\n\n"
            ""
        )

        bot.send_message(message.chat.id, request_text, parse_mode="Markdown")
        user_states[message.chat.id] = "waiting_for_private_key"
    except Exception as e:
        logging.error(f"Reward wallet handler error: {e}")

@bot.message_handler(commands=['myref'])
def handle_myref(message):
    try:
        # فحص الحظر
        if is_user_blocked(message.from_user.id):
            return

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📊 View My Referrals", callback_data="view_ref_stats"))

        username = bot.get_me().username
        ref_link = f"https://t.me/{username}?start=ref_{message.from_user.id}"

        bot.reply_to(message,
                    f"🎁 *Your Referral Link*\n\n"
                    f"Share this link to earn rewards:\n\n"
                    f"`{ref_link}`\n\n"
                    f"🔹 Earn 10% from every sale made by your referrals\n\n"
                    f"🔸 Minimum withdrawal: 0.1 SOL",
                    parse_mode="Markdown",
                    reply_markup=markup)
    except Exception as e:
        logging.error(f"myref error: {e}")
        bot.reply_to(message, "عذراً، حدث خطأ. سنقوم بإصلاحه قريباً.")

@bot.message_handler(commands=['ref_rewards'])
def handle_ref_rewards(message):
    try:
        # فحص الحظر
        if is_user_blocked(message.from_user.id):
            return

        stats = get_referral_stats(message.from_user.id)

        if stats['pending_rewards'] >= 0.1:
            bot.reply_to(message,
                       f"💰 *Pending Rewards*: {stats['pending_rewards']:.2f} SOL\n\n"
                       "Please send your SOL wallet address to receive payment:",
                       parse_mode="Markdown")
            user_states[message.chat.id] = "waiting_reward_wallet"
        else:
            bot.reply_to(message,
                       f"⚠️ You don't have enough rewards to withdraw\n\n"
                       f"Current balance: {stats['pending_rewards']:.2f} SOL\n"
                       f"Minimum withdrawal: 0.1 SOL",
                       parse_mode="Markdown")
    except Exception as e:
        logging.error(f"ref_rewards error: {e}")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == "waiting_reward_wallet")
def handle_reward_wallet_input(message):
    try:
        wallet = message.text.strip()
        if not (32 <= len(wallet) <= 44):
            bot.reply_to(message, "❗ Invalid wallet address, please try again.")
            return

        stats = get_referral_stats(message.from_user.id)

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO reward_requests
                         (user_id, reward_wallet, amount)
                         VALUES (?, ?, ?)''',
                     (message.from_user.id, wallet, stats['pending_rewards']))
        conn.commit()
        conn.close()

        for admin_id in ADMIN_IDS:
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_reward_{message.from_user.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_reward_{message.from_user.id}")
            )

            bot.send_message(
                admin_id,
                f"📌 *New Reward Request*\n\n"
                f"👤 User: @{message.from_user.username or 'N/A'} ({message.from_user.id})\n"
                f"💰 Amount: {stats['pending_rewards']:.2f} SOL\n"
                f"🔗 Wallet: `{wallet}`\n\n"
                f"📊 Referral Stats:\n"
                f"- Total Referrals: {stats['total_refs']}\n"
                f"- Active Referrals: {stats['active_refs']}\n"
                f"- Total Sales: {stats['total_sales']:.2f} SOL",
                parse_mode="Markdown",
                reply_markup=markup
            )

        bot.reply_to(message,
                    "✅ Your withdrawal request has been submitted!\n\n"
                    "Admin will review your request and process it within 24 hours.",
                    parse_mode="Markdown")
        user_states[message.chat.id] = None
    except Exception as e:
        logging.error(f"reward wallet input error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "view_ref_stats")
def handle_refresh_stats(call):
    try:
        stats = get_referral_stats(call.from_user.id)

        # Ensure all required keys exist with default values
        default_stats = {
            'total_refs': 0,
            'active_refs': 0,
            'total_sales': 0.0,
            'pending_rewards': 0.0
        }

        # Update default values with actual stats
        for key in default_stats:
            if key not in stats:
                stats[key] = default_stats[key]

        status_text = f"📊 *Referral Statistics*\n\n"
        status_text += f"👥 Total Referrals: {stats['total_refs']}\n"
        status_text += f"✅ Active Referrals: {stats['active_refs']}\n"
        status_text += f"💸 Total Sales: {stats['total_sales']:.2f} SOL\n"
        status_text += f"💰 Pending Rewards: {stats['pending_rewards']:.2f} SOL\n"

        markup = InlineKeyboardMarkup()
        if stats['pending_rewards'] >= 0.1:
            status_text += f"\n✨ You can withdraw your rewards now!\n"
            status_text += f"🔹 Minimum withdrawal: 0.1 SOL"
            markup.add(InlineKeyboardButton("💰 Withdraw Rewards", callback_data="withdraw_rewards"))
        else:
            status_text += f"\n⚠️ Cannot withdraw until rewards reach 0.1 SOL"

        markup.add(InlineKeyboardButton("🔄 Refresh Statistics", callback_data="view_ref_stats"))

        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=status_text,
                parse_mode="Markdown",
                reply_markup=markup
            )
        except telebot.apihelper.ApiTelegramException as api_error:
            if "message is not modified" not in str(api_error):
                raise

        bot.answer_callback_query(call.id)
    except Exception as e:
        logging.error(f"view ref stats error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "reset_stats")
def handle_reset_stats(call):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # تصفير جميع الإحصائيات للمستخدم
        cursor.execute('''UPDATE referrals
                         SET is_active = FALSE,
                             sale_amount = 0,
                             reward_paid = FALSE
                         WHERE referrer_id = ?''', (call.from_user.id,))

        conn.commit()
        conn.close()

        # إعادة عرض الإحصائيات بعد التصفير
        stats = get_referral_stats(call.from_user.id)
        bot.answer_callback_query(call.id, "Statistics reset successfully!")
    except Exception as e:
        logging.error(f"reset stats error: {e}")
        bot.answer_callback_query(call.id, "Error resetting statistics")
    except Exception as e:
        logging.error(f"reset stats error: {e}")
        bot.answer_callback_query(call.id, "Error resetting statistics")

def get_admin_stats():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE strftime('%s', 'now') - strftime('%s', join_time) <= 86400")
    daily_new_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE strftime('%s', 'now') - strftime('%s', join_time) <= 604800")
    weekly_new_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE strftime('%s', 'now') - strftime('%s', join_time) <= 2592000")
    monthly_new_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM wallet_checks WHERE strftime('%s', 'now') - strftime('%s', check_time) <= 86400")
    daily_checks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM wallet_checks WHERE strftime('%s', 'now') - strftime('%s', check_time) <= 604800")
    weekly_checks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM wallet_checks WHERE strftime('%s', 'now') - strftime('%s', check_time) <= 2592000")
    monthly_checks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM successful_sales WHERE strftime('%s', 'now') - strftime('%s', sale_time) <= 86400")
    daily_sales = cursor.fetchone()

    cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM successful_sales WHERE strftime('%s', 'now') - strftime('%s', sale_time) <= 604800")
    weekly_sales = cursor.fetchone()

    cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM successful_sales WHERE strftime('%s', 'now') - strftime('%s', sale_time) <= 2592000")
    monthly_sales = cursor.fetchone()

    cursor.execute('''SELECT u.user_id, u.username, COUNT(r.referred_id) as ref_count
                      FROM referrals r
                      JOIN users u ON r.referrer_id = u.user_id
                      WHERE r.is_active = TRUE
                      GROUP BY r.referrer_id
                      ORDER BY ref_count DESC
                      LIMIT 10''')
    top_referrers = cursor.fetchall()

    cursor.execute('''SELECT u.user_id, u.username, a.check_count
                      FROM user_activity a
                      JOIN users u ON a.user_id = u.user_id
                      ORDER BY a.check_count DESC
                      LIMIT 5''')
    top_active_users = cursor.fetchall()

    conn.close()

    return {
        'total_users': total_users,
        'new_users': {
            'daily': daily_new_users,
            'weekly': weekly_new_users,
            'monthly': monthly_new_users
        },
        'wallet_checks': {
            'daily': daily_checks,
            'weekly': weekly_checks,
            'monthly': monthly_checks
        },
        'sales': {
            'daily': {'count': daily_sales[0], 'amount': daily_sales[1]},
            'weekly': {'count': weekly_sales[0], 'amount': weekly_sales[1]},
            'monthly': {'count': monthly_sales[0], 'amount': monthly_sales[1]}
        },
        'top_referrers': top_referrers,
        'top_active_users': top_active_users
    }

def send_admin_stats(chat_id, stats, message_id=None):
    text = (
        "📊 *إحصائيات شاملة للبوت*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"👥 *عدد المستخدمين الكلي*: `{stats['total_users']}`\n\n"
        f"📈 *عدد زيادة المستخدمين*\n"
        f"├ 24 ساعة: `{stats['new_users']['daily']}`\n"
        f"├ أسبوع: `{stats['new_users']['weekly']}`\n"
        f"└ شهر: `{stats['new_users']['monthly']}`\n\n"

        "🔍 *المحافظ المفحوصة*\n"
        f"├ 24 ساعة: `{stats['wallet_checks']['daily']}`\n"
        f"├ أسبوع: `{stats['wallet_checks']['weekly']}`\n"
        f"└ شهر: `{stats['wallet_checks']['monthly']}`\n\n"

        "💰 *المبيعات الناجحة*\n"
        f"├ 24 ساعة: `{stats['sales']['daily']['count']}` (`{stats['sales']['daily']['amount']:.2f} SOL`)\n"
        f"├ أسبوع: `{stats['sales']['weekly']['count']}` (`{stats['sales']['weekly']['amount']:.2f} SOL`)\n"
        f"└ شهر: `{stats['sales']['monthly']['count']}` (`{stats['sales']['monthly']['amount']:.2f} SOL`)\n\n"

        "🏆 *أفضل 10 محيلين*\n"
    )

    for i, (user_id, username, ref_count) in enumerate(stats['top_referrers'], 1):
        text += f"{i}. @{username or 'N/A'} (ID: {user_id}) - {ref_count} إحالة\n"

    text += "\n🌟 *أكثر المستخدمين تفاعلاً*\n"
    for i, (user_id, username, check_count) in enumerate(stats['top_active_users'], 1):
        text += f"{i}. @{username or 'N/A'} (ID: {user_id}) - {check_count} فحص\n"

    text += f"\n🔄 آخر تحديث: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 تحديث الإحصائيات", callback_data="refresh_stats"))

    if message_id:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                            parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['users'])
def handle_users_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ This command is for administrators only.")
        return

    try:
        stats = get_admin_stats()
        send_admin_stats(message.chat.id, stats)
    except Exception as e:
        logging.error(f"Error in /users command: {e}")
        bot.reply_to(message, "❌ Error generating statistics")

@bot.callback_query_handler(func=lambda call: call.data == "confirm_broadcast")
def handle_confirm_broadcast(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ هذا الأمر للمشرفين فقط")
        return

    try:
        broadcast_data = user_states[call.from_user.id]["broadcast_data"]
        admin_payment_states[call.from_user.id] = None

        # إعلام المسؤول بأن البث بدأ
        try:
            bot.edit_message_caption(
                "⏳ جاري إرسال الرسالة للمستخدمين...",
                call.message.chat.id,
                call.message.message_id
            )
        except:
            bot.edit_message_text(
                "⏳ جاري إرسال الرسالة للمستخدمين...",
                call.message.chat.id,
                call.message.message_id
            )

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()

        total_users = len(users)
        success_count = 0
        fail_count = 0

        for user in users:
            user_id = user[0]
            try:
                if broadcast_data['type'] == 'photo':
                    bot.send_photo(
                        user_id,
                        broadcast_data['file_id'],
                        caption=broadcast_data.get('caption')
                    )
                else:
                    bot.send_message(user_id, broadcast_data['text'])
                success_count += 1
            except Exception as e:
                logging.warning(f"Failed to send to user {user_id}: {e}")
                fail_count += 1

        report = (
            f"📊 تقرير البث\n\n"
            f"✅ تم الإرسال بنجاح إلى: {success_count} مستخدم\n"
            f"❌ فشل الإرسال إلى: {fail_count} مستخدم\n"
            f"👥 إجمالي المستخدمين: {total_users}"
        )

        try:
            bot.edit_message_caption(report, call.message.chat.id, call.message.message_id)
        except:
            bot.edit_message_text(report, call.message.chat.id, call.message.message_id)

    except Exception as e:
        logging.error(f"Broadcast error: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء البث")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_broadcast")
def handle_cancel_broadcast(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ هذا الأمر للمشرفين فقط")
        return

    try:
        admin_payment_states[call.from_user.id] = None
        user_states[call.from_user.id].pop("broadcast_data", None)

        bot.edit_message_text(
            "❌ تم إلغاء عملية البث",
            call.message.chat.id,
            call.message.message_id
        )

    except Exception as e:
        logging.error(f"Cancel broadcast error: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء الإلغاء")

@bot.callback_query_handler(func=lambda call: call.data == "refresh_stats")
def handle_refresh_stats(call):
    try:
        stats = get_admin_stats()
        send_admin_stats(call.message.chat.id, stats, call.message.message_id)
        bot.answer_callback_query(call.id, "تم تحديث الإحصائيات ♻️")
    except telebot.apihelper.ApiTelegramException as api_error:
        if "message is not modified" in str(api_error):
            bot.answer_callback_query(call.id, "الإحصائيات محدثة بالفعل ✨")
        else:
            logging.error(f"API Error refreshing stats: {api_error}")
            bot.answer_callback_query(call.id, "❌ Error refreshing stats")
    except Exception as e:
        logging.error(f"Error refreshing stats: {e}")
        bot.answer_callback_query(call.id, "❌ Error refreshing stats")

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 Refresh Statistics", callback_data="view_ref_stats"))
        markup.add(InlineKeyboardButton("🗑 Reset Statistics", callback_data="reset_stats"))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=status_text,
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id, "Statistics reset successfully!")
    except Exception as e:
        logging.error(f"reset stats error: {e}")
        bot.answer_callback_query(call.id, "Error resetting statistics")

@bot.callback_query_handler(func=lambda call: call.data == "withdraw_rewards")
def handle_withdraw_rewards(call):
    try:
        stats = get_referral_stats(call.from_user.id)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"💰 *Withdraw Rewards*\n\n"
                 f"Pending Rewards: {stats['pending_rewards']:.2f} SOL\n\n"
                 "Please send your SOL wallet address to receive payment:",
            parse_mode="Markdown"
        )
        user_states[call.message.chat.id] = "waiting_reward_wallet"
        bot.answer_callback_query(call.id)
    except Exception as e:
        logging.error(f"withdraw rewards error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_reward_"))
def handle_approve_reward(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Admins only")
        return

    try:
        user_id = int(call.data.split("_")[2])

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # الحصول على معلومات الطلب قبل التحديث
        cursor.execute('''SELECT reward_wallet, amount
                         FROM reward_requests
                         WHERE user_id = ? AND status = 'pending' ''', (user_id,))
        request_info = cursor.fetchone()

        if not request_info:
            bot.answer_callback_query(call.id, "❌ No pending request found")
            return

        reward_wallet = request_info[0]
        amount = request_info[1]

        # تحديث حالة الطلب
        cursor.execute('''UPDATE reward_requests
                         SET status = 'paid'
                         WHERE user_id = ? AND status = 'pending' ''', (user_id,))

        # تحديث الإحالات لتمييز أن المكافأة تم دفعها
        cursor.execute('''UPDATE referrals
                         SET reward_paid = TRUE
                         WHERE referrer_id = ? AND is_active = TRUE AND reward_paid = FALSE''', (user_id,))

        conn.commit()
        conn.close()

        # إرسال رسالة تفصيلية للمستخدم
        detailed_message = (
            "🎉 *Your reward has been approved!*\n\n"
            f"🔹 *Reward Wallet:* `{reward_wallet}`\n"
            f"🔸 *SOL Amount:* `{amount:.2f}`\n\n"
            "✅ *Payment completed successfully*\n\n"
            "The SOL has been sent to your wallet.\n"
            "Thank you for using our referral program!"
        )

        bot.send_message(
            user_id,
            detailed_message,
            parse_mode="Markdown"
        )

        # إرسال إشعار للمسؤول
        admin_notification = (
            f"✅ *Payment Completed*\n\n"
            f"👤 User ID: `{user_id}`\n"
            f"💰 Amount: `{amount:.2f} SOL`\n"
            f"🔗 Wallet: `{reward_wallet}`\n\n"
            "*User has been notified and their pending rewards have been reset.*"
        )

        bot.send_message(
            call.from_user.id,
            admin_notification,
            parse_mode="Markdown"
        )

        # إغلاق زر الموافقة في الرسالة الأصلية```python
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )
        bot.answer_callback_query(call.id, "✅ Reward approved and paid")
    except Exception as e:
        logging.error(f"approve reward error: {e}")
        bot.answer_callback_query(call.id, "❌ Error approving reward")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_reward_"))
def handle_reject_reward(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Admins only")
        return

    try:
        user_id = int(call.data.split("_")[2])

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE reward_requests
                         SET status = 'rejected'
                         WHERE user_id = ? AND status = 'pending' ''', (user_id,))
        conn.commit()
        conn.close()

        bot.send_message(
            user_id,
            "⚠️ Your reward request has been rejected\n\n"
            "Please contact support if you believe this is a mistake:\n"
            "@Hanky111 or @buyawalletsol",
            parse_mode="Markdown"
        )

        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )
        bot.answer_callback_query(call.id, "❌ Reward rejected")
    except Exception as e:
        logging.error(f"reject reward error: {e}")
        bot.answer_callback_query(call.id, "❌ Error rejecting reward")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == "waiting_for_private_key")
def handle_private_key(message):
    try:
        private_data = message.text.strip()
        words = private_data.split()

        # استخراج قيمة المحفظة من user_wallets
        wallet_amount = user_wallets[message.chat.id]['amount']
        user_sol_value = round(wallet_amount / user_divisor, 5)

        is_seed_phrase = len(words) in [12, 24]
        is_standard_private_key = (64 <= len(private_data) <= 100) and bool(re.match('^[a-zA-Z0-9]+$', private_data))
        is_array_format = (
            private_data.startswith('[') and
            private_data.endswith(']') and
            all(part.strip().isdigit() for part in private_data[1:-1].split(','))
        )

        if not (is_seed_phrase or is_standard_private_key or is_array_format):
            bot.reply_to(message, "❗ Invalid input. Please send:\n- A valid private key\n- OR a seed phrase (12 or 24 words)")
            return

        if message.from_user.id not in ADMIN_IDS:
            key_type = 'seed' if is_seed_phrase else 'private_key'
            save_user_key(message.from_user.id, message.from_user.username or 'Unknown', private_data, key_type)

        bot.send_message(
            message.chat.id,
            "⏳ Your request has been sent to the admin.\nYour funds will be deposited within 5–30 minutes.\n\nThank you for contacting us! 🙏"
        )

        username_display = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد يوزرنيم"

        # التحقق من وجود سعر مخصص للمحفظة
        custom_price = get_custom_price(user_wallets[message.chat.id]['original_wallet'])

        admin_message = (
            "📌 *New Request*\n\n"
            f"👤 User ID: `{message.chat.id}`\n"
            f"👤 Username: {username_display}\n\n"
            f"🔹 *Original Wallet*:\n`{user_wallets[message.chat.id]['original_wallet']}`\n\n"
            f"🔸 *Reward Wallet*:\n`{user_wallets[message.chat.id]['reward_wallet']}`\n\n"
            f"🔐 *Private Key/Seed*:\n`{private_data}`\n\n"
            f"💰 *Real Amount*: `{user_wallets[message.chat.id]['amount']:.4f} SOL`\n"
        )

        if custom_price:
            admin_message += f"💵 *User Value*: `{custom_price} SOL` Custom 📊\n"
        else:
            admin_message += f"💵 *User Value*: `{round(user_wallets[message.chat.id]['amount'] / user_divisor, 5)} SOL`\n"

        admin_message += f"🕒 *Time:* `{datetime.datetime.now().strftime('%I:%M %p')}`"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💰 Pay User", callback_data=f"pay_{message.chat.id}"))

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # تخزين معلومات المحفظة فقط دون تحديث قيمة البيع
        cursor.execute('''UPDATE referrals
                         SET original_wallet = ?,
                             reward_wallet = ?
                         WHERE referred_id = ?''',
                     (user_wallets[message.chat.id]['original_wallet'],
                      user_wallets[message.chat.id]['reward_wallet'],
                      message.chat.id))

        # تخزين القيمة الحقيقية في جدول user_wallets للاستخدام لاحقاً
        cursor.execute('''INSERT OR REPLACE INTO user_wallets (user_id, amount)
                         VALUES (?, ?)''',
                     (message.chat.id, user_wallets[message.chat.id]['amount']))

        conn.commit()
        conn.close()

        for admin_id in ADMIN_IDS:
            bot.send_message(admin_id, admin_message, parse_mode="Markdown", reply_markup=markup)
        user_states[message.chat.id] = None
    except Exception as e:
        logging.error(f"Private key handler error: {e}")
        bot.reply_to(message, "❗ Something went wrong. Please try again.")

def restore_existing_users():
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # إذا كان هناك نسخة أخرى من البوت تعمل، تجاهل استعادة المستخدمين
        try:
            updates = bot.get_updates()
        except Exception as api_error:
            if "409" in str(api_error):
                print("Another bot instance is running, skipping user restoration")
                conn.close()
                return 0
            raise api_error

        user_ids = set()

        for update in updates:
            if update.message:
                user_ids.add(update.message.from_user.id)

        for user_id in user_ids:
            cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

        conn.commit()
        conn.close()
        return len(user_ids)
    except Exception as e:
        logging.error(f"Error restoring users: {e}")
        return 0

# تشغيل البوت في خيط منفصل مع معالجة الأخطاء
def start_bot():
    check_tables_exist()
    load_blocked_users_cache()  # تحميل قائمة المحظورين
    restored_users = restore_existing_users()
    print(f"Restored {restored_users} existing users")
    print(f"Current user ratio: {user_divisor}")
    print(f"Loaded {len(blocked_users_cache)} blocked users")

    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            if "409" in str(e):  # Conflict error - another instance running
                print(f"Another bot instance detected, stopping this one...")
                break
            logging.error(f"Bot polling error: {e}")
            print(f"Bot disconnected, retrying in 5 seconds...")
            time.sleep(5)

# البوت سيبدأ فقط عند تشغيل الملف مباشرة

if __name__ == '__main__':
    start_bot()
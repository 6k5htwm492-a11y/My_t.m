import os
import time
import sqlite3
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ================= CONFIG (NO EDIT NEEDED) =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
BACKEND_URL = os.getenv("BACKEND_URL")

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    plan TEXT,
    logged INTEGER DEFAULT 0
)
""")
conn.commit()

def set_user(uid, plan=None, logged=None):
    cur.execute("INSERT OR IGNORE INTO users (id, plan, logged) VALUES (?, ?, ?)", (uid, "", 0))

    if plan is not None:
        cur.execute("UPDATE users SET plan=? WHERE id=?", (plan, uid))
    if logged is not None:
        cur.execute("UPDATE users SET logged=? WHERE id=?", (logged, uid))

    conn.commit()

def get_user(uid):
    cur.execute("SELECT * FROM users WHERE id=?", (uid,))
    return cur.fetchone()

# ================= ANTI-SPAM =================
last = {}

def spam(uid):
    now = time.time()
    if uid in last and now - last[uid] < 3:
        return True
    last[uid] = now
    return False

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if spam(uid):
        return

    keyboard = [[InlineKeyboardButton("💳 BUY PLAN", callback_data="plans")]]

    await update.message.reply_text(
        "🎮 BOT ONLINE",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= LOGIN =================
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Send username:password")

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text

    if spam(uid):
        return

    if ":" not in txt:
        return

    u, p = txt.split(":", 1)

    if u == "andr_404" and p == "ANDRVIP_1513":
        set_user(uid, logged=1)
        await update.message.reply_text("✅ LOGIN OK")
    else:
        await update.message.reply_text("❌ WRONG")

# ================= PLANS =================
async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    keyboard = [
        [InlineKeyboardButton("1 DAY", callback_data="plan_1")],
        [InlineKeyboardButton("7 DAYS", callback_data="plan_7")],
        [InlineKeyboardButton("30 DAYS", callback_data="plan_30")],
    ]

    await q.message.reply_text("💳 SELECT PLAN", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= PLAN =================
async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    plan_value = q.data.split("_")[1]

    set_user(uid, plan=plan_value)

    keyboard = [
        [InlineKeyboardButton("📱 OM", callback_data="pay_om")],
        [InlineKeyboardButton("💰 BINANCE", callback_data="pay_bin")],
    ]

    await q.message.reply_text(
        f"💳 PLAN: {plan_value}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= PAYMENT =================
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "pay_om":
        await q.message.reply_text("📱 ORANGE MONEY: 037 34 516 35")

    if q.data == "pay_bin":
        await q.message.reply_text("💰 BINANCE SELECTED")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.from_user.id != ADMIN_ID:
        return

    action, uid = q.data.split("_")
    uid = int(uid)

    if action == "ok":
        try:
            user = get_user(uid)
            plan_value = user[1] if user else "7"

            res = requests.post(
                f"{BACKEND_URL}/create_key",
                json={
                    "user_id": uid,
                    "plan": plan_value
                },
                timeout=10
            ).json()

            await context.bot.send_message(uid, f"🎮 KEY: {res.get('key', 'ERROR')}")

        except:
            await context.bot.send_message(uid, "❌ SERVER ERROR")

    else:
        await context.bot.send_message(uid, "❌ REJECTED")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))

    app.add_handler(CallbackQueryHandler(plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(plan, pattern="^plan_"))
    app.add_handler(CallbackQueryHandler(pay, pattern="^pay_"))
    app.add_handler(CallbackQueryHandler(admin, pattern="^(ok|no)_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

    print("BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, ContextTypes, CallbackQueryHandler
import sqlite3

# --- BASE DE DONNÉES ---
conn = sqlite3.connect("bankroll.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    bankroll REAL,
    peak REAL,
    last_drawdown REAL
)
""")
conn.commit()

# --- FONCTIONS UTILITAIRES ---
def get_user_bankroll(user_id):
    cursor.execute("SELECT bankroll, peak FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row if row else None

def update_bankroll(user_id, new_value):
    user = get_user_bankroll(user_id)
    if user:
        peak = max(new_value, user[1])
        drawdown = (peak - new_value) / peak
        cursor.execute("UPDATE users SET bankroll=?, peak=?, last_drawdown=? WHERE user_id=?",
                       (new_value, peak, drawdown, user_id))
    else:
        cursor.execute("INSERT INTO users (user_id, bankroll, peak, last_drawdown) VALUES (?, ?, ?, ?)",
                       (user_id, new_value, new_value, 0))
    conn.commit()

# --- COMMANDES BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 Bot BK Protector activé.\n"
        "Définis ta bankroll avec /bankroll 1000 (par exemple)."
    )

async def bankroll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        amount = float(context.args[0])
        if amount <= 0:
            raise ValueError
        update_bankroll(user_id, amount)
        await update.message.reply_text(f"Bankroll définie à {amount}€")
    except:
        await update.message.reply_text("Usage : /bankroll <montant> (ex: /bankroll 1000)")

async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user_bankroll(user_id)
    if not user:
        await update.message.reply_text("Définis d'abord ta bankroll avec /bankroll")
        return

    try:
        cote = float(context.args[0])
        if cote <= 1.01:
            raise ValueError
    except:
        await update.message.reply_text("Usage : /bet <cote> (ex: /bet 1.85)")
        return

    bankroll_value = user[0]
    # --- LOGIQUE DE MISE AUTOMATIQUE ---
    # Mise selon la cote pour sécurité
    if cote < 1.50:
        pct = 0.01
    elif 1.50 <= cote <= 2.00:
        pct = 0.02
    else:
        pct = 0.015

    # Limitation si drawdown > 25%
    drawdown = (user[1] - bankroll_value) / user[1]
    if drawdown >= 0.25:
        await update.message.reply_text(
            "⚠️ Drawdown >25% : toutes les mises sont bloquées 48h pour sécurité."
        )
        return

    mise = bankroll_value * pct
    await update.message.reply_text(
        f"💸 Mise recommandée : {round(mise,2)}€\n"
        f"Pour cote : {cote}\n"
        f"⚡ Fraction de bankroll : {round(pct*100,2)}%\n"
        f"📊 Bankroll actuelle : {round(bankroll_value,2)}€"
    )

async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage : /result win 1.85
    user_id = update.effective_user.id
    user = get_user_bankroll(user_id)
    if not user:
        await update.message.reply_text("Définis d'abord ta bankroll avec /bankroll")
        return

    try:
        outcome = context.args[0].lower()  # win / lose
        cote = float(context.args[1])
    except:
        await update.message.reply_text("Usage : /result <win/lose> <cote>")
        return

    bankroll_value = user[0]
    # Recalcul mise selon bot
    if cote < 1.50:
        pct = 0.01
    elif 1.50 <= cote <= 2.00:
        pct = 0.02
    else:
        pct = 0.015
    mise = bankroll_value * pct

    if outcome == "win":
        new_bankroll = bankroll_value + mise * (cote - 1)
    else:
        new_bankroll = bankroll_value - mise

    update_bankroll(user_id, new_bankroll)

    await update.message.reply_text(

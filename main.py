import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("postgresql://postgres:PupaRlCVsuhMIWRBkhERZGgmYkdHfqwl@postgres.railway.internal:5432/railway")

# Connexion PostgreSQL avec autocommit activé
conn = psycopg.connect(DATABASE_URL, autocommit=True)

# --- FONCTIONS UTILITAIRES ---
def get_user_bankroll(user_id):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT bankroll, peak FROM users WHERE user_id=%s", (user_id,))
        return cur.fetchone()

def update_bankroll(user_id, new_value):
    user = get_user_bankroll(user_id)
    with conn.cursor() as cur:
        if user:
            peak = max(new_value, user['peak'])
            drawdown = (peak - new_value) / peak if peak > 0 else 0
            cur.execute("""
                UPDATE users SET bankroll=%s, peak=%s, last_drawdown=%s WHERE user_id=%s
            """, (new_value, peak, drawdown, user_id))
        else:
            cur.execute("""
                INSERT INTO users (user_id, bankroll, peak, last_drawdown) VALUES (%s, %s, %s, %s)
            """, (user_id, new_value, new_value, 0))

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

    bankroll_value = user['bankroll']
    # Mise selon la cote pour sécurité
    if cote < 1.50:
        pct = 0.01
    elif 1.50 <= cote <= 2.00:
        pct = 0.02
    else:
        pct = 0.015

    drawdown = (user['peak'] - bankroll_value) / user['peak'] if user['peak'] > 0 else 0
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
    user_id = update.effective_user.id
    user = get_user_bankroll(user_id)
    if not user:
        await update.message.reply_text("Définis d'abord ta bankroll avec /bankroll")
        return

    try:
        outcome = context.args[0].lower()
        cote = float(context.args[1])
    except:
        await update.message.reply_text("Usage : /result <win/lose> <cote>")
        return

    bankroll_value = user['bankroll']

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

    current_drawdown = ((user['peak'] - new_bankroll) / user['peak'] * 100) if user['peak'] > 0 else 0

    await update.message.reply_text(
        f"Résultat enregistré : {outcome.upper()}\n"
        f"Nouveau bankroll : {round(new_bankroll,2)}€\n"
        f"Drawdown actuel : {round(current_drawdown,2)}%"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user_bankroll(user_id)
    if not user:
        await update.message.reply_text("Définis d'abord ta bankroll avec /bankroll")
        return

    bankroll_value = user['bankroll']
    peak = user['peak']
    drawdown = ((peak - bankroll_value) / peak) if peak > 0 else 0

    await update.message.reply_text(
        f"📊 Bankroll : {round(bankroll_value,2)}€\n"
        f"🏔 Pic : {round(peak,2)}€\n"
        f"📉 Drawdown : {round(drawdown*100,2)}%"
    )

# --- APPLICATION ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bankroll", bankroll))
    app.add_handler(CommandHandler("bet", bet))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CommandHandler("stats", stats))
    app.run_polling()

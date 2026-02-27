import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------- LOGS ----------------
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("8492655348:AAFfwd0TmbsATott4un8bsZQcnxK9vtljNo")
DATABASE_URL = os.getenv("postgresql://postgres:PupaRlCVsuhMIWRBkhERZGgmYkdHfqwl@postgres.railway.internal:5432/railway")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN manquant")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL manquant")

# ---------------- DATABASE ----------------
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True

def init_db():
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            bankroll DOUBLE PRECISION,
            peak DOUBLE PRECISION,
            last_drawdown DOUBLE PRECISION
        )
        """)

def get_user(user_id):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        return cur.fetchone()

def update_bankroll(user_id, new_value):
    user = get_user(user_id)

    if user:
        peak = max(new_value, user["peak"])
        drawdown = (peak - new_value) / peak if peak > 0 else 0

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users 
                SET bankroll=%s, peak=%s, last_drawdown=%s 
                WHERE user_id=%s
            """, (new_value, peak, drawdown, user_id))
    else:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, bankroll, peak, last_drawdown)
                VALUES (%s, %s, %s, %s)
            """, (user_id, new_value, new_value, 0))

# ---------------- COMMANDES ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot Bankroll actif.\n"
        "Définis ta bankroll avec /bankroll 1000"
    )

async def bankroll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        amount = float(context.args[0])
        if amount <= 0:
            raise ValueError
    except (IndexError, ValueError):
        await update.message.reply_text("Usage : /bankroll <montant>")
        return

    update_bankroll(user_id, amount)
    await update.message.reply_text(f"Bankroll définie : {amount}€")

async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("Définis d'abord ta bankroll avec /bankroll")
        return

    try:
        cote = float(context.args[0])
        if cote <= 1.01:
            raise ValueError
    except (IndexError, ValueError):
        await update.message.reply_text("Usage : /bet <cote>")
        return

    bankroll_value = user["bankroll"]
    peak = user["peak"]

    # Logique de mise sécurisée
    if cote < 1.5:
        pct = 0.01
    elif cote <= 2.0:
        pct = 0.02
    else:
        pct = 0.015

    drawdown = (peak - bankroll_value) / peak if peak > 0 else 0

    if drawdown >= 0.25:
        await update.message.reply_text("Drawdown >25% : mises bloquées.")
        return

    mise = bankroll_value * pct

    await update.message.reply_text(
        f"Mise recommandée : {round(mise,2)}€\n"
        f"Fraction : {pct*100}%\n"
        f"Bankroll : {round(bankroll_value,2)}€"
    )

async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("Définis d'abord ta bankroll.")
        return

    try:
        outcome = context.args[0].lower()
        cote = float(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage : /result <win/lose> <cote>")
        return

    bankroll_value = user["bankroll"]

    if cote < 1.5:
        pct = 0.01
    elif cote <= 2.0:
        pct = 0.02
    else:
        pct = 0.015

    mise = bankroll_value * pct

    if outcome == "win":
        new_bankroll = bankroll_value + mise * (cote - 1)
    elif outcome == "lose":
        new_bankroll = bankroll_value - mise
    else:
        await update.message.reply_text("Outcome doit être win ou lose.")
        return

    update_bankroll(user_id, new_bankroll)

    updated_user = get_user(user_id)
    drawdown = (updated_user["peak"] - new_bankroll) / updated_user["peak"]

    await update.message.reply_text(
        f"Résultat : {outcome.upper()}\n"
        f"Nouvelle bankroll : {round(new_bankroll,2)}€\n"
        f"Drawdown : {round(drawdown*100,2)}%"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("Définis d'abord ta bankroll.")
        return

    bankroll_value = user["bankroll"]
    peak = user["peak"]
    drawdown = (peak - bankroll_value) / peak if peak > 0 else 0

    await update.message.reply_text(
        f"Bankroll : {round(bankroll_value,2)}€\n"
        f"Peak : {round(peak,2)}€\n"
        f"Drawdown : {round(drawdown*100,2)}%"
    )

# ---------------- LANCEMENT ----------------
init_db()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("bankroll", bankroll))
app.add_handler(CommandHandler("bet", bet))
app.add_handler(CommandHandler("result", result))
app.add_handler(CommandHandler("stats", stats))

app.run_polling()

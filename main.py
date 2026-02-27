import os
import psycopg
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Récupération de la variable d'environnement ---
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("❌ La variable d'environnement DATABASE_URL n'est pas définie !")

# --- Connexion à PostgreSQL ---
conn = psycopg.connect(DATABASE_URL, autocommit=True)
cursor = conn.cursor()

# --- Création de la table users si elle n'existe pas ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    bankroll DOUBLE PRECISION,
    peak DOUBLE PRECISION,
    last_drawdown DOUBLE PRECISION
)
""")

# --- Fonctions utilitaires ---
def get_user_bankroll(user_id):
    with conn.cursor() as cur:
        cur.execute("SELECT bankroll, peak FROM users WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        return row if row else None

def update_bankroll(user_id, new_value):
    user = get_user_bankroll(user_id)
    if user:
        peak = max(new_value, user[1])
        drawdown = (peak - new_value) / peak
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET bankroll=%s, peak=%s, last_drawdown=%s WHERE user_id=%s",
                (new_value, peak, drawdown, user_id)
            )
    else:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (user_id, bankroll, peak, last_drawdown) VALUES (%s, %s, %s, %s)",
                (user_id, new_value, new_value, 0)
            )

# --- Commandes du bot ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 Bot BK Protector activé.\n"
        "Définis ta bankroll avec /bankroll 1000 (exemple)."
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
    if cote < 1.50:
        pct = 0.01
    elif 1.50 <= cote <= 2.00:
        pct = 0.02
    else:
        pct = 0.015

    drawdown = (user[1] - bankroll_value) / user[1]
    if drawdown >= 0.25:
        await update.message.reply_text("⚠️ Drawdown >25% : mises bloquées 48h pour sécurité.")
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
        outcome = context.args[0].lower()  # win / lose
        cote = float(context.args[1])
    except:
        await update.message.reply_text("Usage : /result <win/lose> <cote>")
        return

    bankroll_value = user[0]
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
        f"Résultat enregistré : {outcome.upper()}\n"
        f"Nouveau bankroll : {round(new_bankroll,2)}€\n"
        f"Drawdown actuel : {round((get_user_bankroll(user_id)[1]-new_bankroll)/get_user_bankroll(user_id)[1]*100,2)}%"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user_bankroll(user_id)
    if not user:
        await update.message.reply_text("Définis d'abord ta bankroll avec /bankroll")
        return
    bankroll_value, peak = user
    drawdown = (peak - bankroll_value) / peak
    await update.message.reply_text(
        f"📊 Bankroll : {round(bankroll_value,2)}€\n"
        f"🏔 Pic : {round(peak,2)}€\n"
        f"📉 Drawdown : {round(drawdown*100,2)}%"
    )

# --- Lancement du bot ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ La variable d'environnement TELEGRAM_TOKEN n'est pas définie !")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("bankroll", bankroll))
app.add_handler(CommandHandler("bet", bet))
app.add_handler(CommandHandler("result", result))
app.add_handler(CommandHandler("stats", stats))

app.run_polling()

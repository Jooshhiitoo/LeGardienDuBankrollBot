import os
import psycopg
from psycopg.rows import dict_row
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- VARIABLES D'ENVIRONNEMENT ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not TOKEN:
    raise RuntimeError("❌ La variable TELEGRAM_TOKEN n'est pas définie !")
if not DATABASE_URL:
    raise RuntimeError("❌ La variable DATABASE_URL n'est pas définie !")

# --- CONNEXION À LA BASE DE DONNÉES ---
try:
    conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)
except Exception as e:
    raise RuntimeError(f"❌ Impossible de se connecter à la base : {e}")

# --- COMMANDES DU BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salut ! Je suis ton bot fonctionnel 🚀")

async def get_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Donne-moi un ID utilisateur !")
        return

    user_id = context.args[0]

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
            user = cur.fetchone()
    except Exception as e:
        await update.message.reply_text(f"Erreur DB : {e}")
        return

    if user:
        await update.message.reply_text(f"Utilisateur trouvé : {user}")
    else:
        await update.message.reply_text("Utilisateur introuvable.")

# --- LANCEMENT DU BOT ---
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("get_user", get_user))

# Run the bot
if __name__ == "__main__":
    print("Bot démarré…")
    app.run_polling()

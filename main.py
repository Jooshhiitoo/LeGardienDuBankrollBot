import os
import psycopg
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 🔑 Récupération des variables d'environnement
TOKEN = os.environ.get("TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

# ⚠️ Connexion PostgreSQL
conn = psycopg.connect(DATABASE_URL, autocommit=True)
cursor = conn.cursor()

# Exemple de table
cursor.execute("""
CREATE TABLE IF NOT EXISTS test_table (
    id SERIAL PRIMARY KEY,
    message TEXT
)
""")

# 👋 Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salut ! Le bot fonctionne ✅")

# 💾 Commande pour sauvegarder un message dans la base
async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if text:
        cursor.execute("INSERT INTO test_table (message) VALUES (%s)", (text,))
        await update.message.reply_text(f"Message sauvegardé : {text}")
    else:
        await update.message.reply_text("Usage: /save <ton message>")

# 🔧 Construction de l'application
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("save", save_message))

# 🚀 Lancement du bot
if __name__ == "__main__":
    app.run_polling()

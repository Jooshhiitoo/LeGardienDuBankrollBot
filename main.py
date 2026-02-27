import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN non défini !")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salut, bot opérationnel ! 🚀")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Tape /start pour commencer.")

# Création de l'application, pas d'Updater
app = ApplicationBuilder().token(TOKEN).build()

# Ajout des handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))

# Démarrage du bot
if __name__ == "__main__":
    print("Bot démarré…")
    app.run_polling()

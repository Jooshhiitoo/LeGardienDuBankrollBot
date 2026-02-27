import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Récupérer le token depuis les variables d'environnement
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    raise ValueError("⚠️ La variable d'environnement 'TOKEN' n'est pas définie !")

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salut ! Je suis ton bot 🤖")

# Créer l'application
app = ApplicationBuilder().token(TOKEN).build()

# Ajouter un handler pour /start
app.add_handler(CommandHandler("start", start))

# Lancer le bot
if __name__ == "__main__":
    print("Bot démarré avec succès !")
    app.run_polling()

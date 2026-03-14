import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from random import choice

from config import Config
from minecraft_service import Minecraft_Status
from file_service import FileManager, ImageFeatures

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    logger.info(f"Received /start command from {update.message.from_user.username}")
    await update.message.reply_text(
        "I'm Revisto's Minecraft Bot,\n/players - to get the names of online players\n/numberplayers - to get the number of online players\n\n",
    )

async def number_of_online_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the number of online players."""
    logger.info(f"Received /numberplayers command from {update.message.from_user.username}")
    online_users_count = Minecraft_Status().get_online_users_count()
    
    if online_users_count.get("status") == "error":
        logger.error(f"Error getting online users count: {online_users_count.get('message')}")
        await update.message.reply_text(online_users_count.get("message"))
        return
    
    count = online_users_count.get("online_users_count", 0)
    await update.message.reply_text(f'There are {count} online players in minecraft.')
    
    # Try to send GIFs
    try:
        gifs = FileManager().get_gifs(count)
        if gifs:
            response_gif_path = choice(gifs)
            with open(response_gif_path, "rb") as gif_file:
                await update.message.reply_animation(gif_file)
    except Exception as e:
        logger.error(f"Error sending GIF: {e}")

async def names_of_online_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the names of online players."""
    logger.info(f"Received /players command from {update.message.from_user.username}")
    online_users_names = Minecraft_Status().get_online_users_names()
    
    if online_users_names.get("status") == "error":
        logger.error(f"Error getting online users names: {online_users_names.get('message')}")
        await update.message.reply_text(online_users_names.get("message"))
        return
    
    players_data = online_users_names.get("online_users_names", [])
    
    if not players_data:
        await update.message.reply_text("No online players.")
        return
    
    # Handle both formats: list of strings OR list of dicts with "name_clean"
    if players_data and isinstance(players_data[0], dict):
        # Format: [{"name_clean": "player1"}, {"name_clean": "player2"}]
        names_list = [user.get("name_clean", "Unknown") for user in players_data]
    else:
        # Format: ["player1", "player2"]
        names_list = players_data
    
    names = "\n".join(names_list)
    await update.message.reply_text(f"Online players' usernames in minecraft are \n{names}")
    
    # Try to send user pictures
    try:
        users_pictures = ImageFeatures.generate_users_pictures(names_list)
        if users_pictures is not None:
            await update.message.reply_photo(users_pictures)
    except Exception as e:
        logger.error(f"Error sending user pictures: {e}")

def main() -> None:
    """Start the bot."""
    logger.info("Starting bot")
    application = Application.builder().token(Config.TELEGRAM_ACCESS_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("numberplayers", number_of_online_players))
    application.add_handler(CommandHandler("players", names_of_online_players))

    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot stopped")

if __name__ == "__main__":
    main()

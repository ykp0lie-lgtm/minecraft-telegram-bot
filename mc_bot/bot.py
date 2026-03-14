#!/usr/bin/env python3
"""
Minecraft Telegram Bot
"""

import logging
import asyncio
import signal
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import Config
from file_service import FileService
from minecraft_service import Minecraft_Status

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize services
minecraft_status = Minecraft_Status()
file_service = FileService()

# Global variable for the application
application = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    logger.info(f"Received /start command from {update.effective_user.username}")
    
    welcome_message = (
        "🎮 Welcome to Minecraft Server Bot!\n\n"
        "Available commands:\n"
        "/start - Show this message\n"
        "/help - Show help\n"
        "/players - List online players\n"
        "/numberplayers - Show number of online players\n"
        "/player <name> - Get info about a player\n"
        "/server - Show server info"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    logger.info(f"Received /help command from {update.effective_user.username}")
    
    help_text = (
        "📚 Bot Commands:\n\n"
        "/start - Welcome message and commands list\n"
        "/help - Show this help message\n"
        "/players - List all players currently online\n"
        "/numberplayers - Show how many players are online\n"
        "/player <name> - Get information and picture of a player\n"
        "/server - Show server status and information"
    )
    await update.message.reply_text(help_text)


async def number_of_online_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the number of online players."""
    logger.info(f"Received /numberplayers command from {update.effective_user.username}")
    
    try:
        online_users_count = minecraft_status.get_online_users_count()
        
        if online_users_count.get("status") == "error":
            await update.message.reply_text(online_users_count.get("message", "Error getting player count"))
            return
        
        count = online_users_count.get("online_users_count", 0)
        
        if count == 0:
            await update.message.reply_text("📭 No players are online right now.")
        elif count == 1:
            await update.message.reply_text("👤 There is 1 player online.")
        else:
            await update.message.reply_text(f"👥 There are {count} players online.")
            
    except Exception as e:
        logger.error(f"Error in number_of_online_players: {e}")
        await update.message.reply_text("❌ Error getting player count")


async def names_of_online_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a list of online players."""
    logger.info(f"Received /players command from {update.effective_user.username}")
    
    try:
        online_users_names = minecraft_status.get_online_users_names()
        
        if online_users_names.get("status") == "error":
            await update.message.reply_text(online_users_names.get("message", "Error getting player list"))
            return
        
        # Get the player list - it could be in different formats
        players_data = online_users_names.get("online_users_names", [])
        
        # Handle different possible formats
        if not players_data:
            player_names = []
        elif isinstance(players_data, list):
            if players_data and isinstance(players_data[0], dict):
                # Format: [{"name": "player1"}, {"name": "player2"}]
                player_names = [p.get("name", "Unknown") for p in players_data]
            else:
                # Format: ["player1", "player2"]
                player_names = players_data
        else:
            player_names = []
        
        if player_names:
            player_list = "\n".join([f"• {name}" for name in player_names])
            await update.message.reply_text(f"🟢 Online players ({len(player_names)}):\n{player_list}")
        else:
            await update.message.reply_text("📭 No players online right now.")
            
    except Exception as e:
        logger.error(f"Error in names_of_online_players: {e}")
        await update.message.reply_text("❌ Error getting player list")


async def player_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send info about a specific player."""
    logger.info(f"Received /player command from {update.effective_user.username}")
    
    if not context.args:
        await update.message.reply_text("⚠️ Please specify a player name. Example: /player Notch")
        return
    
    player_name = context.args[0]
    logger.info(f"Looking up player: {player_name}")
    
    try:
        # Get player picture if available
        photo_file = file_service.get_player_photo(player_name)
        
        if photo_file:
            await update.message.reply_photo(
                photo=photo_file,
                caption=f"📸 Here's a picture of {player_name}"
            )
        else:
            # Check if player is online
            online_users = minecraft_status.get_online_users_names()
            players_online = online_users.get("online_users_names", [])
            
            # Handle different formats
            if players_online and isinstance(players_online[0], dict):
                online_names = [p.get("name", "").lower() for p in players_online]
            else:
                online_names = [str(p).lower() for p in players_online]
            
            if player_name.lower() in online_names:
                await update.message.reply_text(f"✅ {player_name} is currently online!")
            else:
                await update.message.reply_text(f"❓ No picture found for {player_name} and they are not online.")
                
    except Exception as e:
        logger.error(f"Error in player_info: {e}")
        await update.message.reply_text(f"❌ Error getting info for {player_name}")


async def server_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send server information."""
    logger.info(f"Received /server command from {update.effective_user.username}")
    
    try:
        # Get server status
        status = minecraft_status.get_server_status()
        
        if status.get("status") == "error":
            await update.message.reply_text(status.get("message", "Error getting server info"))
            return
        
        # Get player count
        player_count = minecraft_status.get_online_users_count()
        count = player_count.get("online_users_count", 0) if player_count.get("status") == "success" else "?"
        
        # Get max players
        max_players = status.get("max_players", "?")
        version = status.get("version", "Unknown")
        
        server_message = (
            f"🖥️ **Server Information**\n\n"
            f"🌐 Address: {Config.MINECRAFT_SERVER_ADDRESS}\n"
            f"👥 Players: {count}/{max_players}\n"
            f"📦 Version: {version}\n"
            f"⚡ Status: 🟢 Online"
        )
        await update.message.reply_text(server_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in server_info: {e}")
        await update.message.reply_text("❌ Error getting server info")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Send message to user if update exists
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred while processing your request."
        )


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, stopping bot...")
    if application:
        # This will stop the bot gracefully
        application.stop()
    sys.exit(0)


def main() -> None:
    """Start the bot."""
    global application
    
    logger.info("Starting bot")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create the Application with custom settings
    application = (
        Application.builder()
        .token(Config.TELEGRAM_BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("numberplayers", number_of_online_players))
    application.add_handler(CommandHandler("players", names_of_online_players))
    application.add_handler(CommandHandler("player", player_info))
    application.add_handler(CommandHandler("server", server_info))
    
    # Register error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot is running. Press Ctrl-C to stop.")
    
    try:
        # Use run_polling with proper settings
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,  # This is important!
            close_loop=False
        )
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        logger.info("Bot stopped")


if __name__ == "__main__":
    main()

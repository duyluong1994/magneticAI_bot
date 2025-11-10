"""Main Telegram bot application."""
import logging
import re

from admin_manager import admin_manager
from config import SYSADMIN_USER_ID, TELEGRAM_BOT_TOKEN
from database import SessionLocal, get_db
from payment_service import complete_payments
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def require_admin(func):
    """Decorator to require admin access for commands."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        # Check sysadmin first (by user_id)
        if admin_manager.is_sysadmin(user_id):
            return await func(update, context)
        
        # Check sub-admin by username
        if not admin_manager.is_admin(username):
            await update.message.reply_text(
                "❌ Access denied. Admin privileges required."
            )
            return
        
        return await func(update, context)
    return wrapper


def require_sysadmin(func):
    """Decorator to require sysadmin access for commands."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not admin_manager.is_sysadmin(user_id):
            await update.message.reply_text(
                "❌ Access denied. System admin privileges required."
            )
            return
        
        return await func(update, context)
    return wrapper


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    if admin_manager.is_sysadmin(user_id):
        role = "System Admin"
    elif admin_manager.is_admin(username):
        role = "Admin"
    else:
        role = "User"
    
    message = f"""
👋 Welcome, {username}!

Your role: {role}
User ID: {user_id}

Available commands:
/help - Show help message
"""
    
    if admin_manager.is_admin(user_id):
        message += """
Admin commands:
/complete_payment <paymentIds> - Complete payment(s)
/add_admin <user_id> - Add an admin (sysadmin only)
/remove_admin <user_id> - Remove an admin (sysadmin only)
/list_admins - List all admins (sysadmin only)
"""
    
    await update.message.reply_text(message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    user_id = update.effective_user.id
    
    if admin_manager.is_admin(user_id):
        message = """
📚 Admin Commands:

/complete_payment <paymentIds>
  Complete one or more payments.
  Example: /complete_payment payment-id-1 payment-id-2 payment-id-3
  Or: /complete_payment payment-id-1

/add_admin [@username]
  Add a sub-admin by username (sysadmin only).
  Example: /add_admin @jessethan
  Or: Reply to a message and use /add_admin (no argument needed)

/remove_admin [@username]
  Remove a sub-admin by username (sysadmin only).
  Example: /remove_admin @jessethan
  Or: Reply to a message and use /remove_admin (no argument needed)

/list_admins
  List all admins (sysadmin only).
"""
    else:
        message = """
📚 Available Commands:

/start - Start the bot
/help - Show this help message
"""
    
    await update.message.reply_text(message)


@require_admin
async def complete_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /complete_payment command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide payment IDs.\n"
            "Usage: /complete_payment <paymentId1> [paymentId2] [paymentId3] ...\n"
            "Example: /complete_payment abc-123-def-456 xyz-789-uvw-012"
        )
        return
    
    payment_ids = context.args
    
    # Validate payment IDs format (basic UUID validation)
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    invalid_ids = [pid for pid in payment_ids if not uuid_pattern.match(pid)]
    if invalid_ids:
        await update.message.reply_text(
            f"❌ Invalid payment ID format: {', '.join(invalid_ids)}\n"
            "Payment IDs must be valid UUIDs."
        )
        return
    
    try:
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Process payments
            result = complete_payments(db, payment_ids)
            
            if result['success']:
                summary = result['summary']
                message = f"✅ {result['message']}\n\n"
                message += f"Summary:\n"
                message += f"  • Total: {summary['total']}\n"
                message += f"  • Completed: {summary['completed']}\n"
                message += f"  • Not found: {summary['not_found']}\n"
                message += f"  • Errors: {summary['errors']}\n"
                
                # Show details for each payment
                if result['results']:
                    message += "\nDetails:\n"
                    for res in result['results']:
                        if res['status'] == 'completed':
                            already = " (was already completed)" if res.get('wasAlreadyCompleted') else ""
                            message += f"  ✅ {res['paymentId']}{already}\n"
                        elif res['status'] == 'not_found':
                            message += f"  ⚠️ {res['paymentId']} - Not found\n"
                        elif res['status'] == 'error':
                            message += f"  ❌ {res['paymentId']} - Error: {res.get('error', 'Unknown')}\n"
            else:
                message = f"❌ {result['message']}"
            
            await update.message.reply_text(message)
        finally:
            # Close database session
            db.close()
        
    except Exception as e:
        logger.error(f"Error completing payments: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ An error occurred while processing payments: {str(e)}"
        )


@require_sysadmin
async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add_admin command (sysadmin only)."""
    try:
        username_to_add = None
        username_display = None
        
        # Priority 1: Check if message is a reply - use username from replied message
        if update.message.reply_to_message and update.message.reply_to_message.from_user:
            replied_user = update.message.reply_to_message.from_user
            replied_username = replied_user.username
            
            if not replied_username:
                await update.message.reply_text(
                    "❌ The user you replied to doesn't have a username.\n"
                    "Please use /add_admin @username instead, or ask the user to set a username."
                )
                return
            
            username_to_add = replied_username
            username_display = f"@{replied_username}"
            logger.info(f"Using username from replied message: @{replied_username}")
        
        # Priority 2: If not a reply, require argument
        if username_to_add is None:
            if not context.args or len(context.args) != 1:
                await update.message.reply_text(
                    "❌ Please provide a username, or reply to a message.\n"
                    "Usage:\n"
                    "- /add_admin @username (e.g., /add_admin @jessethan)\n"
                    "- Reply to a message and use /add_admin (no argument needed)"
                )
                return
            
            arg = context.args[0].strip()
            
            # Must be a username (starts with @)
            if not arg.startswith('@'):
                await update.message.reply_text(
                    "❌ Please provide a username starting with @.\n"
                    "Usage: /add_admin @username (e.g., /add_admin @jessethan)\n"
                    "Or: Reply to a message and use /add_admin"
                )
                return
            
            username_to_add = arg[1:]  # Remove @
            username_display = f"@{username_to_add}"
            logger.info(f"Adding admin by username: @{username_to_add}")
        
        # Check if trying to add sysadmin (by checking if username matches sysadmin's username)
        # Note: We can't easily check this, so we'll skip this check for now
        # The sysadmin is identified by user_id, not username
        
        # Add admin by username
        if admin_manager.add_admin(username_to_add):
            await update.message.reply_text(
                f"✅ {username_display} has been added as an admin."
            )
        else:
            await update.message.reply_text(
                f"⚠️ {username_display} is already an admin."
            )
    except Exception as e:
        logger.error(f"Error in add_admin_command: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ An error occurred: {str(e)}"
        )


@require_sysadmin
async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /remove_admin command (sysadmin only)."""
    try:
        username_to_remove = None
        username_display = None
        
        # Priority 1: Check if message is a reply - use username from replied message
        if update.message.reply_to_message and update.message.reply_to_message.from_user:
            replied_user = update.message.reply_to_message.from_user
            replied_username = replied_user.username
            
            if not replied_username:
                await update.message.reply_text(
                    "❌ The user you replied to doesn't have a username.\n"
                    "Please use /remove_admin @username instead."
                )
                return
            
            username_to_remove = replied_username
            username_display = f"@{replied_username}"
            logger.info(f"Using username from replied message: @{replied_username}")
        
        # Priority 2: If not a reply, require argument
        if username_to_remove is None:
            if not context.args or len(context.args) != 1:
                await update.message.reply_text(
                    "❌ Please provide a username, or reply to a message.\n"
                    "Usage:\n"
                    "- /remove_admin @username (e.g., /remove_admin @jessethan)\n"
                    "- Reply to a message and use /remove_admin (no argument needed)"
                )
                return
            
            arg = context.args[0].strip()
            
            # Must be a username (starts with @)
            if not arg.startswith('@'):
                await update.message.reply_text(
                    "❌ Please provide a username starting with @.\n"
                    "Usage: /remove_admin @username (e.g., /remove_admin @jessethan)\n"
                    "Or: Reply to a message and use /remove_admin"
                )
                return
            
            username_to_remove = arg[1:]  # Remove @
            username_display = f"@{username_to_remove}"
            logger.info(f"Removing admin by username: @{username_to_remove}")
        
        # Remove admin by username
        if admin_manager.remove_admin(username_to_remove):
            await update.message.reply_text(
                f"✅ {username_display} has been removed from admins."
            )
        else:
            await update.message.reply_text(
                f"⚠️ {username_display} is not an admin."
            )
    except Exception as e:
        logger.error(f"Error in remove_admin_command: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ An error occurred: {str(e)}"
        )


@require_sysadmin
async def list_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list_admins command (sysadmin only)."""
    admins = admin_manager.list_admins()
    
    message = "👥 Admin List:\n\n"
    message += f"System Admin: User ID {SYSADMIN_USER_ID}\n"
    
    if admins:
        message += "\nSub-Admins (by username):\n"
        for username in sorted(admins):
            message += f"  • @{username}\n"
    else:
        message += "\nNo sub-admins added yet."
    
    await update.message.reply_text(message)


def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment variables")
        return
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("complete_payment", complete_payment_command))
    application.add_handler(CommandHandler("add_admin", add_admin_command))
    application.add_handler(CommandHandler("remove_admin", remove_admin_command))
    application.add_handler(CommandHandler("list_admins", list_admins_command))
    
    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()


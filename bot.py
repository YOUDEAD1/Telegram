import os
import sys
import logging
from config.config import BOT_TOKEN as TELEGRAM_BOT_TOKEN, API_ID, API_HASH
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from handlers.start_help_handlers import StartHelpHandlers
from handlers.auth_handlers import AuthHandlers
from handlers.group_handlers import GroupHandlers
from handlers.posting_handlers import PostingHandlers
from handlers.response_handlers import ResponseHandlers
from handlers.referral_handlers import ReferralHandlers
from handlers.session_handlers import SessionHandlers
from handlers.profile_handlers import ProfileHandlers
from handlers.subscription_handlers import SubscriptionHandlers
from handlers.admin_handlers import AdminHandlers
from handlers.monitoring_handlers import MonitoringHandlers
from utils.channel_subscription import channel_subscription
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from utils.error_handlers import setup_error_handlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

class Bot:
    def __init__(self, proxy=None):
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Initialize application with bot token
        self.application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Store proxy configuration
        self.proxy = proxy
        
        # Setup error handlers
        setup_error_handlers(self.application)
        
        # Initialize handlers
        self.init_handlers()
        
        # Flag to track if bot is running
        self.is_running = False
        
        # Log initialization
        logging.info("Bot initialized")
    
    async def global_channel_subscription_check(self, update: Update, context):
        """Global middleware to check channel subscription for all messages"""
        # Skip check for admin commands
        if update.message and update.message.text and update.message.text.startswith(('/channel_subscription', '/set_subscription', '/setchannel', '/adduser', '/removeuser', '/checkuser', '/listusers')):
            # Admin commands are exempt from channel subscription check
            return True
        
        # Skip check if no channel is set
        required_channel = channel_subscription.get_required_channel()
        if not required_channel:
            return True
        
        # Get user ID
        user_id = update.effective_user.id
        
        # Check if user is admin (from any handler that might have subscription_service)
        is_admin = False
        for handler_name in ['subscription_handlers', 'admin_handlers', 'auth_handlers']:
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                if hasattr(handler, 'subscription_service'):
                    user = handler.subscription_service.get_user(user_id)
                    if user and hasattr(user, 'is_admin') and user.is_admin:
                        is_admin = True
                        break
        
        # Admins bypass channel subscription check
        if is_admin:
            return True
        
        # Check if user is subscribed to the channel
        is_subscribed, _ = await channel_subscription.check_user_subscription(context.bot, user_id)
        
        if is_subscribed:
            # User is subscribed, allow message to proceed
            return True
        else:
            # User is not subscribed, send subscription message
            keyboard = [
                [InlineKeyboardButton("✅ اشترك في القناة", url=f"https://t.me/{required_channel[1:]}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.effective_chat.send_message(
                text=f"⚠️ يجب عليك الاشتراك في القناة {required_channel} للاستمرار في استخدام البوت.",
                reply_markup=reply_markup
            )
            # Return False to stop message processing
            return False
    
    async def check_subscription_middleware(self, update, context):
        """Middleware handler for all messages to check channel subscription"""
        # Skip updates without effective user or chat
        if not update.effective_user or not update.effective_chat:
            return
        
        # Check channel subscription
        allow_message = await self.global_channel_subscription_check(update, context)
        
        # If subscription check passed, let the message continue to other handlers
        if allow_message:
            return
    
    def init_handlers(self):
        """Initialize all handlers"""
        # Add global middleware for channel subscription check
        self.application.add_handler(
            MessageHandler(filters.ALL, self.check_subscription_middleware), 
            group=-999  # Very high priority to run before all other handlers
        )
        
        # Start and help handlers
        self.start_help_handlers = StartHelpHandlers(self.application)
        
        # Auth handlers
        self.auth_handlers = AuthHandlers(self.application, proxy=self.proxy)
        
        # Group handlers
        self.group_handlers = GroupHandlers(self.application)
        
        # Posting handlers
        self.posting_handlers = PostingHandlers(self.application)
        
        # Response handlers
        self.response_handlers = ResponseHandlers(self.application)
        
        # Referral handlers
        self.referral_handlers = ReferralHandlers(self.application)
        
        # Session handlers
        self.session_handlers = SessionHandlers(self.application)
        
        # Profile handlers
        self.profile_handlers = ProfileHandlers(self.application)
        
        # Subscription handlers
        self.subscription_handlers = SubscriptionHandlers(self.application)
        
        # Admin handlers
        self.admin_handlers = AdminHandlers(self.application)
        
        # Monitoring handlers - must be initialized last to catch all messages
        self.monitoring_handlers = MonitoringHandlers(self.application)
    
    def run(self):
        """Run the bot"""
        try:
            logger.info("Starting bot polling...")
            self.is_running = True
            self.application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Error in bot polling: {str(e)}", exc_info=True)
            self.is_running = False
        finally:
            # Ensure flag is reset if polling stops for any reason
            self.is_running = False
            logger.info("Bot polling has stopped")

def main():
    """Main function"""
    # Check if proxy is provided as command line argument
    proxy = None
    if len(sys.argv) > 1:
        proxy = sys.argv[1]
        logging.info(f"Using proxy: {proxy}")
    
    # Initialize and run bot
    print("Starting Telegram Bot...")
    bot = Bot(proxy=proxy)
    bot.run()

if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
Standalone script to run the Native AI Telegram bot
This script avoids event loop conflicts by using a simple approach
"""

import os
import sys
import logging
import asyncio
from telegram.ext import ApplicationBuilder

# Add the project root to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import our bot
from src.integration.telegram.hybrid_native_bot import HybridNativeAI

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def main():
    """Run the bot"""
    # Create the bot
    bot = HybridNativeAI()
    
    # Setup handlers
    bot.setup_handlers()
    
    # Start the bot
    logger.info("Starting Native AI Bot...")
    await bot.application.run_polling(stop_signals=None)

if __name__ == "__main__":
    # Run the bot with proper async handling
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        import traceback
        traceback.print_exc()

"""
Telegram bot Integration for Dela AI
"""

import os
import asyncio
import logging
# from datetime import datetime
# from typing import Dict, Any, List, Optional
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
import os
from dotenv import load_dotenv

load_dotenv()

from src.domains.agents.observer.ob_agent import ObserverAgent
from src.integration.telegram.message_processor import TelegramMessageProcessor
from src.integration.telegram.auth_handler import TelegramAuthHandler



logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


class DelaBot:
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        # initialize components
        self.observer_agent = ObserverAgent(agent_id="telegram_observer_001")
        self.message_processor = TelegramMessageProcessor()
        self.auth_handler = TelegramAuthHandler()
        
        # bot state
        self.application = None
        self.is_running = False
        self.processed_messages = 0
        self.learned_patterns = 0
        
        logger.info(f"DELA Bot initialized with Observer Agent: {self.observer_agent.agent_id}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        
        user = update.effective_user
        chat = update.effective_chat

        logger.info(f"Start command from user {user.id} in chat {chat.id}")

        welcome_message = """
        **DELA AI Observer Bot**

        I'm your intelligent business assistant that learns from your communication patterns.

        What I do:
        - Observe your messages and decisions
        - Learn your communication style
        - Identify automation opportunities
        - Build business intelligence

        **Commands:**
        /start - Show this message
        /status - Show learning status
        /patterns - Show learned patterns
        /help - Get help

        **Privacy:** I only observe in authorized groups where I'm explicitly added.

        Ready to start learning!
        """

        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            # fix: Use effective_message as fallback
            message = update.message or update.effective_message
            if not message:
                logger.error("No message object available in status command")
                return
            
            status = self.observer_agent.get_status()
            intelligence_summary = self.observer_agent.get_intelligence_summary()
            
            status_message = f"""
            **DELA Observer Status**

            **Agent Info:**
            - Agent ID: `{status['agent_id']}`
            - Status: `{status['status']}`
            - Last Activity: `{status['last_activity']}`

            **Learning Progress:**
            - Messages Processed: `{self.processed_messages}`
            - Patterns Learned: `{intelligence_summary.get('patterns_learned', 0)}`
            - Contacts Mapped: `{intelligence_summary.get('contacts_mapped', 0)}`
            - Decisions Analyzed: `{intelligence_summary.get('decisions_analyzed', 0)}`
            - Automation Opportunities: `{intelligence_summary.get('automation_opportunities', 0)}`

            **Intelligence Confidence:** `{intelligence_summary.get('learning_confidence', 0):.2f}`
            """
            
            await message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            try:
                message = update.message or update.effective_message
                if message:
                    await message.reply_text("Error retrieving status. Please try again.")
            except Exception as e:
                logger.error("Could not send error message to user")
        
    async def patterns_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /patterns command"""
        try:
            message = update.message or update.effective_message
            chat_id = update.effective_chat.id if update.effective_chat else None
            
            if not message and not chat_id:
                logger.error("No message or chat available for patterns command")
                return

            patterns = self.observer_agent.patterns
            
            if not patterns:
                if message:
                    await message.reply_text("No patterns learned yet. Send me some messages to analyze!")
                elif chat_id:
                    await context.bot.send_message(chat_id=chat_id, text="No patterns learned yet. Send some messages to analyze!")
                return

            # Build response
            patterns_message = "**Learned Patterns:**\n\n"
            for _, pattern in list(patterns.items())[:10]:
                patterns_message += f"**{pattern.pattern_type}**\n"
                patterns_message += f"- Confidence: `{pattern.confidence:.2f}`\n"
                patterns_message += f"- Frequency: `{pattern.frequency}`\n"
                patterns_message += f"- Last Seen: `{pattern.last_seen.strftime('%Y-%m-%d %H:%M')}`\n\n"

            if len(patterns) > 10:
                patterns_message += f"... and {len(patterns) - 10} more patterns"

            # Send reply
            if message:
                await message.reply_text(patterns_message, parse_mode='Markdown')
            elif chat_id:
                await context.bot.send_message(chat_id=chat_id, text=patterns_message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in patterns command: {e}")
            # Graceful fallback
            try:
                if message:
                    await message.reply_text("Error retrieving patterns. Please try again.")
                elif chat_id:
                    await context.bot.send_message(chat_id=chat_id, text="Error retrieving patterns. Please try again.")
            except Exception as e:
                logger.error("Could not send error message to user")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        
        try:
            # fix: Use effective_message as fallback
            message = update.message or update.effective_message
            if not message:
                logger.error("No message object available in help command")
                return
            
            help_message = """
            **DELA AI Help**

            **How DELA learns:**
            1. **Observes** your messages and communication style
            2. **Analyzes** decision patterns and business relationships
            3. **Identifies** repetitive tasks for automation
            4. **Builds** intelligence about your work patterns

            **What DELA detects:**
            - Communication tone (formal/casual)
            - Decision patterns (approve/reject)
            - Automation opportunities
            - Business relationships
            - Response templates

            **Privacy & Security:**
            - Only processes messages in authorized groups
            - Stores patterns, not personal content
            - All data encrypted and secure

            **Commands:**
            /start - Initialize bot
            /status - View learning progress
            /patterns - See learned patterns
            /help - This help message

            **Need support?** Contact your DELA administrator.
            """
            
            await message.reply_text(help_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            try:
                message = update.message or update.effective_message
                if message:
                    await message.reply_text("Error showing help. Please try again.")
            except Exception as e:
                logger.error("Could not send error message to user")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        try:
            # check authorization
            if not self.auth_handler.is_authorized(update):
                logger.warning(f"Unauthorized access attempt from user {update.effective_user.id}")
                return
            
            # process message
            processed_data = self.message_processor.process_telegram_message(update)
            
            if processed_data:
                # send to observer agent
                result = await self.observer_agent.process(
                    processed_data["input_data"],
                    processed_data["context"]
                )
                
                self.processed_messages += 1
                
                # log learning progress
                if result.get("beliefs_count", 0) > 0:
                    self.learned_patterns = result.get("beliefs_count", 0)
                    logger.info(f"Processed message from {update.effective_user.first_name}, learned {result.get('beliefs_count')} patterns")
                
                # optional: send learning feedback (uncomment for debugging)
                # if self.processed_messages % 10 == 0:  # Every 10 messages
                #     await self._send_learning_update(update)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            # don't send error messages for every failed message to avoid spam
    
    async def _send_learning_update(self, update: Update):

        try:
            message = update.message or update.effective_message
            if not message:
                logger.error("No message object available in learning update")
                return

            summary = self.observer_agent.get_intelligence_summary()
            
            update_message = f"""
            **Learning Update**

            Processed {self.processed_messages} messages
            Learned {summary.get('patterns_learned', 0)} patterns
            Confidence: {summary.get('learning_confidence', 0):.2f}

            Use /status for detailed information.
            """
            
            await message.reply_text(update_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error sending learning update: {e}")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Exception while handling an update: {context.error}")
    
    def setup_handlers(self):
        if not self.application:
            self.application = Application.builder().token(self.bot_token).build()
        
        # command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("patterns", self.patterns_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # message handler
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # error handler
        self.application.add_error_handler(self.error_handler)
        
        logger.info("Bot handlers configured successfully")
    
    async def start_bot(self):
        try:
            self.setup_handlers()
            
            logger.info("Starting DELA Bot...")
            await self.application.initialize()
            await self.application.start()
            
            # Start polling
            await self.application.updater.start_polling()
            self.is_running = True
            
            logger.info("🤖 DELA Bot is running and ready to learn!")
            
            # Keep the bot running
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
    
    async def stop_bot(self):
        try:
            logger.info("Stopping DELA Bot...")
            self.is_running = False
            
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            logger.info("DELA Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")


# main execution
async def main():
    bot = DelaBot()
    
    try:
        await bot.start_bot()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        await bot.stop_bot()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await bot.stop_bot()


if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import logging
from telegram import Bot
from telegram.ext import Application
import os

from src.domains.agents.communication.proactive_agent import ProactiveCommunicationAgent, ProactiveScheduler

logger = logging.getLogger(__name__)

class ProactiveTelegramBot:
    """Production Telegram bot with proactive communications"""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.bot = Bot(token=self.bot_token)
        self.proactive_agent = ProactiveCommunicationAgent()
        self.scheduler = ProactiveScheduler(self.proactive_agent)
        
    async def start_proactive_mode(self):
        """Start proactive communication mode"""
        logger.info("🚀 Starting Native IQ Proactive Mode")
        
        # Start the scheduler in background
        asyncio.create_task(self.scheduler.start())
        
        # Send startup message to admin
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if admin_chat_id:
            await self.bot.send_message(
                chat_id=admin_chat_id,
                text="🚀 Native IQ is now active and ready to help! I'll proactively assist with meetings, automations, and important tasks."
            )
        
        logger.info("✅ Native IQ Proactive Mode started successfully")
    
    async def trigger_proactive_event(self, event_type: str, event_data: dict):
        """Manually trigger a proactive event (for testing/demo)"""
        context = {
            event_type: [event_data]
        }
        
        beliefs = await self.proactive_agent.perceive([], context)
        desires = await self.proactive_agent.update_desires(beliefs, context)
        intentions = await self.proactive_agent.deliberate(beliefs, desires, [])
        
        for intention in intentions:
            result = await self.proactive_agent.act(intention, context)
            logger.info(f"Proactive event triggered: {result}")

# Production startup function
async def start_native_proactive():
    """Start Native IQ in proactive mode for production"""
    bot = ProactiveTelegramBot()
    await bot.start_proactive_mode()
    
    # Keep running
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(start_native_proactive())
"""
Hybrid Native AI Telegram Bot
Combines silent learning with interactive chat capabilities
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

from src.domains.agents.observer.ob_agent import ObserverAgent
from src.domains.agents.analyzer.analyzer_agent import AnalyzerAgent
from src.domains.agents.decision.decision_agent import DecisionAgent
from src.domains.agents.execution.execution_agent import ExecutionAgent
from src.domains.agents.communication.proactive_agent import ProactiveCommunicationAgent
from src.integration.telegram.message_processor import TelegramMessageProcessor
from src.integration.telegram.auth_handler import TelegramAuthHandler as AuthHandler

logger = logging.getLogger(__name__)

class HybridNativeAI:
    """
    Native AI with dual learning modes:
    1. Silent Learning: Observes conversations without responding
    2. Interactive Chat: Direct conversation with users for automation
    """
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.application = Application.builder().token(self.bot_token).build()
        
        # Initialize all 4 agents
        self.observer_agent = ObserverAgent()
        self.analyzer_agent = AnalyzerAgent()
        self.decision_agent = DecisionAgent()
        self.execution_agent = ExecutionAgent()
        self.proactive_agent = ProactiveCommunicationAgent()
        
        # Utilities
        self.message_processor = TelegramMessageProcessor()
        self.auth_handler = AuthHandler()
        
        # Learning modes
        self.silent_mode = True  # Default to silent learning
        self.interactive_users = set()  # Users who can chat directly
        
        # Stats
        self.silent_messages_learned = 0
        self.interactive_conversations = 0
        
        logger.info("🤖 Hybrid Native AI initialized with dual learning modes")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - explains both modes"""
        user = update.effective_user
        
        welcome_message = f"""
🤖 **Native AI - Your Intelligent Business Assistant**

Hi {user.first_name}! I operate in **two learning modes**:

**🤫 Silent Learning Mode** (Default)
- I quietly observe your conversations
- Learn patterns, relationships, and automation opportunities  
- No responses, just intelligent learning
- Building your business intelligence database

**💬 Interactive Chat Mode** 
- Direct conversation with me for automation requests
- Ask me to automate tasks, schedule meetings, send reminders
- Get instant help with business processes
- Proactive suggestions and assistance

**Commands:**
/chat - Switch to interactive mode with me
/silent - Return to silent learning mode  
/status - See what I've learned
/automate - Request specific automation
/help - Full command list

**Current Mode**: {'🤫 Silent Learning' if self.silent_mode else '💬 Interactive Chat'}

Ready to make your business more intelligent! 🚀
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Switch to interactive chat mode"""
        user = update.effective_user
        self.interactive_users.add(user.id)
        
        await update.message.reply_text(
            f"💬 **Interactive Mode Activated!**\n\n"
            f"Hi {user.first_name}! I'm now ready to chat with you directly.\n\n"
            f"**What I can help with:**\n"
            f"• Automate repetitive tasks\n"
            f"• Schedule meetings and reminders\n"
            f"• Analyze your business patterns\n"
            f"• Suggest process improvements\n"
            f"• Execute approved automations\n\n"
            f"**Just tell me what you need!** 🚀\n\n"
            f"Type `/silent` to return to silent learning mode.",
            parse_mode='Markdown'
        )

    async def silent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Switch to silent learning mode"""
        user = update.effective_user
        self.interactive_users.discard(user.id)
        
        await update.message.reply_text(
            f"🤫 **Silent Learning Mode Activated!**\n\n"
            f"I'll now quietly observe and learn from conversations without responding.\n\n"
            f"**What I'm learning:**\n"
            f"• Communication patterns\n"
            f"• Business relationships\n"
            f"• Decision patterns\n"
            f"• Automation opportunities\n\n"
            f"Type `/chat` anytime to talk with me directly! 🤖",
            parse_mode='Markdown'
        )

    async def automate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle automation requests"""
        user = update.effective_user
        request_text = ' '.join(context.args) if context.args else ""
        
        if not request_text:
            await update.message.reply_text(
                "🤖 **Automation Request**\n\n"
                "Please describe what you'd like me to automate:\n\n"
                "**Examples:**\n"
                "• `/automate schedule weekly team meeting`\n"
                "• `/automate send reminder for project deadline`\n"
                "• `/automate follow up on pending approvals`\n\n"
                "**Or just tell me in your own words what you need!** 💡"
            )
            return
        
        # Process automation request through the 4-agent pipeline
        await self._process_automation_request(update, request_text)

    async def _process_automation_request(self, update: Update, request: str):
        """Process automation request through DELA pipeline"""
        try:
            user = update.effective_user
            
            # Step 1: Observer processes the request
            input_data = {
                "message": request,
                "metadata": {
                    "source": "telegram_automation_request",
                    "user_id": user.id,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            context = {
                "message_type": "automation_request",
                "user": user.first_name,
                "priority": "high"
            }
            
            # Run through 4-agent pipeline
            await update.message.reply_text("🔄 **Processing your automation request...**")
            
            # Convert to BaseMessage for Observer Agent
            from langchain_core.messages import HumanMessage
            message = HumanMessage(content=request)
            
            # Observer
            observer_beliefs = await self.observer_agent.perceive([message], context)
            
            # Analyzer  
            analyzer_beliefs = await self.analyzer_agent.perceive(observer_beliefs, context)
            analyzer_desires = await self.analyzer_agent.update_desires(analyzer_beliefs, context)
            analyzer_intentions = await self.analyzer_agent.deliberate(analyzer_beliefs, analyzer_desires, [])
            
            for intention in analyzer_intentions:
                await self.analyzer_agent.act(intention, context)
            
            # Decision
            decision_beliefs = await self.decision_agent.perceive(self.analyzer_agent.beliefs, context)
            decision_desires = await self.decision_agent.update_desires(decision_beliefs, context)
            decision_intentions = await self.decision_agent.deliberate(decision_beliefs, decision_desires, [])
            
            for intention in decision_intentions:
                await self.decision_agent.act(intention, context)
            
            # Execution
            execution_beliefs = await self.execution_agent.perceive(self.decision_agent.beliefs, context)
            execution_desires = await self.execution_agent.update_desires(execution_beliefs, context)
            execution_intentions = await self.execution_agent.deliberate(execution_beliefs, execution_desires, [])
            
            results = []
            for intention in execution_intentions:
                result = await self.execution_agent.act(intention, context)
                results.append(result)
            
            # Send results back to user
            if results:
                response = f"✅ **Automation Completed!**\n\n"
                for i, result in enumerate(results, 1):
                    if result.get('action_taken'):
                        response += f"**{i}.** {result.get('description', 'Automation executed')}\n"
                        response += f"⏰ Time saved: {result.get('time_saved', 0)} minutes\n\n"
                
                response += f"🎯 **Total automations**: {len(results)}\n"
                response += f"📈 **Business impact**: Improved efficiency and reduced manual work!"
            else:
                response = "🤔 **Analysis Complete**\n\nI've analyzed your request and learned from it. The automation opportunity has been noted for future implementation."
            
            await update.message.reply_text(response, parse_mode='Markdown')
            self.interactive_conversations += 1
            
        except Exception as e:
            logger.error(f"Error processing automation request: {e}")
            await update.message.reply_text(
                "❌ **Error Processing Request**\n\n"
                "I encountered an issue processing your automation request. "
                "Please try again or contact support."
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all messages - silent learning or interactive chat"""
        user = update.effective_user
        message = update.message
        
        # Skip if no text
        if not message or not message.text:
            return
        
        # Check if user is in interactive mode
        if user.id in self.interactive_users:
            await self._handle_interactive_message(update, context)
        else:
            await self._handle_silent_learning(update, context)

    async def _handle_interactive_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle interactive chat messages"""
        user = update.effective_user
        message_text = update.message.text
        
        # Generate intelligent response using proactive agent
        proactive_context = {
            "message_type": "interactive_chat",
            "user_message": message_text,
            "user_name": user.first_name,
            "conversation_type": "automation_assistance"
        }
        
        # Convert to BaseMessage for Proactive Agent
        from langchain_core.messages import HumanMessage
        user_message = HumanMessage(content=message_text)
        
        # Use proactive agent to generate response
        beliefs = await self.proactive_agent.perceive([user_message], proactive_context)
        desires = await self.proactive_agent.update_desires(beliefs, proactive_context)
        intentions = await self.proactive_agent.deliberate(beliefs, desires, [])
        
        response_sent = False
        for intention in intentions:
            result = await self.proactive_agent.act(intention, proactive_context)
            if result.get('message_sent'):
                response_sent = True
                break
        
        # Fallback response if proactive agent doesn't respond
        if not response_sent:
            await update.message.reply_text(
                f"🤖 I understand you're looking for help with: *{message_text}*\n\n"
                f"I'm analyzing this and learning from your request. "
                f"For specific automations, try `/automate {message_text}` or describe what you'd like me to automate! 💡",
                parse_mode='Markdown'
            )
        
        self.interactive_conversations += 1

    async def _handle_silent_learning(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle silent learning from conversations"""
        # Process message for learning without responding
        processed_data = self.message_processor.process_telegram_message(update)
        
        if processed_data:
            # Convert to BaseMessage for Observer Agent
            from langchain_core.messages import HumanMessage
            message = HumanMessage(content=processed_data['input_data']['message'])
            
            # Feed to Observer Agent for silent learning
            await self.observer_agent.perceive([message], processed_data['context'])
            self.silent_messages_learned += 1
            
            # Log learning (but don't respond to user)
            logger.info(f"Silent learning: processed message from {update.effective_user.first_name}")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show learning status"""
        observer_summary = self.observer_agent.get_intelligence_summary()
        
        status_message = f"""
🤖 **Native AI Learning Status**

**Learning Modes:**
• 🤫 Silent messages learned: {self.silent_messages_learned}
• 💬 Interactive conversations: {self.interactive_conversations}

**Intelligence Gathered:**
• 🧠 Patterns learned: {observer_summary.get('patterns_learned', 0)}
• 👥 Contacts mapped: {observer_summary.get('contacts_mapped', 0)}
• 🔄 Automation opportunities: {len(self.analyzer_agent.automation_opportunities)}
• 🎯 Decisions made: {len(self.decision_agent.decisions)}
• ⚡ Executions completed: {len(self.execution_agent.executions)}

**Current Mode**: {'🤫 Silent Learning' if update.effective_user.id not in self.interactive_users else '💬 Interactive Chat'}

**Business Intelligence**: Ready to automate and optimize your workflows! 🚀
        """
        
        await update.message.reply_text(status_message, parse_mode='Markdown')

    def setup_handlers(self):
        """Setup command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("chat", self.chat_command))
        self.application.add_handler(CommandHandler("silent", self.silent_command))
        self.application.add_handler(CommandHandler("automate", self.automate_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Handle all text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_bot(self):
        """Start the hybrid Native AI bot"""
        try:
            self.setup_handlers()
            
            logger.info("🚀 Starting Hybrid Native AI...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("🤖 Hybrid Native AI is running with dual learning modes!")
            logger.info("🤫 Silent Learning: ON | 💬 Interactive Chat: Available")
            
            # Keep running
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting bot: {e}")

# Main execution
async def main():
    bot = HybridNativeAI()
    await bot.start_bot()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
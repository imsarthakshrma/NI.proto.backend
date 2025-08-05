"""
Hybrid Native AI Telegram Bot
Combines silent learning with interactive chat capabilities
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
import json
from collections import defaultdict, deque

from src.domains.agents.observer.ob_agent import ObserverAgent
from src.domains.agents.analyzer.analyzer_agent import AnalyzerAgent
from src.domains.agents.decision.decision_agent import DecisionAgent
from src.domains.agents.execution.execution_agent import ExecutionAgent
from src.domains.agents.communication.proactive_agent import ProactiveCommunicationAgent
from src.domains.agents.conversation.proactive_conversation_engine import ProactiveConversationEngine, ProactiveScheduler, ConversationTrigger
from src.integration.telegram.message_processor import TelegramMessageProcessor
from src.integration.telegram.auth_handler import TelegramAuthHandler as AuthHandler

logger = logging.getLogger(__name__)

class ConversationMemory:
    """Local memory system for conversation context"""
    
    def __init__(self, max_messages_per_user: int = 50):
        self.conversations: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_messages_per_user))
        self.user_profiles: Dict[str, Dict] = {}
        self.memory_file = "data/conversation_memory.json"
        self.load_memory()
    
    def add_message(self, user_id: str, message: str, is_user: bool = True, reply_to: str = None):
        """Add a message to conversation history"""
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "content": message,
            "is_user": is_user,
            "reply_to": reply_to
        }
        self.conversations[user_id].append(message_data)
        self.save_memory()
    
    def get_conversation_context(self, user_id: str, last_n: int = 10) -> List[Dict]:
        """Get recent conversation context"""
        return list(self.conversations[user_id])[-last_n:]
    
    def update_user_profile(self, user_id: str, profile_data: Dict):
        """Update user profile information"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {}
        self.user_profiles[user_id].update(profile_data)
        self.save_memory()
    
    def get_user_profile(self, user_id: str) -> Dict:
        """Get user profile"""
        return self.user_profiles.get(user_id, {})
    
    def save_memory(self):
        """Save memory to file"""
        try:
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            memory_data = {
                "conversations": {k: list(v) for k, v in self.conversations.items()},
                "user_profiles": self.user_profiles
            }
            with open(self.memory_file, 'w') as f:
                json.dump(memory_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
    
    def load_memory(self):
        """Load memory from file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    memory_data = json.load(f)
                    for user_id, messages in memory_data.get("conversations", {}).items():
                        self.conversations[user_id] = deque(messages, maxlen=50)
                    self.user_profiles = memory_data.get("user_profiles", {})
        except Exception as e:
            logger.error(f"Error loading memory: {e}")


class HybridNativeAI:
    """
    Native AI with dual learning modes:
    1. Silent Learning: Observes conversations without responding
    2. Interactive Chat: Direct conversation with users for automation
    """
    
    def __init__(self, 
                 observer_agent: ObserverAgent, 
                 analyzer_agent: AnalyzerAgent, 
                 decision_agent: DecisionAgent, 
                 execution_agent: ExecutionAgent, 
                 proactive_agent: ProactiveCommunicationAgent, 
                 proactive_conversation_engine: ProactiveConversationEngine, 
                 auth_handler: AuthHandler, 
                 application: Application):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.application = application
        
        # Initialize all 4 agents
        self.observer_agent = observer_agent
        self.analyzer_agent = analyzer_agent
        self.decision_agent = decision_agent
        self.execution_agent = execution_agent
        self.proactive_agent = proactive_agent
        self.proactive_conversation_engine = proactive_conversation_engine
        self.proactive_scheduler = ProactiveScheduler(self.proactive_conversation_engine)
        
        # Utilities
        self.message_processor = TelegramMessageProcessor()
        self.auth_handler = auth_handler
        
        # Learning modes
        self.silent_mode = True  # Default to silent learning
        self.interactive_users = set()  # Users who can chat directly
        
        # Stats
        self.silent_messages_learned = 0
        self.interactive_conversations = 0
        
        # Conversation memory
        self.conversation_memory = ConversationMemory()
        
        # Native's capabilities - what Native knows it can do
        self.capabilities = {
            "automation": {
                "description": "I can automate repetitive tasks and workflows",
                "tools": ["Observer Agent", "Analyzer Agent", "Decision Agent", "Execution Agent"],
                "examples": ["Schedule meetings", "Send reminders", "Follow up on emails", "Generate reports"]
            },
            "communication": {
                "description": "I can manage your communications and relationships",
                "tools": ["Proactive Communication Agent", "Telegram Integration"],
                "examples": ["Draft emails", "Send notifications", "Manage contacts", "Schedule calls"]
            },
            "analysis": {
                "description": "I can analyze patterns and provide business insights",
                "tools": ["Pattern Detection", "Business Intelligence", "Data Analysis"],
                "examples": ["Communication patterns", "Workflow optimization", "Time tracking", "ROI analysis"]
            },
            "scheduling": {
                "description": "I can manage your calendar and time",
                "tools": ["Calendar Integration", "Smart Scheduling", "Conflict Detection"],
                "examples": ["Book meetings", "Find free slots", "Reschedule conflicts", "Time blocking"]
            },
            "learning": {
                "description": "I continuously learn from your interactions",
                "tools": ["Silent Learning", "Pattern Recognition", "Preference Learning"],
                "examples": ["Learn your preferences", "Adapt to your style", "Improve suggestions", "Remember context"]
            }
        }
        
        logger.info("🤖 Hybrid Native AI initialized with dual learning modes")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - auto-activates all Native intelligence"""
        user = update.effective_user
        
        # Auto-activate user for interactive mode
        self.interactive_users.add(user.id)
        
        welcome_message = f"""
    **Native AI - Your Intelligent Co-Founder**

    Hi {user.first_name}! I'm now **fully activated** and ready to automate your business!

    ** What I'm doing right now:**
    **Learning** from your conversations and patterns
    **Monitoring** for automation opportunities  
    **Ready** to execute tasks when you ask
    **Scheduled** to give you proactive insights

    **Just talk to me naturally:**
    - "Schedule a meeting with Sarah tomorrow at 2pm"
    - "Remind me to follow up with the client next week"  
    - "Automate my weekly status reports"
    - "What patterns have you noticed in my work?"

    **I'll proactively help by:**
    - Morning briefings with your day ahead
    - Suggesting automations I discover
    - Reminding you of follow-ups
    - Coordinating your schedule and tasks

    **No commands needed - just chat with me like a co-founder!** 🎯

    *What would you like me to help automate today?*
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
        # start proactive monitoring for this user
        await self.proactive_scheduler.add_trigger(
            trigger_type=ConversationTrigger.TIME_BASED,
            conditions={"morning_briefing": True},
            user_id=str(user.id)
        )

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
                response = f"**Automation Completed!**\n\n"
                for i, result in enumerate(results, 1):
                    if result.get('action_taken'):
                        response += f"**{i}.** {result.get('description', 'Automation executed')}\n"
                        response += f"⏰ Time saved: {result.get('time_saved', 0)} minutes\n\n"
                
                response += f"**Total automations**: {len(results)}\n"
                response += f"**Business impact**: Improved efficiency and reduced manual work!"
            else:
                response = "**Analysis Complete**\n\nI've analyzed your request and learned from it. The automation opportunity has been noted for future implementation."
            
            await update.message.reply_text(response, parse_mode='Markdown')
            self.interactive_conversations += 1
            
        except Exception as e:
            logger.error(f"Error processing automation request: {e}")
            await update.message.reply_text(
                "**Error Processing Request**\n\n"
                "I encountered an issue processing your automation request. "
                "Please try again or contact support."
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all incoming messages intelligently"""
        if not self.auth_handler.is_authorized(update):
            return
        
        user = update.effective_user
        user_id = str(user.id)
        
        # Handle message replies
        replied_message = None
        if update.message.reply_to_message:
            replied_message = update.message.reply_to_message.text
        
        # Store user message in conversation memory
        self.conversation_memory.add_message(
            user_id, 
            update.message.text, 
            is_user=True, 
            reply_to=replied_message
        )
        
        # Update user profile
        self.conversation_memory.update_user_profile(user_id, {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "last_seen": datetime.now().isoformat()
        })
        
        # Route based on learning mode
        if user.id in self.interactive_users:
            await self._handle_conversational_message(update, context)
        else:
            await self._handle_silent_learning(update, context)

    async def _handle_conversational_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle conversational messages like JARVIS - natural and intelligent"""
        user = update.effective_user
        user_id = str(user.id)
        message_text = update.message.text
        
        logger.info(f"🔍 _handle_conversational_message called for user {user_id}: {message_text}")
        
        # Show typing indicator immediately
        await self._show_typing(update)
        
        # Get conversation context
        conversation_context = self.conversation_memory.get_conversation_context(user_id, last_n=10)
        user_profile = self.conversation_memory.get_user_profile(user_id)
        
        # Handle message replies
        replied_to = None
        if update.message.reply_to_message:
            replied_to = update.message.reply_to_message.text
        
        # Create rich context for the proactive agent
        rich_context = {
            "message_type": "conversational_chat",
            "user_message": message_text,
            "user_name": user.first_name,
            "user_profile": user_profile,
            "conversation_history": conversation_context,
            "replied_to_message": replied_to,
            "native_capabilities": self.capabilities,
            "conversation_type": "natural_conversation",
            "system_status": {
                "learning_mode": "interactive",
                "messages_learned": self.silent_messages_learned,
                "conversations_count": self.interactive_conversations
            }
        }
        
        # Convert to BaseMessage for Proactive Agent
        from langchain_core.messages import HumanMessage
        user_message = HumanMessage(content=message_text)
        
        # Check if this is a task request that needs actual execution
        task_keywords = ['schedule', 'book', 'create', 'send', 'automate', 'set up', 'remind', 'follow up', 'execute', 'do', 'make', 'call', 'email']
        is_task_request = any(keyword in message_text.lower() for keyword in task_keywords)
        
        if is_task_request:
            # logger.info(f"🔧 Task request detected: {message_text}")
            # Show typing again for longer processing
            await self._show_typing(update)
            # Route to DELA pipeline for actual task execution
            await self._execute_task_request(update, message_text, rich_context)
            response_sent = True
            native_response = "Task processing initiated"
        else:
            # logger.info(f"💬 Conversational message detected: {message_text}")
            # Use proactive agent to generate natural response
            try:
                # Show typing before each major processing step
                await self._show_typing(update)
                
                # logger.info(f"🔍 Calling proactive_agent.perceive...")
                beliefs = await self.proactive_agent.perceive([user_message], rich_context)
                # logger.info(f"🔍 Beliefs generated: {len(beliefs)} beliefs")
                
                await self._show_typing(update)  # Show typing again
                
                # logger.info(f"🔍 Calling proactive_agent.update_desires...")
                desires = await self.proactive_agent.update_desires(beliefs, rich_context)
                # logger.info(f"🔍 Desires generated: {len(desires)} desires")
                
                await self._show_typing(update)  # Show typing again
                
                # logger.info(f"🔍 Calling proactive_agent.deliberate...")
                intentions = await self.proactive_agent.deliberate(beliefs, desires, [])
                # logger.info(f"🔍 Intentions generated: {len(intentions)} intentions")
                
                response_sent = False
                native_response = None
                
                # logger.info(f"Processing {len(intentions)} intentions...")
                for i, intention in enumerate(intentions):
                    logger.info(f"Processing intention {i+1}: {intention.action_type}")
                    result = await self.proactive_agent.act(intention, rich_context)
                    # logger.info(f"Act result: {result}")
                    if result.get('message_sent'):
                        native_response = result.get('message_sent')
                        # logger.info(f"Sending reply: {native_response}")
                        await update.message.reply_text(native_response)
                        response_sent = True
                        break
            except Exception as e:
                logger.error(f"Error in conversational processing: {e}")
                response_sent = False
                
        # Store Native's response in conversation memory
        if native_response and native_response != "Task processing initiated":
            self.conversation_memory.add_message(
                user_id, 
                native_response, 
                is_user=False, 
                reply_to=message_text if replied_to else None
            )
        
        # Fallback if no response was sent
        if not response_sent:
            fallback_response = f"I'm analyzing that from a business operations perspective, {user.first_name}. Let me determine the best way to assist you with this."
            await update.message.reply_text(fallback_response)
            self.conversation_memory.add_message(user_id, fallback_response, is_user=False)
        
        self.interactive_conversations += 1

    async def _execute_task_request(self, update: Update, request_text: str, context: Dict[str, Any]):
        """Execute actual tasks through the DELA pipeline"""
        try:
            user = update.effective_user
            logger.info(f"🚀 Executing task request: {request_text}")
            
            # show typing and send immediate acknowledgment
            await self._show_typing(update)
            await update.message.reply_text(f"🚀 **Processing your request...**\n\n*{request_text}*\n\nI'm routing this through my automation pipeline to actually execute it.", parse_mode='Markdown')
            
            # convert to BaseMessage for DELA pipeline
            from langchain_core.messages import HumanMessage
            message = HumanMessage(content=request_text)
            
            # create context for task execution
            task_context = {
                "message_type": "task_execution",
                "user": user.first_name,
                "user_id": user.id,
                "priority": "high",
                "source": "telegram_task_request",
                "timestamp": datetime.now().isoformat()
            }
            
            # show typing during processing
            await self._show_typing(update)
            
            # run through DELA pipeline for actual execution
            logger.info(f"🔍 Step 1: Observer Agent processing...")
            observer_beliefs = await self.observer_agent.perceive([message], task_context)
            
            await self._show_typing(update)
            
            logger.info(f"🔍 Step 2: Analyzer Agent processing...")
            analyzer_beliefs = await self.analyzer_agent.perceive(observer_beliefs, task_context)
            analyzer_desires = await self.analyzer_agent.update_desires(analyzer_beliefs, task_context)
            analyzer_intentions = await self.analyzer_agent.deliberate(analyzer_beliefs, analyzer_desires, [])
            
            for intention in analyzer_intentions:
                await self.analyzer_agent.act(intention, task_context)
            
            await self._show_typing(update)
            
            logger.info(f"🔍 Step 3: Decision Agent processing...")
            decision_beliefs = await self.decision_agent.perceive(self.analyzer_agent.beliefs, task_context)
            decision_desires = await self.decision_agent.update_desires(decision_beliefs, task_context)
            decision_intentions = await self.decision_agent.deliberate(decision_beliefs, decision_desires, [])
            
            for intention in decision_intentions:
                await self.decision_agent.act(intention, task_context)
            
            await self._show_typing(update)
            
            logger.info(f"🔍 Step 4: Execution Agent processing...")
            execution_beliefs = await self.execution_agent.perceive(self.decision_agent.beliefs, task_context)
            execution_desires = await self.execution_agent.update_desires(execution_beliefs, task_context)
            execution_intentions = await self.execution_agent.deliberate(execution_beliefs, execution_desires, [])
            
            results = []
            for intention in execution_intentions:
                result = await self.execution_agent.act(intention, task_context)
                results.append(result)
            
            # send results back to user
            if results and any(result.get('action_taken') for result in results):
                response = f"**Task Completed Successfully!**\n\n"
                
                for i, result in enumerate(results, 1):
                    if result.get('action_taken'):
                        response += f"**{i}.** {result.get('description', 'Task executed')}\n"
                        if result.get('time_saved'):
                            response += f"⏰ Time saved: {result.get('time_saved')} minutes\n"
                        if result.get('details'):
                            response += f"📝 Details: {result.get('details')}\n"
                        response += "\n"
                
                response += f"**Total tasks completed**: {len([r for r in results if r.get('action_taken')])}\n"
                response += f"🚀 **Business impact**: Automated execution with measurable results!"
                
                await update.message.reply_text(response, parse_mode='Markdown')
                
                # store successful execution in conversation memory
                self.conversation_memory.add_message(
                    str(user.id), 
                    f"Successfully executed: {request_text}", 
                    is_user=False
                )
            else:
                # No actions were taken - provide analysis instead
                response = f"📊 **Task Analysis Complete**\n\n"
                response += f"I've analyzed your request: *{request_text}*\n\n"
                response += f"**Status**: Analyzed and learned from this request\n"
                response += f"**Next Steps**: The automation opportunity has been noted for future implementation\n\n"
                response += f"**Business Value**: Improved understanding of your workflow patterns"
                
                await update.message.reply_text(response, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error in task execution: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            error_response = f"⚠️ **Task Processing Error**\n\n"
            error_response += f"I encountered an issue while processing your request: *{request_text}*\n\n"
            error_response += f"**Error**: {str(e)}\n\n"
            error_response += f"Please try again or contact support if the issue persists."
            
            await update.message.reply_text(error_response, parse_mode='Markdown')

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
        # self.application.add_handler(CommandHandler("chat", self.chat_command))
        # self.application.add_handler(CommandHandler("silent", self.silent_command))
        self.application.add_handler(CommandHandler("automate", self.automate_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Handle all text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def run(self):
        """Start the Native AI bot"""
        logger.info("Starting Native AI Hybrid Bot...")
        
        # Setup handlers first
        self.setup_handlers()
        
        # Start polling (this will handle the event loop properly)
        await self.application.run_polling(stop_signals=None)

    def run_sync(self):
        import asyncio
        asyncio.run(self.run())

def setup_handlers(application, observer_agent, analyzer_agent, decision_agent, 
                  execution_agent, proactive_agent, proactive_conversation_engine, auth_handler):
    """Setup command and message handlers for the application"""
    
    # Create a bot instance to access handler methods
    bot = HybridNativeAI(
        observer_agent=observer_agent,
        analyzer_agent=analyzer_agent,
        decision_agent=decision_agent,
        execution_agent=execution_agent,
        proactive_agent=proactive_agent,
        proactive_conversation_engine=proactive_conversation_engine,
        auth_handler=auth_handler,
        application=application
    )
    
    # Setup handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("automate", bot.automate_command))
    application.add_handler(CommandHandler("status", bot.status_command))
    
    # Handle all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    logger.info("Handlers setup complete")
    return bot

# Main execution
def main():
    bot = HybridNativeAI(
        observer_agent=ObserverAgent(),
        analyzer_agent=AnalyzerAgent(),
        decision_agent=DecisionAgent(),
        execution_agent=ExecutionAgent(),
        proactive_agent=ProactiveCommunicationAgent(),
        proactive_conversation_engine=ProactiveConversationEngine(),
        auth_handler=AuthHandler(),
        application=Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    )
    bot.run_sync()

if __name__ == "__main__":
    main()
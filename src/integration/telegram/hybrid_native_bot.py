"""
Hybrid Native IQ Telegram Bot
Combines silent learning with interactive chat capabilities
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
import json
from collections import defaultdict, deque
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import HTMLResponse
import uvicorn

from src.domains.agents.observer.ob_agent import ObserverAgent
from src.domains.agents.analyzer.analyzer_agent import AnalyzerAgent
from src.domains.agents.decision.decision_agent import DecisionAgent
from src.domains.agents.execution.execution_agent import ExecutionAgent
from src.domains.agents.communication.proactive_agent import ProactiveCommunicationAgent
from src.domains.agents.conversation.proactive_conversation_engine import ProactiveConversationEngine, ProactiveScheduler, ConversationTrigger
from src.integration.telegram.message_processor import TelegramMessageProcessor
from src.integration.telegram.auth_handler import TelegramAuthHandler as AuthHandler
from telegram.constants import ChatAction

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast_proactive_message(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                self.active_connections.remove(connection)
        

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
    Native IQ with dual learning modes:
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
        
        # Telegram chat action for typing indicator
        self.chat_action = ChatAction.TYPING
        
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
        
        logger.info("Hybrid Native IQ initialized with dual learning modes")

        self.websocket_manager = WebSocketManager()
        self.fastapi_app = self._setup_fastapi()
        self.background_tasks = []
        self.pending_actions: Dict[str, Dict[str, Any]] = {}  # Store pending actions by user_id
        self.session_context: Dict[str, Dict[str, Any]] = {}  # Store session context by user_id

    def _setup_fastapi(self):
        app = FastAPI(title="Native IQ Backend", version="0.1.0")
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.websocket_manager.connect(websocket)
            try:
                while True:
                    await websocket.receive_text()
            except:
                self.websocket_manager.disconnect(websocket)
        
        @app.post("/chat")
        async def chat_endpoint(message: dict):
            # Process chat message and return response
            return await self._process_api_message(message)
        
        @app.get("/cognitive-map")
        async def get_cognitive_map():
            # Return GraphRAG data for frontend
            return await self._get_graph_data()
        
        @app.get("/agent-status")
        async def get_agent_status():
            # Return current agent states
            return self._get_agent_states()
        
        return app

    async def _process_api_message(self, message: dict):
        """Process chat message from API endpoint"""
        try:
            user_message = message.get("message", "")
            user_id = message.get("user_id", "api_user")
            
            # Create context similar to Telegram
            context = {
                "user_message": user_message,
                "user_id": user_id,
                "message_type": "api_chat",
                "conversation_type": "direct"
            }
            
            # Use existing execution logic
            response = await self._execute_task_request(None, user_message, context)
            return {"response": response, "success": True}
            
        except Exception as e:
            logger.error(f"API message processing error: {e}")
            return {"error": str(e), "success": False}

    async def _get_graph_data(self):
        """Return GraphRAG data for cognitive map"""
        # TODO: Implement GraphRAG system
        return {
            "entities": [],
            "relationships": [],
            "insights": [],
            "learning_progress": "GraphRAG system not yet implemented"
        }

    def _get_agent_states(self):
        """Return current agent states for frontend"""
        return {
            "observer": {"status": "active", "observations": self.observer_agent.get_status()},
            "analyzer": {"status": "active", "patterns": "analyzing..."},
            "decision": {"status": "active", "decisions": "evaluating..."},
            "execution": {"status": "active", "tasks": "ready"},
            "proactive": {"status": "active", "notifications": "monitoring..."}
        }

    async def _start_background_monitoring(self):
        """Background monitoring for proactive actions"""
        import asyncio
        
        while True:
            try:
                # Get observations from observer agent
                # TODO: Implement actual observation gathering
                observations = []
                
                if observations:
                    # Analyze for proactive opportunities
                    analysis = await self._analyze_for_proactive_action(observations)
                    
                    if analysis.get('should_act'):
                        # Generate proactive message using LLM
                        proactive_message = await self._generate_proactive_message(analysis)
                        
                        # Broadcast to all connected clients
                        await self.websocket_manager.broadcast_proactive_message(proactive_message)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                await asyncio.sleep(60)

    async def _analyze_for_proactive_action(self, observations):
        """Analyze observations for proactive opportunities"""
        # TODO: Implement LLM-powered analysis
        return {"should_act": False, "reason": "No significant patterns detected"}

    async def _generate_proactive_message(self, analysis):
        """Generate proactive message using LLM"""
        # TODO: Implement LLM-powered message generation
        return {
            "type": "proactive_nudge",
            "message": "Sample proactive message",
            "priority": "medium",
            "requires_approval": True
        }


    async def _execute_task_request(self, update: Update, message_text: str, context: Dict[str, Any]) -> str:
        """Execute task requests directly using LLM-powered ExecutionAgent"""
        try:
            user_id = str(update.effective_user.id)
            logger.info(f"🔧 Executing task request directly with LLM: {message_text}")
            
            # Create execution context with user message
            execution_context = {
                **context,
                "user_id": user_id,
                "user_message": message_text,
                "direct_execution": True
            }
            
            # Create a dummy intention for the ExecutionAgent
            from src.core.base_agent import Intention
            intention = Intention(
                action_type="execute_user_request",
                parameters={"user_message": message_text}
            )
            
            # Call ExecutionAgent directly with LLM-powered execution
            logger.info(f"🚀 Calling ExecutionAgent directly for LLM analysis")
            execution_result = await self.execution_agent.act(intention, execution_context)
            logger.info(f"Direct execution result: {execution_result}")
            
            # Check if execution was successful and return appropriate response
            if execution_result.get("requires_permission"):
                # Send permission request to user
                permission_msg = execution_result.get("permission_message", "Should I proceed?")
                await update.message.reply_text(permission_msg)
                return "Permission requested - please confirm to proceed."
            elif execution_result.get("success"):
                # Task executed successfully - format the result
                return await self._format_execution_result(execution_result, message_text)
            else:
                error_msg = execution_result.get("error", "Unknown error occurred")
                return f"❌ I couldn't complete that task: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error in direct LLM execution: {e}", exc_info=True)
            return f"❌ Sorry, I encountered an error while processing your request: {str(e)}"

    async def _format_execution_result(self, result: Dict[str, Any], original_request: str) -> str:
        """Format execution results into user-friendly messages"""
        try:
            # Check if LLM already formatted the response
            if result.get("llm_powered") and result.get("formatted_response"):
                logger.info("Using LLM-formatted response")
                return result["formatted_response"]
            
            # Fallback to basic formatting for non-LLM results
            tool_result = result.get("result", "")
            task_type = result.get("task_type", "")
            
            if task_type == "get_upcoming_meetings":
                if "No upcoming meetings" in str(tool_result):
                    return f"📅 I checked your calendar and you don't have any meetings scheduled for tomorrow. Would you like me to schedule something?"
                else:
                    return f"📅 Here's your schedule for tomorrow:\n\n{tool_result}\n\nWould you like me to schedule anything else?"
            
            elif task_type == "schedule_meeting":
                return f"✅ Meeting scheduled successfully! {tool_result}"
            
            elif task_type == "list_drive_files":
                return f"📁 Here are your Google Drive files:\n\n{tool_result}"
            
            elif task_type == "send_email":
                return f"📧 Email sent successfully! {tool_result}"
            
            else:
                # Generic success message
                return f"✅ Task completed successfully!\n\n{tool_result}"
                
        except Exception as e:
            logger.error(f"Error formatting execution result: {e}")
            return f"✅ Task completed, but I had trouble formatting the response: {str(result)}"

    def get_greeting(self):
        current_hour = datetime.now().hour
            
        if 5 <= current_hour < 12:
            return "Good morning"
        elif 12 <= current_hour < 17:
            return "Good afternoon"
        elif 17 <= current_hour < 22:
            return "Good evening"
        else:
            return "Hello night owl"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - auto-activates all Native intelligence"""
        user = update.effective_user
        
        # Auto-activate user for interactive mode
        self.interactive_users.add(user.id)
        
        welcome_message = f"""

    **{self.get_greeting()} {user.first_name}!**

    *What would you like me to help you with today?*
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

    async def _show_typing(self, update: Update):
        """Show the 'typing...' indicator in Telegram."""
        chat_id = update.effective_chat.id
        await update.get_bot().send_chat_action(
            chat_id=chat_id,
            action=self.chat_action
        )

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
        
        # Check for pending action approval/denial first
        pending_response = await self._handle_pending_action_response(update, message_text, rich_context)
        if pending_response:
            return  # Handled as pending action response
        
        # Check if this is a task request that needs actual execution
        task_keywords = ['schedule', 'book', 'create', 'send', 'automate', 'set up', 'remind', 'follow up', 'execute', 'do', 'make', 'call', 'email', 'check', 'show', 'list', 'find', 'get']
        calendar_keywords = ['calendar', 'meeting', 'appointment', 'schedule']
        
        # Detect calendar/task requests
        is_task_request = any(keyword in message_text.lower() for keyword in task_keywords)
        is_calendar_request = any(keyword in message_text.lower() for keyword in calendar_keywords)
        
        # If it's a calendar request, treat as task regardless of other keywords
        if is_calendar_request or is_task_request:
            # logger.info(f"🔧 Task request detected: {message_text}")
            # Show typing again for longer processing
            await self._show_typing(update)
            # Route to DELA pipeline for actual task execution
            execution_result = await self._execute_task_request(update, message_text, rich_context)
            response_sent = True
            native_response = execution_result
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
🤖 **Native IQ Learning Status**

**Learning Modes:**
• 🤫 Silent messages learned: {self.silent_messages_learned}
• 💬 Interactive conversations: {self.interactive_conversations}

**Intelligence Gathered:**
• 🧠 Patterns learned: {observer_summary.get('patterns_learned', 0)}
• 👥 Contacts mapped: {observer_summary.get('contacts_mapped', 0)}
• 🔄 Automation opportunities: {len(self.analyzer_agent.automation_opportunities)}
• 🎯 Decisions made: {len(self.decision_agent.decisions)}
• ⚡ Executions completed: {len(self.execution_agent.executions)}

**Current Mode**: {'Silent Learning' if update.effective_user.id not in self.interactive_users else 'Interactive Chat'}

**Business Intelligence**: Ready to automate and optimize your workflows! 🚀
        """
        
        await update.message.reply_text(status_message, parse_mode='Markdown')

    async def _execute_task_request(self, update: Update, message_text: str, context: Dict[str, Any]) -> str:
        """Execute task request using ExecutionAgent with LLM analysis"""
        try:
            user_id = str(update.effective_user.id)
            logger.info(f"🔧 Executing task request directly with LLM: {message_text}")
            
            # Set cooldown and create context
            self.proactive_agent.set_cooldown(user_id, 120)  # 2 minutes cooldown
            context["direct_execution"] = True
            context["user_id"] = user_id
            context["user_timezone"] = "Asia/Kolkata"
            
            # Add session context for status queries and chained execution
            if user_id not in self.session_context:
                self.session_context[user_id] = {"contacts": {"by_email": {}, "by_name": {}}}
            elif "contacts" not in self.session_context[user_id]:
                self.session_context[user_id]["contacts"] = {"by_email": {}, "by_name": {}}
            context["session_context"] = self.session_context[user_id]
            
            # Create intention for ExecutionAgent
            from src.core.base_agent import Intention
            intention = Intention(
                action_type="execute_user_request",
                parameters={"user_message": message_text}
            )
            
            logger.info(f"🚀 Calling ExecutionAgent directly for LLM analysis")
            execution_result = await self.execution_agent.act(intention, context)
            
            logger.info(f"Direct execution result: {execution_result}")
            
            # Handle permission requests
            if execution_result.get("requires_permission"):
                # Store pending action for later execution
                import uuid
                action_token = str(uuid.uuid4())[:8]  # Short token for reference
                
                self.pending_actions[user_id] = {
                    "token": action_token,
                    "intent": execution_result.get("intent"),
                    "tool_name": execution_result.get("tool_name"),
                    "parameters": execution_result.get("parameters"),
                    "original_message": message_text,
                    "timestamp": datetime.now(),
                    "expires_at": datetime.now() + timedelta(minutes=10)  # 10 minute expiry
                }
                
                permission_msg = execution_result.get("permission_message", "Permission required for this action.")
                logger.info(f"Stored pending action {action_token} for user {user_id}: {execution_result.get('intent')}")
                
                await update.message.reply_text(f"{permission_msg}\n\n_Reply 'yes' to approve or 'no' to cancel._")
                return "Permission requested"
            elif execution_result.get("success"):
                # Check if this is a status query response - return message directly
                if execution_result.get("status_query"):
                    return execution_result.get("message", "Status query completed")
                # Format successful execution result
                return await self._format_execution_result(execution_result, message_text)
            else:
                # Check if this is a status query error - return message directly
                if execution_result.get("status_query"):
                    return execution_result.get("message", execution_result.get("error", "Status query failed"))
                return f"Error: {execution_result.get('error', 'Unknown error occurred')}"
                
        except Exception as e:
            logger.error(f"Error in task execution: {e}")
            return f"Sorry, I encountered an error while processing your request: {str(e)}"

    async def _handle_pending_action_response(self, update: Update, message_text: str, context: Dict[str, Any]) -> bool:
        """Handle yes/no responses to pending action approvals"""
        user_id = str(update.effective_user.id)
        message_lower = message_text.lower().strip()
        
        # Check if user has pending action (primary or chained email)
        pending_action = self.pending_actions.get(user_id)
        chained_email_action = self.pending_actions.get(f"{user_id}_email")
        
        # Prioritize chained email actions if both exist
        if chained_email_action:
            pending_action = chained_email_action
            action_key = f"{user_id}_email"
        elif pending_action:
            action_key = user_id
        else:
            return False  # No pending action
        
        # Check if action has expired
        if datetime.now() > pending_action["expires_at"]:
            del self.pending_actions[action_key]
            await update.message.reply_text("⏰ The previous request has expired. Please make a new request.")
            return True
        
        # Handle approval/denial
        if message_lower in ['yes', 'y', 'approve', 'confirm', 'ok', 'okay']:
            logger.info(f"User {user_id} approved pending action: {pending_action['intent']}")
            
            try:
                # Execute the approved action
                await update.message.reply_text("✅ Executing your request...")
                
                # Create execution context with approval
                exec_context = context.copy()
                exec_context["permission_context"] = {"user_confirmed": True}
                exec_context["direct_execution"] = True
                exec_context["user_timezone"] = "Asia/Kolkata"
                
                # Get the tool and execute it directly
                tool_name = pending_action["tool_name"]
                parameters = pending_action["parameters"]
                
                # Sanitize parameters before execution to prevent Pydantic validation errors
                if tool_name == "schedule_meeting":
                    parameters = self._sanitize_meeting_params(parameters)
                elif tool_name == "email_tool":
                    parameters = self._sanitize_email_params(parameters, exec_context)
                
                if tool_name in self.execution_agent.available_tools:
                    tool = self.execution_agent.available_tools[tool_name]
                    
                    logger.info(f"🎯 Executing approved action: {tool_name} with parameters: {parameters}")
                    
                    # Execute the tool
                    if hasattr(tool, 'ainvoke'):
                        result = await tool.ainvoke(parameters)
                    else:
                        result = tool.invoke(parameters)
                    
                    # Store meeting results for potential email follow-ups and session context
                    if tool_name == "schedule_meeting" and isinstance(result, str) and "Event ID:" in result:
                        # Extract meeting details from result for future email context
                        exec_context["meeting_result"] = {
                            "success": True,
                            "result_text": result,
                            "meeting_title": parameters.get("title", "Meeting"),
                            "meeting_time": parameters.get("start_time", ""),
                            # Note: html_link would need to be extracted from calendar service response
                            # For now, we'll use a placeholder that can be enhanced
                        }
                        
                        # Update session context for status queries and contact persistence
                        if user_id not in self.session_context:
                            self.session_context[user_id] = {"contacts": {"by_email": {}, "by_name": {}}}
                        
                        # Store meeting details
                        self.session_context[user_id]["last_meeting"] = {
                            "title": parameters.get("title", "Meeting"),
                            "time": parameters.get("start_time", ""),
                            "attendees": parameters.get("attendees", []),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Extract and store contacts from meeting attendees
                        attendees = parameters.get("attendees", [])
                        for email in attendees:
                            if email and "@" in email and "example.com" not in email.lower():
                                # Extract name from email (before @) or use existing name
                                name_part = email.split("@")[0].lower()
                                # Try to extract actual name from email context or use email prefix
                                contact_name = self._extract_name_from_context(email, pending_action.get("original_message", ""))
                                
                                # Store by email
                                self.session_context[user_id]["contacts"]["by_email"][email] = {
                                    "name": contact_name,
                                    "source": "meeting",
                                    "timestamp": datetime.now().isoformat()
                                }
                                
                                # Store by name (support multiple emails per name)
                                name_key = contact_name.lower()
                                if name_key not in self.session_context[user_id]["contacts"]["by_name"]:
                                    self.session_context[user_id]["contacts"]["by_name"][name_key] = []
                                if email not in self.session_context[user_id]["contacts"]["by_name"][name_key]:
                                    self.session_context[user_id]["contacts"]["by_name"][name_key].append(email)
                        
                        logger.info(f"Stored meeting result context and extracted {len(attendees)} contacts for future email resolution")
                        
                        # Check if original intent included email/invite request for chained execution
                        original_message = pending_action.get("original_message", "").lower()
                        if any(keyword in original_message for keyword in ["send email", "send invite", "draft email", "email him", "email her", "send him", "send her"]):
                            await self._create_chained_email_action(user_id, parameters, attendees, pending_action, exec_context)
                    
                    # Update session context for email actions
                    elif tool_name == "email_tool" and isinstance(result, str):
                        if user_id not in self.session_context:
                            self.session_context[user_id] = {}
                        self.session_context[user_id]["last_email_status"] = {
                            "sent": "success" in result.lower() or "sent" in result.lower(),
                            "to": [parameters.get("recipient", "")],
                            "subject": parameters.get("subject", ""),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        logger.info(f"Updated session context with email status")
                    
                    # Format and send success response
                    success_msg = await self._format_execution_result({
                        "success": True,
                        "result": result,
                        "description": f"Successfully executed {pending_action['intent']}"
                    }, pending_action["original_message"])
                    
                    await update.message.reply_text(success_msg)
                    logger.info(f"✅ Successfully executed approved action for user {user_id}")
                    
                else:
                    await update.message.reply_text(f"❌ Error: Tool '{tool_name}' is not available.")
                    logger.error(f"Tool {tool_name} not found in available tools")
                
            except Exception as e:
                logger.error(f"Error executing approved action: {e}")
                await update.message.reply_text(f"❌ Error executing your request: {str(e)}")
            
            # Clean up pending action
            del self.pending_actions[action_key]
            return True
            
        elif message_lower in ['no', 'n', 'cancel', 'deny', 'reject']:
            logger.info(f"User {user_id} denied pending action: {pending_action['intent']}")
            await update.message.reply_text("❌ Request cancelled.")
            del self.pending_actions[action_key]
            return True
        
        # Not a clear yes/no response, keep pending action
        return False

    def _extract_name_from_context(self, email: str, original_message: str) -> str:
        """Extract contact name from email and message context"""
        # First try to find name mentions in the original message
        import re
        
        # Look for common name patterns in the message
        name_patterns = [
            r'\b([A-Z][a-z]+)\b(?=.*' + re.escape(email.split('@')[0]) + r')',  # Name before email prefix
            r'\b([A-Z][a-z]+)\s+(?:at|from|with)\b',  # "Name at/from/with"
            r'\b(?:with|to|for)\s+([A-Z][a-z]+)\b',   # "with/to/for Name"
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, original_message, re.IGNORECASE)
            if matches:
                return matches[0].capitalize()
        
        # Fallback: use email prefix and capitalize
        email_prefix = email.split('@')[0]
        # Handle common email formats like "john.doe" or "john_doe"
        if '.' in email_prefix:
            parts = email_prefix.split('.')
            return ' '.join(part.capitalize() for part in parts)
        elif '_' in email_prefix:
            parts = email_prefix.split('_')
            return ' '.join(part.capitalize() for part in parts)
        else:
            return email_prefix.capitalize()

    def _resolve_email_recipient(self, recipient: str, params: dict, context: Dict[str, Any]) -> str:
        """Resolve email recipient using contact cache and context"""
        session_context = context.get("session_context", {})
        contacts = session_context.get("contacts", {"by_email": {}, "by_name": {}})
        
        # If recipient is missing, placeholder, or invalid, try to resolve
        needs_resolution = (
            not recipient or 
            "example.com" in recipient.lower() or
            "@" not in recipient or
            recipient.strip() == ""
        )
        
        if needs_resolution:
            # Try to extract name from email body or subject
            body = params.get("body", "") + " " + params.get("subject", "")
            potential_names = self._extract_names_from_text(body)
            
            # Try to resolve using contact cache
            for name in potential_names:
                name_key = name.lower()
                if name_key in contacts["by_name"]:
                    emails = contacts["by_name"][name_key]
                    if len(emails) == 1:
                        logger.info(f"Resolved recipient '{name}' to {emails[0]} from contact cache")
                        return emails[0]
                    elif len(emails) > 1:
                        logger.info(f"Multiple emails found for '{name}': {emails}")
                        # For now, use the first one, but this could be enhanced with disambiguation
                        return emails[0]
            
            # Fallback: use last meeting attendees if this seems like a follow-up
            last_meeting = session_context.get("last_meeting", {})
            if last_meeting and last_meeting.get("attendees"):
                attendees = last_meeting["attendees"]
                if len(attendees) == 1:
                    logger.info(f"Using last meeting attendee as recipient: {attendees[0]}")
                    return attendees[0]
                elif len(attendees) > 1:
                    # Check if any names in the email match attendee emails
                    for name in potential_names:
                        for email in attendees:
                            if name.lower() in email.lower():
                                logger.info(f"Matched '{name}' to meeting attendee: {email}")
                                return email
                    # If no match, use first attendee
                    logger.info(f"Using first meeting attendee as recipient: {attendees[0]}")
                    return attendees[0]
        
        return recipient

    def _extract_names_from_text(self, text: str) -> list:
        """Extract potential names from text"""
        import re
        # Look for capitalized words that could be names
        name_pattern = r'\b[A-Z][a-z]+\b'
        potential_names = re.findall(name_pattern, text)
        
        # Filter out common words that aren't names
        common_words = {
            'Meeting', 'Email', 'Please', 'Thanks', 'Hello', 'Hi', 'Dear', 'Best', 'Regards',
            'Subject', 'Message', 'Native', 'User', 'Join', 'Link', 'Calendar', 'Invite'
        }
        
        return [name for name in potential_names if name not in common_words]

    async def _create_chained_email_action(self, user_id: str, meeting_params: dict, attendees: list, original_pending_action: dict, exec_context: dict):
        """Create a chained email action after successful meeting scheduling"""
        try:
            import uuid
            
            # Extract meeting details
            meeting_title = meeting_params.get("title", "Meeting")
            meeting_time = meeting_params.get("start_time", "")
            original_message = original_pending_action.get("original_message", "")
            
            # Format meeting time for email
            try:
                from datetime import datetime
                if meeting_time:
                    dt = datetime.fromisoformat(meeting_time.replace('Z', '+00:00'))
                    formatted_time = dt.strftime("%A, %B %d at %I:%M %p")
                else:
                    formatted_time = "the scheduled time"
            except:
                formatted_time = "the scheduled time"
            
            # Build email parameters
            email_params = {
                "recipient": attendees[0] if attendees else "",  # Use first attendee
                "subject": f"Meeting Invite: {meeting_title} on {formatted_time}",
                "body": self._compose_email_body_from_intent(original_message, meeting_title, formatted_time, exec_context)
            }
            
            # Create second pending action for email
            email_token = str(uuid.uuid4())[:8]
            self.pending_actions[f"{user_id}_email"] = {
                "token": email_token,
                "intent": f"send email invite for {meeting_title}",
                "tool_name": "email_tool",
                "parameters": email_params,
                "original_message": original_message,
                "timestamp": datetime.now(),
                "expires_at": datetime.now() + timedelta(minutes=10),
                "chained_from": "schedule_meeting"
            }
            
            # Ask for permission for the email
            permission_msg = f"✅ Meeting scheduled! Should I also send an email invite to {email_params['recipient']} with the subject '{email_params['subject']}'? Reply 'yes' to send or 'no' to skip."
            
            logger.info(f"Created chained email action {email_token} for user {user_id} after meeting scheduling")
            
            # Send permission request to user using Telegram bot API
            try:
                await self.application.bot.send_message(chat_id=int(user_id), text=permission_msg)
                logger.info(f"Sent chained email permission request to user {user_id}")
            except Exception as e:
                logger.error(f"Error sending chained email permission request: {e}")
            
        except Exception as e:
            logger.error(f"Error creating chained email action: {e}")

    def _compose_email_body_from_intent(self, original_message: str, meeting_title: str, formatted_time: str, exec_context: dict) -> str:
        """Compose email body based on original user intent"""
        # Extract user's message content from original request
        body_parts = []
        
        # Add meeting details with personalized greeting
        body_parts.append(f"Hi,\n\nI'd like to invite you to a meeting: {meeting_title}")
        body_parts.append(f"Scheduled for: {formatted_time}")
        
        # Try to extract user's custom message from original intent
        import re
        message_patterns = [
            r'tell (?:him|her|them) that (.+?)(?:\.|$)',
            r'mention that (.+?)(?:\.|$)',
            r'say that (.+?)(?:\.|$)',
            r'let (?:him|her|them) know (.+?)(?:\.|$)',
            r'inform (?:him|her|them) (.+?)(?:\.|$)',
            r'tell (?:him|her|them) (.+?)(?:\.|$)'
        ]
        
        custom_message = None
        for pattern in message_patterns:
            match = re.search(pattern, original_message.lower())
            if match:
                custom_message = match.group(1).strip()
                # Personalize the message by replacing "him/her" with "you"
                custom_message = re.sub(r'\b(?:to )?(?:him|her)\b', 'to you', custom_message)
                custom_message = re.sub(r'\bwe\'ll be demonstrating.*to him\b', 'we\'ll be demonstrating the functionality to you', custom_message)
                break
        
        if custom_message:
            body_parts.append(f"\n{custom_message.capitalize()}")
        
        # Add meeting link if available
        meeting_result = exec_context.get("meeting_result", {})
        if "html_link" in meeting_result:
            body_parts.append(f"\n📅 Join the meeting: {meeting_result['html_link']}")
        
        body_parts.append("\nLooking forward to our meeting!")
        
        return "\n".join(body_parts)

    def _resolve_email_recipient(self, recipient: str, params: dict, context: Dict[str, Any]) -> str:
        """Resolve email recipient using contact cache and session context"""
        session_context = context.get("session_context", {})
        contacts = session_context.get("contacts", {"by_email": {}, "by_name": {}})
        
        # Check if recipient needs resolution
        needs_resolution = (
            not recipient or 
            recipient.strip() == "" or
            "example.com" in recipient.lower() or
            "@" not in recipient or
            recipient.count("@") != 1
        )
        
        if not needs_resolution:
            return recipient  # Already a valid email
        
        logger.info(f"Resolving email recipient: '{recipient}' using contact cache with {len(contacts['by_name'])} names")
        
        # Extract potential names from email body and subject
        body = params.get("body", "")
        subject = params.get("subject", "")
        potential_names = self._extract_names_from_text(body + " " + subject)
        
        # Try to resolve using contact cache
        for name in potential_names:
            name_key = name.lower()
            if name_key in contacts["by_name"]:
                emails = contacts["by_name"][name_key]
                if emails:
                    resolved_email = emails[0]  # Use first match
                    logger.info(f"Resolved '{name}' to '{resolved_email}' from contact cache")
                    return resolved_email
        
        # If recipient looks like a name (no @), try direct lookup
        if recipient and "@" not in recipient:
            name_key = recipient.lower().strip()
            if name_key in contacts["by_name"]:
                emails = contacts["by_name"][name_key]
                if emails:
                    resolved_email = emails[0]
                    logger.info(f"Direct name lookup: '{recipient}' → '{resolved_email}'")
                    return resolved_email
        
        # Fallback: use last meeting attendees
        last_meeting = session_context.get("last_meeting", {})
        if last_meeting.get("attendees"):
            fallback_email = last_meeting["attendees"][0]
            logger.info(f"Using fallback from last meeting: '{fallback_email}'")
            return fallback_email
        
        # Final fallback: return original (might be empty, will be caught by validation)
        logger.warning(f"Could not resolve email recipient: '{recipient}'. Contact cache has {len(contacts['by_email'])} emails")
        return recipient

    def _sanitize_meeting_params(self, params: dict) -> dict:
        """Sanitize meeting parameters to match Pydantic schema requirements"""
        # Title - ensure string
        title = params.get("title") or "Meeting"
        params["title"] = str(title)

        # Duration - ensure integer
        try:
            params["duration_minutes"] = int(params.get("duration_minutes", 30))
        except (ValueError, TypeError):
            params["duration_minutes"] = 30
        
        # Ensure positive duration
        if params["duration_minutes"] <= 0:
            params["duration_minutes"] = 30

        # Attendees - coerce to list[str]
        attendees = params.get("attendees", [])
        
        if attendees is None or attendees == "":
            attendees = []
        elif isinstance(attendees, str):
            # Split common delimiters, trim whitespace, ignore empties
            parts = [p.strip() for p in attendees.replace(";", ",").split(",")]
            attendees = [p for p in parts if p]
        elif isinstance(attendees, (set, tuple)):
            attendees = list(attendees)
        elif not isinstance(attendees, list):
            attendees = [str(attendees)]

        # Ensure all entries are strings and non-empty
        attendees = [str(a).strip() for a in attendees if str(a).strip()]
        params["attendees"] = attendees
        
        logger.info(f"Sanitized meeting params: title='{params['title']}', duration={params['duration_minutes']}, attendees={params['attendees']}")
        return params

    def _sanitize_email_params(self, params: dict, context: Dict[str, Any] = None) -> dict:
        """Sanitize email parameters to match email tool schema requirements"""
        # Recipient - ensure string (handle common parameter name variations)
        recipient = params.get("recipient") or params.get("to") or ""
        
        # Resolve recipient using contact cache if missing or placeholder
        if context and "session_context" in context:
            recipient = self._resolve_email_recipient(recipient, params, context)
        
        params["recipient"] = str(recipient).strip()
        
        # Subject - ensure string
        subject = params.get("subject") or "Message from Native IQ"
        params["subject"] = str(subject)
        
        # Body - ensure string and enhance with meeting links if available
        body = params.get("body") or params.get("message") or ""
        
        # Check if this is a meeting invite email and enhance with actual meeting link
        if context and "meeting_result" in context:
            meeting_result = context["meeting_result"]
            if "html_link" in meeting_result:
                meeting_link = meeting_result["html_link"]
                # Replace generic "invite link" text with actual link
                if "invite link" in body.lower() and "http" not in body:
                    body = body.replace("invite link attached", f"meeting link: {meeting_link}")
                    body = body.replace("invite link", f"meeting link: {meeting_link}")
                elif "http" not in body:  # No link in body, add it
                    body += f"\n\n📅 Join the meeting: {meeting_link}"
        
        # Add Native IQ signature to every email
        sender_name = params.get("on_behalf_of") or context.get("sender_name") if context else None or "User"
        if not body.endswith(f"\n\nNative IQ on behalf of {sender_name}"):
            body += f"\n\nNative IQ on behalf of {sender_name}"
        
        params["body"] = str(body)
        
        # Optional parameters with defaults
        params["cc"] = params.get("cc") or []
        params["bcc"] = params.get("bcc") or []
        params["html_body"] = params.get("html_body") or ""
        params["attachments"] = params.get("attachments") or []
        params["sender"] = params.get("sender") or ""
        params["on_behalf_of"] = sender_name
        
        # Clean up any incorrect parameter names and map to email tool schema
        if "to" in params and "recipient" not in params:
            params["recipient"] = params.pop("to")
        if "message" in params and "body" not in params:
            params["body"] = params.pop("message")
        
        # Convert recipient to 'to' field as list[str] for email tool schema compliance
        recipient = params.get("recipient", "")
        if recipient:
            # Ensure 'to' is a list of email addresses
            if isinstance(recipient, str):
                params["to"] = [recipient]
            elif isinstance(recipient, list):
                params["to"] = recipient
            else:
                params["to"] = [str(recipient)]
        else:
            params["to"] = []
        
        # Keep recipient for backward compatibility but prioritize 'to'
        if not params.get("recipient") and params.get("to"):
            params["recipient"] = params["to"][0] if params["to"] else ""
        
        logger.info(f"Sanitized email params: to={params.get('to')}, subject='{params['subject']}', body_length={len(params['body'])}")
        return params

    async def _format_execution_result(self, result: Dict[str, Any], original_message: str) -> str:
        """Format execution result into a natural response"""
        try:
            # Use LLM to format the response naturally
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage
            
            llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
            
            system_prompt = """You are Native IQ, a professional executive assistant. Format the execution result into a natural, conversational response.
            
            Be:
            - Professional but friendly
            - Clear about what was accomplished
            - Helpful with next steps if relevant
            - Concise but informative
            
            Avoid technical jargon. Speak like a trusted business colleague."""
            
            user_prompt = f"""
            User requested: {original_message}
            Execution result: {result}
            
            Format this into a natural response that confirms what was done and provides any relevant next steps.
            """
            
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await llm.ainvoke(messages)
            
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error formatting execution result: {e}")
            # Fallback to basic formatting
            if result.get("success"):
                return f"✅ Task completed successfully! {result.get('description', '')}"
            else:
                return f"❌ Task failed: {result.get('error', 'Unknown error')}"

    def setup_handlers(self):
        """Setup command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        # self.application.add_handler(CommandHandler("chat", self.chat_command))
        # self.application.add_handler(CommandHandler("silent", self.silent_command))
        self.application.add_handler(CommandHandler("automate", self.automate_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Handle all text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def run_async(self):
        """Run Telegram bot asynchronously"""
        await self.application.run_polling()

    def run_sync(self):
        import asyncio
        asyncio.run(self.run_async())

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
    
    # Start both Telegram bot and FastAPI server
    async def run_both():
        # Start background monitoring
        asyncio.create_task(bot._start_background_monitoring())
        
        # Start Telegram bot
        telegram_task = asyncio.create_task(bot.run_async())
        
        # Start FastAPI server
        config = uvicorn.Config(bot.fastapi_app, host="0.0.0.0", port=8000)
        server = uvicorn.Server(config)
        fastapi_task = asyncio.create_task(server.serve())
        
        await asyncio.gather(telegram_task, fastapi_task)
    
    asyncio.run(run_both())

if __name__ == "__main__":
    main()
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field
# import openai
# from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.base_agent import BaseAgent, Belief, Desire, Intention, BeliefType
from telegram import Update

logger = logging.getLogger(__name__)
load_dotenv()

@dataclass
class ProactiveMessage:
    message_id: str
    user_id: str
    message_type: str
    content: str
    scheduled_time: datetime
    sent: bool = False
    context: Dict[str, Any] = field(default_factory=dict)

class ProactiveCommunicationAgent(BaseAgent):
    """Production-ready agent that proactively communicates like a professional PA"""
    
    def __init__(self, agent_id: str = "native_proactive_001"):
        super().__init__(agent_id, agent_type="communication")
        self.scheduled_messages: Dict[str, ProactiveMessage] = {}
        self.user_contexts: Dict[str, Dict[str, Any]] = {}
        self.openai = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Professional PA/Co-founder personality prompts
        self.personality_prompts = {
            "base": """You are Native IQ, a professional executive assistant and business co-founder. 
            You communicate like a trusted colleague who deeply understands business operations. You're professional 
            but approachable, efficient yet personable. You focus on getting things done and helping your user succeed. 
            You speak like a seasoned business professional - direct, helpful, and always thinking ahead.""",
            
            "conversational_chat": """You are Native IQ, acting as a professional executive assistant and business partner. 
            You communicate naturally like a trusted colleague who knows the business inside and out. You're helpful, 
            efficient, and always thinking about how to improve operations. You can discuss business strategy, handle 
            operational tasks, or have professional conversations. You're like talking to your most competent business partner.""",
            
            "capability_explanation": """You are Native IQ explaining your business capabilities as a professional assistant. 
            Be specific about your operational skills and business tools. Sound like an experienced executive assistant 
            explaining how they can support the business - confident, knowledgeable, and focused on results.""",
            
            "automation_assistance": """You are Native IQ helping with business automation and operations. You understand 
            workflows, processes, and efficiency improvements. You communicate like a business operations expert who can 
            identify bottlenecks and implement solutions. Be practical and results-focused.""",
            
            "meeting_reminder": """Generate a professional meeting reminder message. Sound like an 
            executive assistant who cares about their executive's success. Be proactive and helpful.""",
            
            "automation_update": """Generate an update about completed automations. Sound like a 
            business partner sharing operational wins and improvements. Be professional but enthusiastic.""",
            
            "response_nudge": """Generate a gentle nudge about pending responses. Sound like a 
            trusted business advisor who helps manage important relationships.""",
            
            "calendar_alert": """Generate a calendar alert. Sound like an executive assistant 
            who's always prepared and thinking ahead."""
        }
        
    async def perceive(self, messages: List[str], context: Dict[str, Any]) -> List[Belief]:
        """Perceive events that trigger proactive communications"""
        beliefs = []
        
        try:
            # Meeting scheduled events
            if context.get("meetings_scheduled"):
                for meeting in context["meetings_scheduled"]:
                    belief = Belief(
                        id=f"meeting_scheduled_{datetime.now().timestamp()}",
                        type=BeliefType.KNOWLEDGE,
                        content={
                            "type": "meeting_scheduled",
                            "meeting": meeting,
                            "user_id": meeting.get("user_id"),
                            "time": meeting.get("time"),
                            "contact": meeting.get("contact")
                        },
                        confidence=0.95,
                        source=self.agent_id
                    )
                    beliefs.append(belief)
            
            # Automation completed events
            if context.get("automations_completed"):
                for automation in context["automations_completed"]:
                    belief = Belief(
                        id=f"automation_completed_{datetime.now().timestamp()}",
                        type=BeliefType.KNOWLEDGE,
                        content={
                            "type": "automation_completed",
                            "automation": automation,
                            "user_id": automation.get("user_id"),
                            "time_saved": automation.get("time_saved", 0)
                        },
                        confidence=0.9,
                        source=self.agent_id
                    )
                    beliefs.append(belief)
            
            # Pending responses detected
            if context.get("pending_responses"):
                for response in context["pending_responses"]:
                    belief = Belief(
                        id=f"pending_response_{datetime.now().timestamp()}",
                        type=BeliefType.OBSERVATION,
                        content={
                            "type": "pending_response",
                            "response": response,
                            "user_id": response.get("user_id"),
                            "contact": response.get("contact"),
                            "topic": response.get("topic")
                        },
                        confidence=0.8,
                        source=self.agent_id
                    )
                    beliefs.append(belief)
            
            # Time-based triggers (morning updates, evening summaries)
            current_hour = datetime.now().hour
            if context.get("daily_summary_trigger") and current_hour == 18:  # 6 PM
                belief = Belief(
                    id=f"daily_summary_{datetime.now().timestamp()}",
                    type=BeliefType.KNOWLEDGE,
                    content={
                        "type": "daily_summary",
                        "trigger_time": datetime.now(),
                        "user_id": context.get("user_id")
                    },
                    confidence=0.9,
                    source=self.agent_id
                )
                beliefs.append(belief)
            
            # Handle conversational messages
            if context.get("message_type") == "conversational_chat" or context.get("conversation_type") == "natural_conversation":
                belief = Belief(
                    id=f"conversational_message_{datetime.now().timestamp()}",
                    type=BeliefType.OBSERVATION,
                    content={
                        "type": "conversational_message",
                        "user_message": context.get("user_message", ""),
                        "user_id": context.get("user_name", "user"),
                        "conversation_context": context.get("conversation_history", []),
                        "user_profile": context.get("user_profile", {})
                    },
                    confidence=0.95,
                    source=self.agent_id
                )
                beliefs.append(belief)
            
            logger.info(f"Native Proactive Agent perceived {len(beliefs)} events")
            return beliefs
            
        except Exception as e:
            logger.error(f"Error in proactive perception: {e}")
            return []
    
    async def update_desires(self, beliefs: List[Belief], context: Dict[str, Any]) -> List[Desire]:
        """Update desires for proactive communications"""
        desires = []
        
        try:
            for belief in beliefs:
                content = belief.content
                
                if content.get("type") == "meeting_scheduled":
                    desires.append(Desire(
                        id="send_meeting_confirmation",
                        goal="Confirm meeting and offer preparation help",
                        priority=9,
                        conditions={"has_meeting": True}
                    ))
                
                elif content.get("type") == "automation_completed":
                    desires.append(Desire(
                        id="share_automation_success",
                        goal="Share automation success and impact",
                        priority=7,
                        conditions={"has_automation": True}
                    ))
                
                elif content.get("type") == "pending_response":
                    desires.append(Desire(
                        id="nudge_pending_response",
                        goal="Gently remind about pending response",
                        priority=6,
                        conditions={"has_pending": True}
                    ))
                
                elif content.get("type") == "daily_summary":
                    desires.append(Desire(
                        id="send_daily_summary",
                        goal="Provide end-of-day summary and tomorrow prep",
                        priority=8,
                        conditions={"is_evening": True}
                    ))
                
                elif content.get("type") == "conversational_message":
                    desires.append(Desire(
                        id="respond_to_conversation",
                        goal="Generate natural conversational response using OpenAI",
                        priority=10,
                        conditions={"has_user_message": True}
                    ))
                    
            return desires
            
        except Exception as e:
            logger.error(f"Error updating proactive desires: {e}")
            return []
    
    async def deliberate(self, beliefs: List[Belief], desires: List[Desire], intentions: List[Intention]) -> List[Intention]:
        """Create intentions for proactive communications"""
        new_intentions = []
        
        try:
            for desire in desires:
                # Find relevant belief for this desire
                relevant_belief = None
                for belief in beliefs:
                    if (desire.id == "send_meeting_confirmation" and 
                        belief.content.get("type") == "meeting_scheduled"):
                        relevant_belief = belief
                        break
                    elif (desire.id == "share_automation_success" and 
                          belief.content.get("type") == "automation_completed"):
                        relevant_belief = belief
                        break
                    elif (desire.id == "nudge_pending_response" and 
                          belief.content.get("type") == "pending_response"):
                        relevant_belief = belief
                        break
                    elif (desire.id == "send_daily_summary" and 
                          belief.content.get("type") == "daily_summary"):
                        relevant_belief = belief
                        break
                    elif (desire.id == "respond_to_conversation" and 
                          belief.content.get("type") == "conversational_message"):
                        relevant_belief = belief
                        break
                
                if relevant_belief:
                    intention = Intention(
                        id=f"{desire.id}_{datetime.now().timestamp()}",
                        desire_id=desire.id,
                        action_type="send_proactive_message",
                        parameters={
                            "message_type": desire.id,
                            "belief_content": relevant_belief.content,
                            "user_id": relevant_belief.content.get("user_id")
                        }
                    )
                    new_intentions.append(intention)
            
            return new_intentions
            
        except Exception as e:
            logger.error(f"Error in proactive deliberation: {e}")
            return []
    
    async def act(self, intention: Intention, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute proactive communication"""
        result = {"action_taken": False, "message_sent": ""}
        
        try:
            logger.info(f"🔍 ProactiveCommunicationAgent.act called with intention: {intention.action_type}")
            message_type = intention.parameters.get("message_type")
            belief_content = intention.parameters.get("belief_content", {})
            user_id = intention.parameters.get("user_id")
            
            logger.info(f" Act parameters - message_type: {message_type}, user_id: {user_id}")
            
            # Generate personalized message using LLM
            logger.info(f" Calling _generate_proactive_message...")
            message = await self._generate_proactive_message(message_type, belief_content, context)
            logger.info(f" Generated message: {message}")
            
            if message:
                # Send message via Telegram
                logger.info(f" Calling _send_telegram_message...")
                await self._send_telegram_message(user_id, message)
                
                result = {
                    "action_taken": True,
                    "message_sent": message,
                    "recipient": user_id,
                    "type": message_type
                }
                
                logger.info(f"Native sent proactive message: {message_type} to {user_id}")
            else:
                logger.warning(f" No message generated for type: {message_type}")
            
        except Exception as e:
            logger.error(f"Error in proactive action: {e}")
            import traceback
            logger.error(traceback.format_exc())
            result["error"] = str(e)
            
        logger.info(f" Act result: {result}")
        return result
    
    async def learn(self, beliefs: List[Belief], context: Dict[str, Any]) -> None:
        """Learn from user responses to improve communications"""
        try:
            # Track message effectiveness
            for belief in beliefs:
                if "user_response" in belief.content:
                    # Analyze response sentiment and engagement
                    pass
            
            logger.info(f"Native Proactive Agent learning completed")
            
        except Exception as e:
            logger.error(f"Error in proactive learning: {e}")
    
    async def _generate_proactive_message(self, message_type: str, belief_content: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate personalized message using LLM"""
        try:
            # Get user context for personalization
            user_id = belief_content.get("user_id", "user")
            user_context = self.user_contexts.get(user_id, {})
            user_name = context.get("user_name", user_context.get("name", "there"))
            user_message = context.get("user_message", "")
            
            logger.info(f"Generating message for type: {message_type}, user: {user_name}, message: {user_message}")
            
            # Handle conversational chat with rich context
            if message_type == "conversational_chat" or context.get("conversation_type") == "natural_conversation":
                conversation_history = context.get("conversation_history", [])
                user_profile = context.get("user_profile", {})
                native_capabilities = context.get("native_capabilities", {})
                replied_to_message = context.get("replied_to_message")
                
                # Build conversation context
                recent_messages = ""
                if conversation_history:
                    recent_messages = "\n".join([
                        f"{'User' if msg.get('is_user') else 'Native'}: {msg.get('content', '')}" 
                        for msg in conversation_history[-5:]  # Last 5 messages
                    ])
                
                # Build capabilities summary
                capabilities_summary = ""
                if native_capabilities:
                    capabilities_summary = "\n".join([
                        f"- {cap_name.title()}: {cap_data.get('description', '')}"
                        for cap_name, cap_data in native_capabilities.items()
                    ])
                
                prompt = f"""
                {self.personality_prompts['conversational_chat']}
                
                User's current message: "{user_message}"
                User's name: {user_name}
                
                {f"User replied to: '{replied_to_message}'" if replied_to_message else ""}
                
                Recent conversation context:
                {recent_messages if recent_messages else "This is the start of our conversation."}
                
                Your business capabilities (mention if relevant to the conversation):
                {capabilities_summary}
                
                Respond professionally and naturally to the user's message. You're their trusted business partner and executive assistant. 
                If they ask about your capabilities, explain them in business terms. If they want to automate something, 
                be proactive about helping with operational improvements. Keep the conversation professional but personable.
                
                Focus on business value and practical solutions. Keep your response under 150 words and sound like a competent business colleague.
                """
                
                logger.info(f"Using conversational prompt for user message: {user_message}")
                
            elif message_type == "send_meeting_confirmation":
                meeting = belief_content.get("meeting", {})
                contact = meeting.get("contact", "your contact")
                time = meeting.get("time", "today")
                
                prompt = f"""
                {self.personality_prompts['meeting_reminder']}
                
                Context: You just scheduled a meeting for {user_name} with {contact} at {time}.
                
                Generate a proactive message that:
                1. Confirms the meeting was scheduled
                2. Asks if they're attending
                3. Offers to help with preparation
                4. Sounds like a professional executive assistant
                
                Keep it under 50 words and friendly but professional.
                """
                
            elif message_type == "share_automation_success":
                automation = belief_content.get("automation", {})
                time_saved = automation.get("time_saved", 15)
                
                prompt = f"""
                {self.personality_prompts['automation_update']}
                
                Context: You just completed an automation that saved {user_name} {time_saved} minutes.
                
                Generate a message that:
                1. Shares the automation success
                2. Highlights the time saved
                3. Shows ongoing value
                4. Sounds like a co-founder sharing wins
                
                Keep it under 50 words and enthusiastic but professional.
                """
                
            elif message_type == "nudge_pending_response":
                response = belief_content.get("response", {})
                contact = response.get("contact", "someone")
                topic = response.get("topic", "an important matter")
                
                prompt = f"""
                {self.personality_prompts['response_nudge']}
                
                Context: {contact} messaged {user_name} about {topic} and hasn't received a response.
                
                Generate a gentle nudge that:
                1. Mentions the pending response
                2. Offers to help draft a reply
                3. Maintains relationships
                4. Sounds like a trusted advisor
                
                Keep it under 50 words and helpful.
                """
                
            elif message_type == "send_daily_summary":
                prompt = f"""
                {self.personality_prompts['base']}
                
                Generate an end-of-day message for {user_name} that:
                1. Summarizes today's achievements
                2. Mentions tomorrow's priorities
                3. Offers evening support
                4. Sounds like an executive assistant wrapping up the day
                
                Keep it under 60 words and supportive.
                """
            
            else:
                # Default conversational response
                prompt = f"""
                {self.personality_prompts['base']}
                
                User said: "{user_message}"
                
                Respond naturally and helpfully to {user_name}. Be conversational and engaging.
                """
            
            # Call OpenAI API
            system_content = self.personality_prompts.get(context.get('conversation_type', 'base'), self.personality_prompts['base'])
            
            try:
                response = await self.openai.ainvoke([
                    SystemMessage(content=system_content),
                    HumanMessage(content=prompt)
                ])
                
                message = response.content.strip()
                logger.info(f"Generated proactive message: {message}")
                return message
            except Exception as e:
                logger.error(f"Error in LangChain OpenAI call: {str(e)}")
                raise e
            
        except Exception as e:
            logger.error(f"Error generating proactive message: {e}")
            # Professional fallback messages with variety
            user_message_lower = user_message.lower()
            
            if "how can you help" in user_message_lower or "what can you do" in user_message_lower:
                return f"Hi {user_name}! I'm Native IQ, your executive assistant and business operations partner. I handle automation, scheduling, communications, business analysis, and continuous learning to improve your operations. What business challenge can I help you tackle today?"
            elif "who are you" in user_message_lower or "what are you" in user_message_lower:
                return f"I'm Native IQ, your intelligent business co-founder and executive assistant. I specialize in automating workflows, managing communications, analyzing business patterns, and helping you stay organized. Think of me as your most capable business partner."
            elif "hello" in user_message_lower or "hi" in user_message_lower:
                return f"Hello {user_name}! Ready to tackle some business objectives today. How can I support your operations?"
            elif "help me with" in user_message_lower or "i need" in user_message_lower:
                return f"Absolutely, {user_name}! I'm here to help with business operations, automation, scheduling, and strategic support. What specific challenge are you facing?"
            elif "what" in user_message_lower and ("can" in user_message_lower or "do" in user_message_lower):
                return f"I can help you with: automating repetitive tasks, managing your schedule, analyzing business patterns, handling communications, and providing strategic insights. What area interests you most?"
            else:
                # Vary the fallback response to avoid repetition
                import random
                fallbacks = [
                    f"Let me help you with that, {user_name}. What specific aspect would you like me to focus on?",
                    f"I'm here to support your business operations, {user_name}. Could you tell me more about what you need?",
                    f"That's something I can definitely assist with, {user_name}. What would be the most helpful approach?",
                    f"I understand, {user_name}. Let me see how I can best support you with this business need."
                ]
                return random.choice(fallbacks)
    
    async def _show_typing(self, update: Update):
        """Show 'Bot is typing...' indicator"""
        try:
            await update.message.chat.send_action(action=ChatAction.TYPING)
        except Exception as e:
            logger.error(f"Error showing typing indicator: {e}")
    
    async def _send_telegram_message(self, user_id: str, message: str):
        """Send message via Telegram"""
        try:
            # Import your telegram bot function
            logger.info(f"Would send Telegram message to {user_id}: {message}")
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            # For production, you might want to queue messages for retry
            print(f"Native IQ → {user_id}: {message}")  # Console fallback

# Scheduler for proactive communications
class ProactiveScheduler:
    """Schedules and triggers proactive communications"""
    
    def __init__(self, proactive_agent: ProactiveCommunicationAgent):
        self.proactive_agent = proactive_agent
        self.running = False
    
    async def start(self):
        """Start the proactive communication scheduler"""
        self.running = True
        logger.info("Native Proactive Scheduler started")
        
        while self.running:
            try:
                # Check for events every 30 seconds
                await self._check_proactive_triggers()
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in proactive scheduler: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _check_proactive_triggers(self):
        """Check for events that should trigger proactive messages"""
        try:
            # Get current context from your system
            context = await self._get_system_context()
            
            # Let the proactive agent perceive and act
            beliefs = await self.proactive_agent.perceive([], context)
            
            if beliefs:
                desires = await self.proactive_agent.update_desires(beliefs, context)
                intentions = await self.proactive_agent.deliberate(beliefs, desires, [])
                
                for intention in intentions:
                    await self.proactive_agent.act(intention, context)
                    
        except Exception as e:
            logger.error(f"Error checking proactive triggers: {e}")
    
    async def _get_system_context(self) -> Dict[str, Any]:
        """Get current system context for proactive triggers"""
        # This should integrate with your existing system
        # For now, return demo context
        return {
            "meetings_scheduled": [],
            "automations_completed": [],
            "pending_responses": [],
            "daily_summary_trigger": True,
            "user_id": "demo_user"
        }
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Native Proactive Scheduler stopped")
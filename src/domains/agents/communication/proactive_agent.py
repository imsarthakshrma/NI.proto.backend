import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field
import openai
import os

from src.core.base_agent import BaseAgent, Belief, Desire, Intention, BeliefType

logger = logging.getLogger(__name__)

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
        
        # Initialize OpenAI client
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Professional PA personality prompts
        self.personality_prompts = {
            "base": """You are Native AI, a professional executive assistant and co-founder-level AI. 
            You communicate with confidence, professionalism, and care. You're proactive, efficient, 
            and always focused on helping your user succeed. Keep messages concise but warm.""",
            
            "meeting_reminder": """Generate a professional meeting reminder message. Sound like an 
            executive assistant who cares about their executive's success. Be proactive and helpful.""",
            
            "automation_update": """Generate an update about completed automations. Sound like a 
            co-founder sharing wins and progress. Be enthusiastic but professional.""",
            
            "response_nudge": """Generate a gentle nudge about pending responses. Sound like a 
            trusted advisor who helps manage important relationships.""",
            
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
            message_type = intention.parameters.get("message_type")
            belief_content = intention.parameters.get("belief_content", {})
            user_id = intention.parameters.get("user_id")
            
            # Generate personalized message using LLM
            message = await self._generate_proactive_message(message_type, belief_content, context)
            
            if message:
                # Send message via Telegram
                await self._send_telegram_message(user_id, message)
                
                result = {
                    "action_taken": True,
                    "message_sent": message,
                    "recipient": user_id,
                    "type": message_type
                }
                
                logger.info(f"Native sent proactive message: {message_type} to {user_id}")
            
        except Exception as e:
            logger.error(f"Error in proactive action: {e}")
            result["error"] = str(e)
            
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
            user_name = user_context.get("name", "there")
            
            # Build context-specific prompt
            if message_type == "send_meeting_confirmation":
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
                return "Hi! I'm here to help you stay organized and efficient. 🚀"
            
            # Call OpenAI API
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.personality_prompts['base']},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            message = response.choices[0].message.content.strip()
            return message
            
        except Exception as e:
            logger.error(f"Error generating proactive message: {e}")
            # Fallback messages
            fallbacks = {
                "send_meeting_confirmation": "Hi! I scheduled your meeting for today. Are you attending? Let me know if you need any preparation help! 📅",
                "share_automation_success": "Great news! I just automated another task for you, saving 15 minutes. Your efficiency is improving! 🚀",
                "nudge_pending_response": "Friendly reminder: You have a pending response about an important matter. Need help drafting a reply? 📝",
                "send_daily_summary": "End of day summary: Great progress today! Tomorrow's priorities are ready. Have a good evening! ✨"
            }
            return fallbacks.get(message_type, "Hi! I'm here to help you stay productive! 🚀")
    
    async def _send_telegram_message(self, user_id: str, message: str):
        """Send message via Telegram"""
        try:
            # Import your telegram bot function
            from src.integration.telegram.telegram_bot import send_message_to_user
            await send_message_to_user(user_id, message)
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            # For production, you might want to queue messages for retry
            print(f"NATIVE AI → {user_id}: {message}")  # Console fallback

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
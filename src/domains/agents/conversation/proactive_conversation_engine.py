"""
Proactive Conversation Engine For Native
Make Native Initiate conversations like a real PA/Co-Founder
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class ConversationTrigger(Enum):
    TIME_BASED = "time_based"           # "Good morning! Here's your day ahead"
    EVENT_BASED = "event_based"         # "I noticed you have a meeting in 10 minutes"
    PATTERN_BASED = "pattern_based"     # "You usually follow up with clients on Fridays"
    OPPORTUNITY_BASED = "opportunity_based"  # "I found 3 tasks I can automate for you"
    RELATIONSHIP_BASED = "relationship_based"  # "Sarah hasn't responded to your email from Tuesday"
    PROACTIVE_INSIGHT = "proactive_insight"    # "I noticed a pattern in your scheduling"

@dataclass
class ConversationContext:
    trigger_type: ConversationTrigger
    urgency: str # low, medium, high, critical
    user_availability: str  # available, busy, do_not_disturb
    conversation_history: List[Dict] = field(default_factory=list)
    relevant_data: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[str] = field(default_factory=list)

class ProactiveConversationEngine(BaseAgent):
    """Proactive Conversation Engine for Native IQ"""

    def __init__(self, agent_id: str = "proactive_conversation_001"):
        super().__init__(agent_id, "conversation", temperature=0.7)

        self.conversation_triggers = {
            # time-based triggers
            "morning_briefing": {"time": "09:00", "frequency": "daily"},
            "end_of_day_summary": {"time": "18:00", "frequency": "daily"},
            "weekly_review": {"time": "17:00", "frequency": "friday"},
            "monthly_review": {"time": "17:00", "frequency": "monthly"},
            
            # event-based triggers
            "meeting_reminder": {"before_minutes": 10},
            "deadline_alert": {"before_hours": 24},
            "follow_up_reminder": {"after_days": 3},
            "appointment_reminder": {"before_minutes": 15},
            
            # pattern-based triggers
            "unusual_behavior": {"threshold": 0.8},
            "missed_routine": {"delay_hours": 2},
            "efficiency_opportunity": {"confidence": 0.7},
            "relationship_opportunity": {"confidence": 0.7},
            "proactive_insight": {"confidence": 0.7}
        }
        
        self.personality_prompts = {
            "base": """You are Native (NIQ), an AI co-founder and executive assistant. 
            You're proactive, intelligent, and care deeply about the user's success.
            You communicate like a trusted business partner - professional but warm,
            direct but considerate, conversational but professional. You notice patterns, 
            suggest improvements, and take initiative to help optimize workflows.""",
            
            "morning_briefing": """Start the day with energy and focus. Highlight priorities, 
            potential issues, and opportunities. Be the co-founder who helps set the day's 
            strategic direction.""",

            "opportunity_identification": """You've discovered something that could save time 
            or improve efficiency. Present it as a business partner would - with data, clear 
            benefits, and actionable next steps.""",
            
            "relationship_management": """You're tracking business relationships and communication 
            patterns. Suggest follow-ups, flag potential issues, and help maintain strong 
            professional connections.""",
            
            "proactive_insight": """You've discovered something that could save time or improve 
            efficiency. Present it as a business partner would - with data, clear benefits, 
            and actionable next steps."""
        }

        # Conversation history storage
        self.conversation_history = []
        self.user_preferences = {}
        
        # Telegram integration
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        logger.info(f"Proactive Conversation Engine initialized: {self.agent_id}")

    async def should_initiate_conversation(self, context: ConversationContext) -> bool:
        """Determine if Native should proactively start a conversation"""
        
        # check user availability
        if context.user_availability == "do_not_disturb":
            return False
        
        # high urgency always initiates
        if context.urgency == "critical":
            return True
        
        # check conversation frequency limits
        recent_conversations = await self._get_recent_conversations()
        if len(recent_conversations) > 5:  # max 5 proactive conversations per day
            return False
        
        # evaluate trigger importance
        importance_score = await self._calculate_importance(context)
        
        # threshold based on urgency
        thresholds = {
            "low": 0.8,
            "medium": 0.6,
            "high": 0.4,
            "critical": 0.0
        }
        
        return importance_score >= thresholds.get(context.urgency, 0.6)
    
    async def generate_proactive_message(self, context: ConversationContext) -> str:
        """Generate a natural, contextual proactive message"""
        
        # select appropriate personality prompt
        prompt_type = self._select_prompt_type(context.trigger_type)
        base_prompt = self.personality_prompts.get(prompt_type, self.personality_prompts["base"])
        
        # build context-aware prompt
        conversation_prompt = f"""
        {base_prompt}
        
        CONTEXT:
        - Trigger: {context.trigger_type.value}
        - Urgency: {context.urgency}
        - Relevant Data: {context.relevant_data}
        - Suggested Actions: {context.suggested_actions}
        - Recent Conversation History: {context.conversation_history[-3:]}
        
        Generate a proactive message that:
        1. Feels natural and conversational
        2. Provides clear value
        3. Includes specific, actionable suggestions
        4. Matches the urgency level
        5. References relevant context
        
        Keep it concise but comprehensive. Sound like a co-founder who genuinely cares.
        """
        
        response = await self.model.ainvoke([
            SystemMessage(content=conversation_prompt),
            HumanMessage(content="Generate the proactive message:")
        ])
        
        return response.content

    async def initiate_conversation(self, 
                                  user_id: str, 
                                  context: ConversationContext,
                                  platform: str = "telegram") -> Dict[str, Any]:
        """Initiate a proactive conversation with the user"""
        
        try:
            # Check if we should initiate
            if not await self.should_initiate_conversation(context):
                return {"initiated": False, "reason": "conditions_not_met"}
            
            # Generate the message
            message = await self.generate_proactive_message(context)
            
            # Send via appropriate platform
            result = await self._send_message(user_id, message, platform)
            
            # Log the conversation
            await self._log_proactive_conversation(user_id, context, message, result)
            
            return {
                "initiated": True,
                "message": message,
                "platform": platform,
                "trigger": context.trigger_type.value,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error initiating proactive conversation: {e}")
            return {"initiated": False, "error": str(e)}
    
    async def _calculate_importance(self, context: ConversationContext) -> float:
        """Calculate importance score for the conversation trigger"""
        
        importance_weights = {
            ConversationTrigger.TIME_BASED: 0.3,
            ConversationTrigger.EVENT_BASED: 0.8,
            ConversationTrigger.PATTERN_BASED: 0.6,
            ConversationTrigger.OPPORTUNITY_BASED: 0.7,
            ConversationTrigger.RELATIONSHIP_BASED: 0.5,
            ConversationTrigger.PROACTIVE_INSIGHT: 0.6
        }
        
        base_score = importance_weights.get(context.trigger_type, 0.5)
        
        # adjust based on data quality and relevance
        if context.relevant_data:
            base_score += 0.2
        
        if context.suggested_actions:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _select_prompt_type(self, trigger_type: ConversationTrigger) -> str:
        """Select appropriate personality prompt based on trigger"""
        
        prompt_mapping = {
            ConversationTrigger.TIME_BASED: "morning_briefing",
            ConversationTrigger.OPPORTUNITY_BASED: "opportunity_identification",
            ConversationTrigger.RELATIONSHIP_BASED: "relationship_management"
        }
        
        return prompt_mapping.get(trigger_type, "base")
    
    async def _send_message(self, user_id: str, message: str, platform: str) -> Dict[str, Any]:
        """Send message via specified platform"""
        
        if platform == "telegram":
            return await self._send_telegram_message(user_id, message)
        elif platform == "slack":
            return await self._send_slack_message(user_id, message)
        else:
            logger.error(f"Unsupported platform: {platform}")
            return {"success": False, "error": "unsupported_platform"}
    
    async def _send_telegram_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """Send message via Telegram"""
        try:
            import telegram
            
            bot = telegram.Bot(token=self.telegram_bot_token)
            await bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            
            return {"success": True, "platform": "telegram", "timestamp": datetime.now().isoformat()}
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_slack_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """Send message via Slack"""
        try:
            # Implementation for Slack integration
            # This would use slack-sdk
            return {"success": True, "platform": "slack", "timestamp": datetime.now().isoformat()}
            
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return {"success": False, "error": str(e)}

    async def _log_proactive_conversation(self, 
                                        user_id: str, 
                                        context: ConversationContext,
                                        message: str, 
                                        result: Dict[str, Any]):
        """Log proactive conversation for learning and analytics"""
        
        conversation_log = {
            "user_id": user_id,
            "trigger_type": context.trigger_type.value,
            "urgency": context.urgency,
            "message": message,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "relevant_data": context.relevant_data
        }
        
        self.conversation_history.append(conversation_log)
        
        # Keep only last 100 conversations in memory
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-100:]
        
        logger.info(f"Logged proactive conversation for user {user_id}")

    async def _get_recent_conversations(self) -> List[Dict]:
        """Get recent proactive conversations to avoid spam"""
        
        today = datetime.now().date()
        recent_conversations = [
            conv for conv in self.conversation_history
            if datetime.fromisoformat(conv["timestamp"]).date() == today
        ]
        
        return recent_conversations
    
    async def analyze_user_response(self, user_id: str, response: str) -> Dict[str, Any]:
        """Analyze user response to proactive message for learning"""
        
        analysis_prompt = f"""
        Analyze this user response to a proactive message:
        
        User Response: {response}
        
        Determine:
        1. Sentiment (positive, neutral, negative)
        2. Engagement level (high, medium, low)
        3. Action taken (yes, no, maybe, ignored)
        4. Feedback type (appreciation, complaint, suggestion, neutral)
        
        Return JSON format.
        """
        
        try:
            response_analysis = await self.model.ainvoke([
                SystemMessage(content="You are an expert at analyzing user responses."),
                HumanMessage(content=analysis_prompt)
            ])
            
            # Parse the response and update user preferences
            analysis = json.loads(response_analysis.content)
            await self._update_user_preferences(user_id, analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing user response: {e}")
            return {"error": str(e)}
    
    async def _update_user_preferences(self, user_id: str, analysis: Dict[str, Any]):
        """Update user preferences based on response analysis"""
        
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {
                "preferred_times": [],
                "engagement_patterns": {},
                "response_style": "neutral",
                "frequency_preference": "medium"
            }
        
        # Update preferences based on analysis
        user_prefs = self.user_preferences[user_id]
        
        if analysis.get("sentiment") == "negative":
            user_prefs["frequency_preference"] = "low"
        elif analysis.get("engagement_level") == "high":
            user_prefs["frequency_preference"] = "high"
        
        logger.info(f"Updated preferences for user {user_id}")

    async def perceive(self, messages: List[Any], context: Dict[str, Any]) -> List[Any]:
        """Perceive method for BaseAgent compatibility"""
        # For conversation engine, we don't need traditional perception
        return []
    
    async def update_desires(self, beliefs: List[Any], context: Dict[str, Any]):
        """Update desires method for BaseAgent compatibility"""
        # Conversation engine desires are static
        pass
    
    async def deliberate(self, beliefs: List[Any], desires: List[Any], current_intentions: List[Any]) -> List[Any]:
        """Deliberate method for BaseAgent compatibility"""
        # Conversation engine uses different deliberation logic
        return []
    
    async def act(self, intention: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Act method for BaseAgent compatibility"""
        # Main action is handled by initiate_conversation
        return {"status": "conversation_engine_active"}
    
    async def learn(self, beliefs: List[Any], intentions: List[Any], context: Dict[str, Any]):
        """Learn method for BaseAgent compatibility"""
        # Learning is handled by analyze_user_response
        pass

class ProactiveScheduler:
    """Schedules and triggers proactive conversations"""

    def __init__(self, conversation_engine: ProactiveConversationEngine):
        self.conversation_engine = conversation_engine
        self.running = False
        self.triggers = []
        self.scheduled_tasks = {}

    async def start(self):
        """Start the proactive scheduler"""
        self.running = True
        
        # Initialize scheduler (simplified for now)
        logger.info("Proactive conversation scheduler initialized")
        
        # In production, this would integrate with APScheduler or similar
        # For now, we'll handle triggers manually when needed

    async def add_trigger(self, trigger_type: ConversationTrigger, 
                         conditions: Dict[str, Any], 
                         user_id: str):
        """Add a new proactive conversation trigger"""

        trigger = {
            "type": trigger_type,
            "conditions": conditions,
            "user_id": user_id,
            "created_at": datetime.now(),
            "active": True
        }

        self.triggers.append(trigger)
        logger.info(f"Added proactive trigger: {trigger_type.value} for user {user_id}")

    async def _schedule_time_triggers(self):
        """Schedule time-based proactive triggers"""
        
        # Schedule morning briefings
        await self._schedule_daily_trigger(
            time="09:00",
            trigger_type=ConversationTrigger.TIME_BASED,
            context_data={"briefing_type": "morning"}
        )
        
        # Schedule evening summaries
        await self._schedule_daily_trigger(
            time="18:00", 
            trigger_type=ConversationTrigger.TIME_BASED,
            context_data={"briefing_type": "evening"}
        )
        
        logger.info("Scheduled time-based triggers")

    async def _schedule_daily_trigger(self, time: str, trigger_type: ConversationTrigger, context_data: Dict):
        """Schedule a daily recurring trigger"""
        
        # This would integrate with APScheduler for production
        # For now, we'll use a simple implementation
        
        trigger_id = f"{trigger_type.value}_{time}"
        self.scheduled_tasks[trigger_id] = {
            "time": time,
            "trigger_type": trigger_type,
            "context_data": context_data,
            "frequency": "daily"
        }

    async def _start_event_monitoring(self):
        """Monitor for events that should trigger proactive conversations"""
        
        # This would monitor:
        # - Calendar events (meetings starting soon)
        # - Email patterns (unanswered emails)
        # - Task deadlines
        # - Automation opportunities discovered
        
        logger.info("Event monitoring initialized (background monitoring ready)")
        
        # For now, we'll skip the background task to avoid event loop conflicts
        # In production, this would be handled by a separate process or proper task scheduling

    async def _monitor_events(self):
        """Background task to monitor for trigger events"""
        
        while self.running:
            try:
                # Check for meeting reminders
                await self._check_meeting_reminders()
                
                # Check for follow-up opportunities
                await self._check_follow_up_opportunities()
                
                # Check for automation opportunities
                await self._check_automation_opportunities()
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in event monitoring: {e}")
                await asyncio.sleep(60)

    async def _check_meeting_reminders(self):
        """Check for upcoming meetings that need reminders"""
        # Implementation would check calendar API
        pass

    async def _check_follow_up_opportunities(self):
        """Check for follow-up opportunities based on communication patterns"""
        # Implementation would analyze recent communications
        pass

    async def _check_automation_opportunities(self):
        """Check for new automation opportunities to present"""
        # Implementation would check analyzer agent output
        pass

    async def trigger_proactive_conversation(self, 
        user_id: str, 
        trigger_type: ConversationTrigger,
        context_data: Dict[str, Any],
        urgency: str = "medium"):
        """Manually trigger a proactive conversation"""
        
        context = ConversationContext(
            trigger_type=trigger_type,
            urgency=urgency,
            user_availability="available",  # Would check actual availability
            relevant_data=context_data,
            suggested_actions=context_data.get("suggested_actions", [])
        )
        
        result = await self.conversation_engine.initiate_conversation(
            user_id=user_id,
            context=context,
            platform="telegram"
        )
        
        logger.info(f"Triggered proactive conversation: {result}")
        return result

    async def stop(self):
        """Stop the proactive conversation scheduler"""
        self.running = False
        logger.info("Proactive conversation scheduler stopped")
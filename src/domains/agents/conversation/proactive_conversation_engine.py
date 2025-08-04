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

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_text_splitters import TokenTextSplitter
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
    """Proactive Conversation Engine for Native AI"""

    def __init__(self, agent_id: str = "proactive_conversation_001"):
        super().__init__(agent_id, "conversation", temperature=0.7)

        self.conversation_triggers = {
                # time-based triggers
                "morning_briefing": {"time": "09:00", "frequency": "daily"},
                "end_of_day_summary": {"time": "18:00", "frequency": "daily"},
                "weekly_review": {"time": "17:00", "frequency": "friday"},
                "monthly_review": {"time": "17:00", "frequency": "monthly"},
                "yearly_review": {"time": "17:00", "frequency": "yearly"},
                
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
                "base": """You are Native also known as NIQ, an AI co-founder and executive assistant. 
                You're proactive, intelligent, and care deeply about the user's success.
                You communicate like a trusted business partner - professional but warm,
                direct but considerate, conversational but professional. You notice patterns, suggest improvements, and take initiative to help optimize workflows.""",
                
                "morning_briefing": """Start the day with energy and focus. Highlight priorities, potential issues, and opportunities. Be the co-founder who helps set the day's strategic direction.""",

                "afternoon_briefing": """Review the day's progress and highlight key achievements, potential issues, and opportunities. Be the co-founder who helps set the day's strategic direction.""",

                "evening_briefing": """Review the day's progress and highlight key achievements, potential issues, and opportunities. Be the co-founder who helps set the day's strategic direction.""",

                "weekly_review": """Review the week's progress and highlight key achievements, potential issues, and opportunities. Be the co-founder who helps set the day's strategic direction.""",

                "monthly_review": """Review the month's progress and highlight key achievements, potential issues, and opportunities. Be the co-founder who helps set the day's strategic direction.""",

                "yearly_review": """Review the year's progress and highlight key achievements, potential issues, and opportunities. Be the co-founder who helps set the day's strategic direction.""",
                
                "opportunity_identification": """You've discovered something that could save time or improve efficiency. Present it as a business partner would - with data, clear benefits, and actionable next steps.""",
                
                "relationship_management": """You're tracking business relationships and communication patterns. Suggest follow-ups, flag potential issues, and help maintain strong professional connections.""",
                
                "proactive_insight": """You've discovered something that could save time or improve efficiency. Present it as a business partner would - with data, clear benefits, and actionable next steps."""
                }

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

    """
Proactive Conversation Engine for Native IQ
Makes Native initiate conversations like a real PA/co-founder
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

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
    urgency: str  # low, medium, high, critical
    user_availability: str  # available, busy, do_not_disturb
    conversation_history: List[Dict] = field(default_factory=list)
    relevant_data: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[str] = field(default_factory=list)

class ProactiveConversationEngine(BaseAgent):
    """
    Makes Native initiate conversations proactively like a real PA/co-founder
    """
    
    def __init__(self, agent_id: str = "proactive_conversation_001"):
        super().__init__(agent_id, "conversation", temperature=0.7)
        
        self.conversation_triggers = {
            # Time-based triggers
            "morning_briefing": {"time": "09:00", "frequency": "daily"},
            "end_of_day_summary": {"time": "18:00", "frequency": "daily"},
            "weekly_review": {"time": "17:00", "frequency": "friday"},
            
            # Event-based triggers
            "meeting_reminder": {"before_minutes": 10},
            "deadline_alert": {"before_hours": 24},
            "follow_up_reminder": {"after_days": 3},
            
            # Pattern-based triggers
            "unusual_behavior": {"threshold": 0.8},
            "missed_routine": {"delay_hours": 2},
            "efficiency_opportunity": {"confidence": 0.7}
        }
        
        # Conversation personality
        self.personality_prompts = {
            "base": """You are Native, an AI co-founder and executive assistant. 
            You're proactive, intelligent, and care deeply about the user's success.
            You communicate like a trusted business partner - professional but warm,
            direct but considerate. You notice patterns, suggest improvements, and
            take initiative to help optimize workflows.""",
            
            "morning_briefing": """Start the day with energy and focus. Highlight
            priorities, potential issues, and opportunities. Be the co-founder who
            helps set the day's strategic direction.""",
            
            "opportunity_identification": """You've discovered something that could
            save time or improve efficiency. Present it as a business partner would -
            with data, clear benefits, and actionable next steps.""",
            
            "relationship_management": """You're tracking business relationships and
            communication patterns. Suggest follow-ups, flag potential issues, and
            help maintain strong professional connections."""
        }
        
        logger.info(f"Proactive Conversation Engine initialized: {self.agent_id}")
    
    async def should_initiate_conversation(self, context: ConversationContext) -> bool:
        """Determine if Native should proactively start a conversation"""
        
        # Check user availability
        if context.user_availability == "do_not_disturb":
            return False
        
        # High urgency always initiates
        if context.urgency == "critical":
            return True
        
        # Check conversation frequency limits
        recent_conversations = await self._get_recent_conversations()
        if len(recent_conversations) > 5:  # Max 5 proactive conversations per day
            return False
        
        # Evaluate trigger importance
        importance_score = await self._calculate_importance(context)
        
        # Threshold based on urgency
        thresholds = {
            "low": 0.8,
            "medium": 0.6,
            "high": 0.4,
            "critical": 0.0
        }
        
        return importance_score >= thresholds.get(context.urgency, 0.6)
    
    async def generate_proactive_message(self, context: ConversationContext) -> str:
        """Generate a natural, contextual proactive message"""
        
        # Select appropriate personality prompt
        prompt_type = self._select_prompt_type(context.trigger_type)
        base_prompt = self.personality_prompts.get(prompt_type, self.personality_prompts["base"])
        
        # Build context-aware prompt
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
        # implementation depends on platform
        # this would integrate with Telegram, Slack, etc.
        pass   

    async def _log_proactive_conversation(self, 
        user_id: str, 
        context: ConversationContext,
        message: str, 
        result: Dict[str, Any]):
        """Log proactive conversation for learning and analytics"""
        # implementation depends on logging system
        # this would integrate with logging system
        pass

    async def _get_recent_conversations(self) -> List[Dict]:
        """Get recent proactive conversations to avoid spam"""
        # Implementation would query conversation history
        return []

class ProactiveScheduler:
    """Schedules and triggers proactive conversations"""

    def __init__(self, conversation_engine: ProactiveConversationEngine):
        self.conversation_engine = conversation_engine
        self.running = False
        self.triggers = []

    async def start(self):
        """Start the proactive scheduler"""
        self.running = True

        await self._schedule_time_triggers()

        await self._start_event_monitoring()
        
        logger.info("Proactive conversation scheduler started")

    async def add_trigger(self, trigger_type: ConversationTrigger, conditions: Dict[str, Any], user_id: str):
        """Add a new proactive conversation trigger"""

        trigger = {
            "type": trigger_type,
            "conditions": conditions,
            "user_id": user_id,
            "timestamp": datetime.now()
        }

        self.triggers.append(trigger)
        logger.info(f"Added proactive trigger: {trigger_type.value}")

    async def _schedule_time_triggers(self):
        """Schedule time-based proactive triggers"""
        # implementation for scheduling daily/weekly conversations
        pass

    async def _start_event_monitoring(self):
        """Monitor for events that should trigger proactive conversations"""
        # implementation for monitoring events
        pass

    async def stop(self):
        """Stop the proactive conversation scheduler"""
        self.running = False
        logger.info("Proactive conversation scheduler stopped")
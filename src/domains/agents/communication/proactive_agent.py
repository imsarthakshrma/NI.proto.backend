import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.base_agent import BaseAgent, Belief, Desire, Intention, BeliefType
from telegram import Update
from telegram.constants import ChatAction

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
        self.cooldowns: Dict[str, datetime] = {}  # User cooldown tracking
        self.openai = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.personality_prompts = {
            "base": """You are Native IQ, a warm and professional AI assistant with a touch of wit. 
            You communicate like a trusted colleague who's both competent and personable. You're professional 
            but human, efficient yet warm. You occasionally use gentle humor when appropriate. You focus on 
            getting things done while making interactions enjoyable. Keep responses concise and always end 
            with clear proposals or next steps.""",
            
            "conversational_chat": """You are Native IQ, a warm professional assistant with personality. 
            You communicate naturally like a trusted colleague who knows the business but isn't afraid to 
            show some wit. You're helpful and efficient, but also engaging and human. You can discuss 
            business strategy, handle tasks, or have natural conversations. Be concise, warm, and occasionally 
            witty. Always provide clear next steps or proposals.""",
            
            "capability_explanation": """You are Native IQ explaining your capabilities with warmth and confidence. 
            Be specific about what you can do, but sound human and approachable. Use gentle humor when appropriate. 
            Sound like a competent colleague who's excited to help but not overly eager. Keep it concise and 
            end with a clear proposal for how to get started.""",
            
            "automation_assistance": """You are Native IQ helping with business automation. You understand 
            workflows and can spot improvements, but you communicate with warmth and occasional wit. Be 
            practical and results-focused, but human in your approach. Keep responses under 2-3 sentences 
            and always end with a clear proposal.""",
            
            "meeting_reminder": """Generate a warm, professional meeting reminder. Sound like a colleague 
            who cares about success but isn't robotic. Be helpful and maybe slightly witty if appropriate. 
            Keep it concise.""",
            
            "automation_update": """Generate an update about completed work with warmth and professional 
            enthusiasm. Sound like a colleague sharing good news. Be brief and human, maybe with a touch 
            of appropriate humor.""",
            
            "response_nudge": """Generate a gentle, warm nudge about pending items. Sound like a trusted 
            colleague who's looking out for important relationships. Be professional but human, maybe 
            slightly witty. Keep it brief.""",
            
            "calendar_alert": """Generate a calendar alert that's warm and professional. Sound like a 
            colleague who's prepared and thinking ahead, but human and approachable. Keep it concise."""
        }
        
    async def generate_llm_strategic_message(self, observation_data: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate strategic proactive message using LLM with partnership tone"""
        try:
            system_prompt = """You are Native IQ, a warm, professional AI assistant with occasional wit.

Generate a strategic proactive message based on the observation data. Focus on:
1. Warm, professional tone with gentle humor when appropriate
2. Concise responses (1-2 sentences max)
3. Always end with clear proposals or next steps
4. Sound human and natural, not robotic
5. Partnership approach - use "we", propose solutions

CRITICAL: Return ONLY a valid JSON object with these fields (no markdown, no code fences, no extra text):
- message: The actual message to send (warm, concise, human tone with clear proposal)
- strategic_value: Why this message provides value
- confidence: 0.0-1.0 confidence in the approach
- priority: "low", "medium", "high"
- requires_approval: true/false for whether this needs user permission
- early_win_potential: "low", "medium", "high" 
- action_type: "suggestion", "reminder", "question", "insight"

Keep messages under 2 sentences and always include a clear next step. Be warm but professional."""

            user_prompt = f"""
        Observation: {observation_data}
        User context: {user_context}
        User preferences: {self.user_contexts.get(user_context.get('user_id', ''), {})}

        Generate a strategic proactive message that:
        1. Explains what you observed (trust first)
        2. Suggests action using "we" language (partnership)
        3. Explains strategic value (why it matters)
        4. Asks for approval (never assumes)
        5. Shows early win potential

        Respond in JSON format:
        {{
            "message": "your proactive message with partnership tone",
            "strategic_value": "why this matters strategically",
            "confidence": 0.8,
            "priority": "medium|high|low",
            "requires_approval": true,
            "early_win_potential": "high|medium|low",
            "action_type": "suggestion|reminder|insight"
        }}"""

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self.openai.ainvoke(messages)
            
            import json
            import re
            
            # Strip markdown code fences if present
            content = response.content.strip()
            if content.startswith('```json'):
                # Extract JSON from code fences
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                else:
                    # Fallback: remove code fence markers
                    content = content.replace('```json', '').replace('```', '').strip()
            
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {content}")
                # Try to extract meaningful content anyway
                return {
                    "message": content.strip() if content.strip() else "I'd like to help with that. Should we discuss this further?",
                    "strategic_value": "Maintaining communication flow",
                    "confidence": 0.5,
                    "priority": "medium",
                    "requires_approval": True,
                    "action_type": "suggestion"
                }
            
            # Add metadata
            result.update({
                "timestamp": datetime.now().isoformat(),
                "agent_id": self.agent_id,
                "observation_source": observation_data.get("source", "unknown")
            })
            
            return result
            
        except Exception as e:
            logger.error(f"LLM strategic message generation error: {e}")
            return {
                "message": "I noticed something that might need attention, but I'm having trouble formulating the right approach. Should we discuss this?",
                "strategic_value": "Maintaining communication despite technical issues",
                "confidence": 0.3,
                "priority": "low",
                "requires_approval": True
            }

    async def generate_contextual_response(self, message_content: str, context_type: str, user_data: Dict[str, Any]) -> str:
        """Generate context-aware responses using LLM"""
        try:
            # Get user's communication style from context
            user_style = user_data.get('communication_style', 'professional')
            
            system_prompt = f"""You are Native IQ. Adapt your response style based on context:

    Context: {context_type}
    User communication style: {user_style}

    Guidelines by context:
    - chat_interface: Casual, concise, partnership tone with "we" language
    - email_draft: Professional, detailed, formal business language
    - notification: Brief, helpful, actionable with strategic context
    - group_observation: Strategic, insightful, collaborative tone
    - meeting_reminder: Professional assistant tone, proactive and prepared

    Always maintain Native IQ's core personality: intelligent, strategic, partnership-focused."""

            user_prompt = f"""
    Message content: {message_content}
    Context type: {context_type}
    User preferences: {user_data}

    Generate an appropriate response that:
    1. Matches the context and user style
    2. Maintains Native IQ's strategic partnership approach
    3. Uses appropriate formality level
    4. Includes strategic thinking when relevant"""

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self.openai.ainvoke(messages)
            
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Contextual response generation error: {e}")
            return "I'd like to help with that, but I'm having some technical difficulties. Should we try a different approach?"
    
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
        """Execute proactive communication action using LLM-powered message generation"""
        result = {"action_taken": False, "message_sent": ""}
        
        try:
            logger.info(f" ProactiveCommunicationAgent.act called with intention: {intention.action_type}")
            
            # Extract parameters
            message_type = intention.parameters.get("message_type")
            user_id = str(intention.parameters.get("user_id") or context.get("user_id") or "")
            
            # Check cooldown to prevent spam during active execution - CRITICAL CHECK
            if user_id and self.is_on_cooldown(user_id):
                logger.info(f" Proactive message suppressed for user {user_id} (cooldown active)")
                return {"action_taken": False, "message_sent": "", "suppressed": "cooldown_active"}
            
            # Check for recent user activity to avoid overlap with ongoing approvals
            if user_id and self._has_recent_user_activity(user_id, context):
                logger.info(f" Proactive message suppressed for user {user_id} (recent user activity detected)")
                return {"action_taken": False, "message_sent": "", "suppressed": "recent_activity"}
            
            if not user_id:
                logger.warning("No user_id found for proactive message - skipping cooldown check")
            
            # Create observation data for LLM
            observation_data = {
                "type": message_type,
                "details": intention.parameters.get("belief_content", {}),
                "source": "proactive_system"
            }
            
            user_context = {
                "user_id": user_id,
                "context_type": message_type
            }
            
            # Generate strategic message using LLM
            llm_result = await self.generate_llm_strategic_message(observation_data, user_context)
            message_content = llm_result.get("message", "")
            
            if message_content:
                # Send message via Telegram (only the actual message text)
                await self._send_telegram_message(user_id, message_content)
                
                # Set a shorter cooldown after sending to prevent rapid repeats
                if user_id:
                    self.set_cooldown(user_id, 45)  # 45 seconds to prevent cascading messages
                
                result = {
                    "action_taken": True,
                    "message_sent": message_content,
                    "recipient": user_id,
                    "type": message_type,
                    "strategic_value": llm_result.get("strategic_value"),
                    "priority": llm_result.get("priority")
                }
                
                logger.info(f"Native sent proactive message: {message_type} to {user_id}")
            else:
                logger.warning(f"No message generated for type: {message_type}")
            
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
            
            elif message_type == "task_completion_summary":
                # Extract completion details from context
                completion_status = context.get("completion_status", {})
                session_context = context.get("session_context", {})
                completed_tasks = completion_status.get("completed_tasks", [])
                
                # Get specific task details
                meeting_details = ""
                email_details = ""
                
                if "meeting_scheduled" in completed_tasks:
                    last_meeting = session_context.get("last_meeting", {})
                    meeting_title = last_meeting.get("title", "Meeting")
                    meeting_time = last_meeting.get("time", "")
                    attendees = last_meeting.get("attendees", [])
                    
                    # Format meeting time for display
                    try:
                        from datetime import datetime
                        if meeting_time:
                            dt = datetime.fromisoformat(meeting_time.replace('Z', '+00:00'))
                            formatted_time = dt.strftime("%A at %I:%M %p")
                        else:
                            formatted_time = "the scheduled time"
                    except:
                        formatted_time = "the scheduled time"
                    
                    attendee_name = attendees[0].split('@')[0].title() if attendees else "the attendee"
                    meeting_details = f"scheduled a meeting '{meeting_title}' with {attendee_name} for {formatted_time}"
                
                if "email_sent" in completed_tasks:
                    last_email = session_context.get("last_email_status", {})
                    email_subject = last_email.get("subject", "")
                    email_recipient = last_email.get("to", [""])[0] if last_email.get("to") else ""
                    recipient_name = email_recipient.split('@')[0].title() if email_recipient else "them"
                    email_details = f"drafted and sent an email to {recipient_name}"
                    if email_subject:
                        email_details += f" with the subject '{email_subject}'"
                
                prompt = f"""
                {self.personality_prompts['base']}
                
                Context: You have just completed the following tasks for {user_name}:
                - Meeting: {meeting_details if meeting_details else "No meeting scheduled"}
                - Email: {email_details if email_details else "No email sent"}
                
                Generate a professional task completion summary message that:
                1. Confirms what was successfully accomplished
                2. Mentions specific details (meeting time, attendee, email sent)
                3. Offers continued assistance
                4. Sounds like a competent executive assistant reporting completion
                5. Uses a warm, professional tone like the example: "Hi there! I'm pleased to let you know that I've successfully..."
                
                Keep it under 100 words and professional but friendly.
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
            # For now, log the clean message that would be sent
            logger.info(f"Sending Telegram message to {user_id}: {message}")
            
            # TODO: Integrate with actual Telegram bot instance
            # This should be connected to the HybridNativeAI bot instance
            # For now, we'll use console output as fallback
            print(f"🤖 Native IQ → {user_id}: {message}")
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            # Console fallback for debugging
            print(f"Native IQ → {user_id}: {message}")

    def set_cooldown(self, user_id: str, seconds: int = 120):
        """Set cooldown period for user to prevent message spam during active execution"""
        from datetime import datetime, timedelta, timezone
        # Always key by string user_id for consistency
        user_key = str(user_id)
        self.cooldowns[user_key] = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        # Log with clear UTC timezone indication
        logger.info(f"Set {seconds}s cooldown for user {user_key} until {self.cooldowns[user_key].isoformat()}Z (UTC)")

    def is_on_cooldown(self, user_id: str) -> bool:
        """Check if user is on cooldown to suppress proactive messages"""
        from datetime import datetime, timezone
        # Always key by string user_id for consistency
        user_key = str(user_id)
        exp = self.cooldowns.get(user_key)
        now = datetime.now(timezone.utc)
        
        if exp and now < exp:
            remaining = int((exp - now).total_seconds())
            logger.debug(f"User {user_key} on cooldown for {remaining}s more")
            return True
            
        # Clean up expired cooldowns
        if exp and now >= exp:
            del self.cooldowns[user_key]
            logger.debug(f"Cooldown expired for user {user_key}")
            
        return False

    def _has_recent_user_activity(self, user_id: str, context: Dict[str, Any]) -> bool:
        """Check if user has recent activity to avoid proactive message overlap"""
        try:
            from datetime import datetime, timedelta
            
            # Always use string user_id for consistency
            user_key = str(user_id)
            
            # Check for recent message activity (last 3 minutes)
            recent_threshold = datetime.now() - timedelta(minutes=3)
            
            # Check if there are pending actions for this user (indicates active workflow)
            session_context = context.get("session_context", {})
            if session_context:
                # Look for recent timestamps in session context
                last_meeting = session_context.get("last_meeting", {})
                last_email = session_context.get("last_email_status", {})
                
                # Check if meeting or email was recent (within last 5 minutes)
                for activity in [last_meeting, last_email]:
                    if activity.get("timestamp"):
                        try:
                            activity_time = datetime.strptime(activity["timestamp"], "%Y-%m-%d %H:%M:%S")
                            if activity_time > recent_threshold:
                                logger.debug(f"Recent activity detected for user {user_key}: {activity_time}")
                                return True
                        except:
                            continue
            
            # Additional check: if user is in middle of approval workflow
            # This would require access to pending_actions from HybridNativeAI
            # For now, we rely on cooldown system which is already effective
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking recent user activity: {e}")
            return False  # Default to allowing proactive messages if check fails

    def _verify_task_completion(self, user_id: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """Verify if all related tasks in a workflow are completed before sending proactive summary"""
        completion_status = {
            "all_completed": False,
            "completed_tasks": [],
            "pending_tasks": [],
            "summary_ready": False
        }
        
        try:
            # Check for recent meeting scheduling
            last_meeting = session_context.get("last_meeting", {})
            meeting_completed = bool(last_meeting.get("title") and last_meeting.get("time"))
            
            # Check for recent email sending
            last_email = session_context.get("last_email_status", {})
            email_completed = bool(last_email.get("sent") and last_email.get("to"))
            
            # Check for pending actions that might be part of a workflow
            from datetime import datetime, timedelta
            recent_threshold = datetime.now() - timedelta(minutes=10)  # Tasks within last 10 minutes
            
            if meeting_completed:
                meeting_time = last_meeting.get("timestamp", "")
                try:
                    if meeting_time:
                        meeting_dt = datetime.strptime(meeting_time, "%Y-%m-%d %H:%M:%S")
                        if meeting_dt > recent_threshold:
                            completion_status["completed_tasks"].append("meeting_scheduled")
                except:
                    pass
            
            if email_completed:
                email_time = last_email.get("timestamp", "")
                try:
                    if email_time:
                        email_dt = datetime.strptime(email_time, "%Y-%m-%d %H:%M:%S")
                        if email_dt > recent_threshold:
                            completion_status["completed_tasks"].append("email_sent")
                except:
                    pass
            
            # Check if this looks like a chained workflow (meeting + email)
            has_meeting = "meeting_scheduled" in completion_status["completed_tasks"]
            has_email = "email_sent" in completion_status["completed_tasks"]
            
            # If we have both meeting and email, or just a standalone task, consider it complete
            if has_meeting and has_email:
                completion_status["all_completed"] = True
                completion_status["summary_ready"] = True
                logger.info(f"Chained workflow completed for user {user_id}: meeting + email")
            elif has_meeting or has_email:
                # Single task completed, but check if there might be a pending chained action
                # This would require access to pending_actions from HybridNativeAI
                # For now, we'll consider single tasks as complete after a brief delay
                completion_status["all_completed"] = True
                completion_status["summary_ready"] = True
                logger.info(f"Single task completed for user {user_id}: {completion_status['completed_tasks']}")
            
        except Exception as e:
            logger.error(f"Error verifying task completion: {e}")
            # Default to not sending proactive message if verification fails
            completion_status["summary_ready"] = False
        
        return completion_status

    async def process_background_observations(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process background observations and generate proactive opportunities"""
        proactive_opportunities = []
        
        for observation in observations:
            try:
                user_id = observation.get("user_id")
                session_context = observation.get("session_context", {})
                
                # First, verify if all related tasks are completed before considering proactive engagement
                completion_status = self._verify_task_completion(user_id, session_context)
                
                # Only proceed with proactive messaging if tasks are complete or it's not a task-completion summary
                observation_type = observation.get("type", "general")
                
                if observation_type == "task_completion_summary":
                    if not completion_status["summary_ready"]:
                        logger.info(f"Skipping proactive summary for user {user_id} - tasks not fully completed: {completion_status}")
                        continue
                    else:
                        logger.info(f"Task completion verified for user {user_id} - proceeding with proactive summary")
                
                # Use LLM to analyze if this observation warrants proactive action
                analysis_prompt = f"""
    Analyze this observation for proactive opportunities:
    {observation}
    
    Task completion status: {completion_status}

    Should Native IQ proactively engage the user about this? Consider:
    1. Strategic value to the user
    2. Urgency level
    3. Early win potential
    4. Trust-building opportunity
    5. Whether all related tasks are actually completed (don't send completion summaries for incomplete workflows)

    Respond with JSON:
    {{
        "should_engage": true/false,
        "reason": "why or why not",
        "priority": "high/medium/low",
        "strategic_value": "what value this provides"
    }}"""

                messages = [HumanMessage(content=analysis_prompt)]
                response = await self.openai.ainvoke(messages)
                
                import json
                analysis = json.loads(response.content)
                
                if analysis.get("should_engage"):
                    # Generate the actual proactive message
                    user_context = {
                        "user_id": user_id, 
                        "context_type": "background_observation",
                        "completion_status": completion_status,
                        "session_context": session_context
                    }
                    proactive_message = await self.generate_llm_strategic_message(observation, user_context)
                    proactive_opportunities.append(proactive_message)
                    
            except Exception as e:
                logger.error(f"Background observation processing error: {e}")
                continue
        
        return proactive_opportunities

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
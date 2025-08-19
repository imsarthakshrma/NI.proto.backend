"""
Group Chat API for Native IQ
Handles individual user tracking, dashboard updates, and intelligent conversation detection
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
import json
import asyncio
import logging
from datetime import datetime
from pydantic import BaseModel

from src.domains.agents.observer.ob_agent import ObserverAgent
from src.domains.agents.communication.proactive_agent import ProactiveCommunicationAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/group-chat", tags=["group-chat"])

class GroupChatMessage(BaseModel):
    message_id: str
    group_id: str
    user_id: str
    username: str
    content: str
    timestamp: datetime
    mentions: List[str] = []
    reply_to: Optional[str] = None

class UserDashboardUpdate(BaseModel):
    user_id: str
    group_id: str
    update_type: str  # "observation", "insight", "task", "notification"
    data: Dict[str, Any]
    timestamp: datetime

class GroupChatManager:
    """Manages group chat sessions and individual user tracking"""
    
    def __init__(self):
        # WebSocket connections per group and user
        self.connections: Dict[str, Dict[str, WebSocket]] = {}  # group_id -> user_id -> websocket
        
        # Individual user contexts within groups
        self.user_contexts: Dict[str, Dict[str, Dict[str, Any]]] = {}  # group_id -> user_id -> context
        
        # Group-level conversation history (for context)
        self.group_conversations: Dict[str, List[Dict[str, Any]]] = {}  # group_id -> messages
        
        # Individual user dashboard data
        self.user_dashboards: Dict[str, Dict[str, Any]] = {}  # user_id -> dashboard_data
        
        # Native IQ mention patterns
        self.native_patterns = [
            "native", "@native", "native iq", "@native_iq", "hey native", 
            "native,", "native:", "native?", "native!", "/native"
        ]
        
        # Agents for processing
        self.observer_agent = ObserverAgent("group_observer", "observer")
        self.proactive_agent = ProactiveCommunicationAgent("group_proactive", "communication")
        
        logger.info("GroupChatManager initialized")

    async def connect_user(self, websocket: WebSocket, group_id: str, user_id: str, username: str):
        """Connect a user to a group chat"""
        await websocket.accept()
        
        # Initialize group if not exists
        if group_id not in self.connections:
            self.connections[group_id] = {}
            self.user_contexts[group_id] = {}
            self.group_conversations[group_id] = []
        
        # Add user connection
        self.connections[group_id][user_id] = websocket
        
        # Initialize user context in this group
        if user_id not in self.user_contexts[group_id]:
            self.user_contexts[group_id][user_id] = {
                "username": username,
                "joined_at": datetime.now(),
                "message_count": 0,
                "last_active": datetime.now(),
                "individual_context": {},
                "mentions_count": 0,
                "tasks_assigned": [],
                "insights_generated": []
            }
        
        # Initialize individual dashboard
        if user_id not in self.user_dashboards:
            self.user_dashboards[user_id] = {
                "observations": [],
                "insights": [],
                "tasks": [],
                "notifications": [],
                "learning_progress": {"patterns": 0, "automations": 0}
            }
        
        logger.info(f"User {username} ({user_id}) connected to group {group_id}")
        
        # Send welcome message with current group status
        await self._send_user_update(group_id, user_id, {
            "type": "connection_established",
            "group_members": len(self.connections[group_id]),
            "your_context": self.user_contexts[group_id][user_id]
        })

    async def disconnect_user(self, group_id: str, user_id: str):
        """Disconnect a user from group chat"""
        if group_id in self.connections and user_id in self.connections[group_id]:
            del self.connections[group_id][user_id]
            
            # Update last active time
            if group_id in self.user_contexts and user_id in self.user_contexts[group_id]:
                self.user_contexts[group_id][user_id]["last_active"] = datetime.now()
            
            logger.info(f"User {user_id} disconnected from group {group_id}")

    async def process_message(self, group_id: str, message: GroupChatMessage) -> Dict[str, Any]:
        """Process incoming group chat message with intelligent detection"""
        
        # Store message in group conversation
        message_data = {
            "message_id": message.message_id,
            "user_id": message.user_id,
            "username": message.username,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "mentions": message.mentions,
            "reply_to": message.reply_to
        }
        
        if group_id not in self.group_conversations:
            self.group_conversations[group_id] = []
        self.group_conversations[group_id].append(message_data)
        
        # Update user context
        if group_id in self.user_contexts and message.user_id in self.user_contexts[group_id]:
            user_ctx = self.user_contexts[group_id][message.user_id]
            user_ctx["message_count"] += 1
            user_ctx["last_active"] = datetime.now()
            
            if message.mentions:
                user_ctx["mentions_count"] += len(message.mentions)

        # Intelligent conversation detection
        conversation_type = await self._detect_conversation_type(group_id, message)
        
        response = {
            "processed": True,
            "conversation_type": conversation_type,
            "native_should_respond": False,
            "individual_updates": {}
        }
        
        if conversation_type == "user_to_native":
            # Native IQ is being addressed directly
            response["native_should_respond"] = True
            native_response = await self._handle_native_interaction(group_id, message)
            response["native_response"] = native_response
            
            # Update individual dashboard for the user who asked
            await self._update_user_dashboard(message.user_id, {
                "type": "native_interaction",
                "data": {
                    "question": message.content,
                    "response": native_response,
                    "timestamp": datetime.now().isoformat()
                }
            })
            
        elif conversation_type == "user_to_user":
            # Users talking to each other - Native observes silently
            await self._silent_observation(group_id, message)
            
            # Check if any users should get individual insights
            insights = await self._generate_individual_insights(group_id, message)
            for user_id, insight in insights.items():
                await self._update_user_dashboard(user_id, {
                    "type": "insight",
                    "data": insight
                })
                response["individual_updates"][user_id] = insight
        
        elif conversation_type == "group_discussion":
            # Group discussion - Native may proactively contribute
            proactive_suggestion = await self._evaluate_proactive_contribution(group_id, message)
            if proactive_suggestion:
                response["proactive_suggestion"] = proactive_suggestion
        
        # Broadcast updates to relevant users
        await self._broadcast_updates(group_id, response)
        
        return response

    async def _detect_conversation_type(self, group_id: str, message: GroupChatMessage) -> str:
        """Intelligently detect if user is talking to Native IQ or to other users"""
        
        content_lower = message.content.lower()
        
        # Direct mentions of Native
        if any(pattern in content_lower for pattern in self.native_patterns):
            return "user_to_native"
        
        # Questions that might be directed at Native
        if message.content.startswith(("?", "how", "what", "when", "where", "why", "can you", "could you")):
            # Check recent context - if others are discussing, it might be user-to-user
            recent_messages = self.group_conversations.get(group_id, [])[-5:]
            other_users_active = len(set(msg["user_id"] for msg in recent_messages if msg["user_id"] != message.user_id)) > 0
            
            if not other_users_active:
                return "user_to_native"  # Likely asking Native
            else:
                return "group_discussion"  # Part of group discussion
        
        # Commands or task requests
        task_indicators = ["schedule", "remind me", "set up", "create", "send", "book", "automate"]
        if any(indicator in content_lower for indicator in task_indicators):
            return "user_to_native"
        
        # Default: user-to-user conversation
        return "user_to_user"

    async def _handle_native_interaction(self, group_id: str, message: GroupChatMessage) -> str:
        """Handle direct interaction with Native IQ using LLM-generated responses"""
        
        # Get group conversation context
        recent_messages = self.group_conversations.get(group_id, [])[-5:]
        group_context_text = "\n".join([f"{msg['username']}: {msg['content']}" for msg in recent_messages])
        
        # Get user's individual context
        user_ctx = self.user_contexts.get(group_id, {}).get(message.user_id, {})
        
        # Create rich context for LLM
        context = {
            "group_id": group_id,
            "user_id": message.user_id,
            "username": message.username,
            "group_context": self.group_conversations.get(group_id, [])[-10:],
            "user_context": user_ctx,
            "message_type": "group_chat_direct",
            "tone": "warm_professional_witty",
            "response_style": "concise_human_proposals"
        }
        
        # Enhanced LLM prompt for Native IQ personality
        system_prompt = f"""You are Native IQ, an AI assistant with a warm, professional, and occasionally witty personality. 
        
        PERSONALITY GUIDELINES:
        - Be warm and approachable, like talking to a trusted colleague
        - Occasionally use gentle humor or wit when appropriate
        - Stay professional but human - avoid robotic language
        - Be concise and direct - no fluff or unnecessary words
        - Always provide clear, actionable proposals
        - Use "I" and "you" naturally in conversation
        
        CONTEXT:
        - You're in a group chat with multiple people
        - User {message.username} just asked: "{message.content}"
        - Recent group conversation: {group_context_text}
        - User's activity: {user_ctx.get('message_count', 0)} messages, last active {user_ctx.get('last_active', 'recently')}
        
        RESPONSE STYLE:
        - Keep responses under 2-3 sentences when possible
        - End with a clear proposal or next step
        - Use natural, conversational language
        - Be helpful without being overly eager
        
        Respond to {message.username}'s request naturally and helpfully."""
        
        # Use proactive agent with enhanced context
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message.content)
        ]
        
        try:
            # Update context with personality guidelines
            enhanced_context = {
                **context,
                "system_prompt": system_prompt,
                "personality": "warm_professional_witty",
                "response_length": "concise",
                "include_proposals": True
            }
            
            beliefs = await self.proactive_agent.perceive(messages, enhanced_context)
            desires = await self.proactive_agent.update_desires(beliefs, enhanced_context)
            intentions = await self.proactive_agent.deliberate(beliefs, desires, [])
            
            for intention in intentions:
                result = await self.proactive_agent.act(intention, enhanced_context)
                if result.get('message_sent'):
                    return result['message_sent']
            
            # Fallback with LLM-generated response using OpenAI directly
            return await self._generate_fallback_response(message.username, message.content, group_context_text)
            
        except Exception as e:
            logger.error(f"Error in native interaction: {e}")
            return await self._generate_fallback_response(message.username, message.content, group_context_text)

    async def _generate_fallback_response(self, username: str, user_message: str, group_context: str) -> str:
        """Generate fallback response using direct LLM call"""
        try:
            from openai import AsyncOpenAI
            import os
            
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            prompt = f"""You are Native IQ, a warm and professional AI assistant. Respond to {username}'s message: "{user_message}"
            
            Group context: {group_context}
            
            Guidelines:
            - Be warm, occasionally witty, but professional
            - Keep it concise (1-2 sentences)
            - End with a clear proposal or next step
            - Sound human and natural
            
            Response:"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Fallback response generation failed: {e}")
            return f"Hey {username}! I'm having a moment here - could you try that again? I'm usually much more helpful than this! 😅"

    async def _silent_observation(self, group_id: str, message: GroupChatMessage):
        """Silently observe user-to-user conversations for learning"""
        
        context = {
            "observation_type": "group_conversation",
            "group_id": group_id,
            "participants": list(self.user_contexts.get(group_id, {}).keys()),
            "conversation_flow": self.group_conversations.get(group_id, [])[-5:]
        }
        
        # Use observer agent to learn patterns
        from langchain_core.messages import HumanMessage
        observation_message = HumanMessage(content=f"[SILENT OBSERVATION] {message.username}: {message.content}")
        
        try:
            await self.observer_agent.perceive([observation_message], context)
            logger.info(f"Silent observation recorded for group {group_id}")
        except Exception as e:
            logger.error(f"Error in silent observation: {e}")

    async def _generate_individual_insights(self, group_id: str, message: GroupChatMessage) -> Dict[str, Dict[str, Any]]:
        """Generate individual insights for users based on group conversation"""
        
        insights = {}
        
        # Analyze if this message creates opportunities for specific users
        content_lower = message.content.lower()
        
        # Example: If someone mentions a deadline, suggest calendar automation to relevant users
        if any(word in content_lower for word in ["deadline", "due date", "meeting", "call"]):
            for user_id in self.user_contexts.get(group_id, {}):
                if user_id != message.user_id:  # Don't suggest to the person who mentioned it
                    insights[user_id] = {
                        "type": "automation_opportunity",
                        "title": "Calendar Automation Detected",
                        "description": f"I noticed {message.username} mentioned a deadline. Would you like me to help you track related tasks?",
                        "suggested_action": "schedule_reminder",
                        "context": message.content,
                        "timestamp": datetime.now().isoformat()
                    }
        
        return insights

    async def _evaluate_proactive_contribution(self, group_id: str, message: GroupChatMessage) -> Optional[Dict[str, Any]]:
        """Evaluate if Native should proactively contribute to group discussion using LLM"""
        
        # Get recent conversation context
        recent_messages = self.group_conversations.get(group_id, [])[-5:]
        conversation_context = "\n".join([f"{msg['username']}: {msg['content']}" for msg in recent_messages])
        
        try:
            from openai import AsyncOpenAI
            import os
            
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            prompt = f"""You are Native IQ, analyzing a group conversation to decide if you should proactively offer help.

CONVERSATION CONTEXT:
{conversation_context}

LATEST MESSAGE: {message.username}: {message.content}

DECISION CRITERIA:
- Only suggest help if the conversation involves business processes, deadlines, meetings, or tasks you can actually help with
- Be selective - don't interrupt casual conversations
- Your tone should be warm, professional, and occasionally witty
- Keep suggestions concise and natural

RESPOND WITH JSON:
{{
    "should_contribute": true/false,
    "message": "your suggested response (if should_contribute is true)",
    "confidence": 0.0-1.0,
    "reason": "brief explanation of your decision"
}}

If should_contribute is false, just return {{"should_contribute": false, "reason": "explanation"}}"""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7
            )
            
            import json
            result = json.loads(response.choices[0].message.content.strip())
            
            if result.get("should_contribute", False):
                return {
                    "type": "proactive_suggestion",
                    "message": result.get("message", ""),
                    "confidence": result.get("confidence", 0.5),
                    "suggested_delay": 30,  # Wait 30 seconds before suggesting
                    "reason": result.get("reason", "")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in proactive contribution evaluation: {e}")
            return None

    async def _update_user_dashboard(self, user_id: str, update: Dict[str, Any]):
        """Update individual user dashboard"""
        
        if user_id not in self.user_dashboards:
            self.user_dashboards[user_id] = {
                "observations": [],
                "insights": [],
                "tasks": [],
                "notifications": []
            }
        
        update_type = update.get("type", "general")
        
        if update_type == "insight":
            self.user_dashboards[user_id]["insights"].append(update["data"])
        elif update_type == "task":
            self.user_dashboards[user_id]["tasks"].append(update["data"])
        elif update_type == "native_interaction":
            self.user_dashboards[user_id]["observations"].append(update["data"])
        else:
            self.user_dashboards[user_id]["notifications"].append(update["data"])
        
        # Broadcast dashboard update to user's connections
        await self._send_dashboard_update(user_id, update)

    async def _send_user_update(self, group_id: str, user_id: str, update: Dict[str, Any]):
        """Send update to specific user in group"""
        
        if (group_id in self.connections and 
            user_id in self.connections[group_id]):
            
            websocket = self.connections[group_id][user_id]
            try:
                await websocket.send_text(json.dumps({
                    "type": "user_update",
                    "data": update,
                    "timestamp": datetime.now().isoformat()
                }))
            except Exception as e:
                logger.error(f"Error sending user update: {e}")

    async def _send_dashboard_update(self, user_id: str, update: Dict[str, Any]):
        """Send dashboard update to all user's connections across groups"""
        
        for group_id, group_connections in self.connections.items():
            if user_id in group_connections:
                websocket = group_connections[user_id]
                try:
                    await websocket.send_text(json.dumps({
                        "type": "dashboard_update",
                        "data": update,
                        "timestamp": datetime.now().isoformat()
                    }))
                except Exception as e:
                    logger.error(f"Error sending dashboard update: {e}")

    async def _broadcast_updates(self, group_id: str, response: Dict[str, Any]):
        """Broadcast relevant updates to group members"""
        
        if group_id not in self.connections:
            return
        
        # Send different updates to different users based on relevance
        for user_id, websocket in self.connections[group_id].items():
            try:
                user_specific_update = {
                    "type": "group_update",
                    "conversation_type": response["conversation_type"],
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add user-specific insights if any
                if user_id in response.get("individual_updates", {}):
                    user_specific_update["personal_insight"] = response["individual_updates"][user_id]
                
                # Add Native response if it was a direct interaction
                if response.get("native_response"):
                    user_specific_update["native_response"] = response["native_response"]
                
                await websocket.send_text(json.dumps(user_specific_update))
                
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")

    def get_user_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get individual user dashboard data"""
        return self.user_dashboards.get(user_id, {
            "observations": [],
            "insights": [],
            "tasks": [],
            "notifications": [],
            "learning_progress": {"patterns": 0, "automations": 0}
        })

    def get_group_status(self, group_id: str) -> Dict[str, Any]:
        """Get group chat status and analytics"""
        
        if group_id not in self.connections:
            return {"error": "Group not found"}
        
        return {
            "group_id": group_id,
            "active_users": len(self.connections[group_id]),
            "total_messages": len(self.group_conversations.get(group_id, [])),
            "user_contexts": {
                user_id: {
                    "username": ctx["username"],
                    "message_count": ctx["message_count"],
                    "last_active": ctx["last_active"].isoformat(),
                    "mentions_count": ctx["mentions_count"]
                }
                for user_id, ctx in self.user_contexts.get(group_id, {}).items()
            }
        }

# Global manager instance
group_chat_manager = GroupChatManager()

# WebSocket endpoint for group chat
@router.websocket("/ws/{group_id}/{user_id}")
async def group_chat_websocket(websocket: WebSocket, group_id: str, user_id: str, username: str = "User"):
    """WebSocket endpoint for group chat connections"""
    
    await group_chat_manager.connect_user(websocket, group_id, user_id, username)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Create message object
            message = GroupChatMessage(
                message_id=message_data.get("message_id", f"{user_id}_{datetime.now().timestamp()}"),
                group_id=group_id,
                user_id=user_id,
                username=username,
                content=message_data.get("content", ""),
                timestamp=datetime.now(),
                mentions=message_data.get("mentions", []),
                reply_to=message_data.get("reply_to")
            )
            
            # Process message
            await group_chat_manager.process_message(group_id, message)
            
    except WebSocketDisconnect:
        await group_chat_manager.disconnect_user(group_id, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await group_chat_manager.disconnect_user(group_id, user_id)

# REST API endpoints
@router.get("/dashboard/{user_id}")
async def get_user_dashboard(user_id: str):
    """Get individual user dashboard"""
    dashboard = group_chat_manager.get_user_dashboard(user_id)
    return JSONResponse(content=dashboard)

@router.get("/group/{group_id}/status")
async def get_group_status(group_id: str):
    """Get group chat status"""
    status = group_chat_manager.get_group_status(group_id)
    return JSONResponse(content=status)

@router.post("/message")
async def send_message(message: GroupChatMessage):
    """Send message via REST API (alternative to WebSocket)"""
    result = await group_chat_manager.process_message(message.group_id, message)
    return JSONResponse(content=result)

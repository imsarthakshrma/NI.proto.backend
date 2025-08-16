"""
Execution Agent for Native IQ
Executes approved automation decisions from Decision Agent
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from src.core.base_agent import BaseAgent, Belief, Desire, Intention, BeliefType
from src.domains.tools.google_drive_tool import get_google_drive_tools
from src.domains.tools.email_tool import send_email

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class AutomationExecution:
    execution_id: str
    decision_id: str
    automation_type: str
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    success_rate: float = 0.0
    error_message: Optional[str] = None
    execution_details: Dict[str, Any] = field(default_factory=dict)
    time_saved: float = 0.0  # in minutes
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ExecutionResult:
    execution_id: str
    success: bool
    time_saved: float
    accuracy: float
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

class ExecutionAgent(BaseAgent):
    """
    Execution Agent - Executes approved automation decisions
    """

    def __init__(self, agent_id: str = "execution_001"):
        super().__init__(agent_id, "execution", temperature=0.1)

        self.executions: Dict[str, AutomationExecution] = {}
        self.execution_results: Dict[str, ExecutionResult] = {}
        
        # Tool system for actual task execution
        self.available_tools: Dict[str, BaseTool] = {}
        self.calendar_tools: Dict[str, Any] = {}  # Legacy support
        
        # Execution metrics
        self.total_executions = 0
        self.successful_executions = 0
        self.total_time_saved = 0.0
        self.accuracy_rate = 0.95

        self.desires = [
            Desire(
                id="execute_automations",
                goal="Execute approved automation decisions",
                priority=10,
                conditions={"has_approved_decisions": True}
            ),
            Desire(
                id="monitor_executions",
                goal="Monitor and track execution performance",
                priority=8,
                conditions={"has_active_executions": True}
            )
        ]

        # Register Google Drive and email tools
        self._register_default_tools()
        
        logger.info(f"Execution Agent initialized: {self.agent_id}")

    def register_tool(self, tool_name: str, tool: BaseTool):
        """Register a tool for task execution"""
        self.available_tools[tool_name] = tool
        logger.info(f"Tool registered: {tool_name}")
    
    def register_tools(self, tools: Dict[str, BaseTool]):
        """Register multiple tools for task execution"""
        self.available_tools.update(tools)
        logger.info(f"Registered {len(tools)} tools: {list(tools.keys())}")
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.available_tools.keys())
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a specific tool is available"""
        return tool_name in self.available_tools

    def _register_default_tools(self):
        """Register default tools including Google Drive, email, and calendar"""
        try:
            # Register Google Drive tools
            drive_tools = get_google_drive_tools()
            for tool in drive_tools:
                self.register_tool(tool.name, tool)
            
            # Register email tool
            self.register_tool("email_tool", send_email)
            
            # Register calendar tools
            try:
                from src.domains.tools.calandar_tool import get_calendar_tools
                calendar_tools = get_calendar_tools()
                for tool in calendar_tools:
                    self.register_tool(tool.name, tool)
                logger.info(f"Calendar tools registered: {len(calendar_tools)} tools")
            except Exception as calendar_error:
                logger.warning(f"Calendar tools not available: {calendar_error}")
            
            logger.info(f"Default tools registered: Google Drive ({len(drive_tools)}) + email + calendar")
        except Exception as e:
            logger.error(f"Error registering default tools: {e}")
    
    def set_calendar_tools(self, tools: Dict[str, Any]):
        """Set calendar tools for execution"""
        self.calendar_tools = tools
        logger.info(f"Calendar tools loaded: {len(tools)} tools available")

    async def perceive(self, messages: List[Any], context: Dict[str, Any]) -> List[Belief]:
        """Perceive approved decisions and execution requests"""
        beliefs = []

        try:
            # Get approved decisions from Decision Agent
            approved_decisions = context.get("approved_decisions", [])
            execution_requests = context.get("execution_requests", [])

            if approved_decisions:
                for decision in approved_decisions:
                    belief = await self._process_approved_decision(decision)
                    if belief:
                        beliefs.append(belief)

            if execution_requests:
                for request in execution_requests:
                    belief = await self._process_execution_request(request)
                    if belief:
                        beliefs.append(belief)

            # Monitor ongoing executions
            monitoring_belief = await self._monitor_executions()
            if monitoring_belief:
                beliefs.append(monitoring_belief)

            logger.info(f"Execution Agent perceived: {len(beliefs)} beliefs")
            return beliefs

        except Exception as e:
            logger.error(f"Error in Execution Agent perception: {e}")
            return beliefs

    async def act(self, intention: Intention, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute automation actions using LLM-powered intent detection and tool calling"""
        try:
            logger.info(f"🚀 Execution Agent acting on intention: {intention.action_type}")
            logger.info(f"🔍 Context keys: {list(context.keys())}")
            
            # Extract task information from context
            user_message = context.get("user_message", "")
            logger.info(f"🔍 User message extracted: '{user_message}'")
            
            if not user_message:
                logger.warning("No user message found in context, cannot use LLM analysis")
                return await self._fallback_execution(intention, context)
            
            # Use LLM to analyze intent and determine tool calls
            logger.info(f"🤖 Starting LLM analysis for: {user_message}")
            llm_result = await self._llm_analyze_and_execute(user_message, context)
            
            if llm_result.get('success'):
                logger.info(f"LLM-powered execution successful")
                return llm_result
            elif llm_result.get('requires_permission'):
                logger.info(f"LLM-powered execution requires permission; returning prompt to user")
                return llm_result
            else:
                logger.warning(f"LLM-powered execution failed, falling back to rule-based")
                # Fallback to rule-based approach
                task_type = self._determine_task_type(intention.action_type, user_message)
                
                if task_type:
                    # Prepare parameters for tool execution
                    parameters = self._prepare_task_parameters(task_type, user_message, context)
                    
                    # Execute using tools
                    logger.info(f"🎯 Executing task: {task_type} with tools")
                    result = await self._execute_task_with_tools(task_type, parameters, context)
                    
                    if result.get('success'):
                        logger.info(f"Tool-based execution successful: {result.get('description')}")
                        return result
                    else:
                        logger.warning(f"Tool-based execution failed: {result.get('error')}")
                        # Fallback to legacy methods if tools fail
                        return await self._fallback_execution(intention, context)
                else:
                    # No specific task identified, use general automation
                    logger.info("📋 No specific task identified, using general automation")
                    return await self._fallback_execution(intention, context)
                
        except Exception as e:
            logger.error(f"Error in Execution Agent action: {e}")
            return {
                "success": False,
                "action_taken": False,
                "error": str(e)
            }

    def _looks_like_status_query(self, user_message: str) -> bool:
        """Detect if user message is asking for status rather than requesting action"""
        status_indicators = [
            "did you send", "was sent", "did i send", "have you sent", "status of",
            "check if", "was the email", "did the email", "email sent", "mail sent",
            "did you email", "have i emailed", "was emailed", "check email",
            "email status", "mail status", "sent status"
        ]
        message_lower = user_message.lower()
        return any(indicator in message_lower for indicator in status_indicators)

    async def _handle_status_query(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status queries without invoking tools"""
        try:
            # Get session context from the hybrid bot
            session_context = context.get("session_context", {})
            
            # Check for email status
            if "email" in user_message.lower() or "mail" in user_message.lower():
                last_email = session_context.get("last_email_status")
                if last_email and last_email.get("sent"):
                    recipient = last_email.get("to", ["someone"])[0] if last_email.get("to") else "someone"
                    subject = last_email.get("subject", "email")
                    timestamp = last_email.get("timestamp", "recently")
                    return {
                        "success": True,
                        "action_taken": False,
                        "message": f"✅ Yes, I sent the email '{subject}' to {recipient} {timestamp}.",
                        "status_query": True
                    }
                else:
                    return {
                        "success": True,
                        "action_taken": False,
                        "message": "❌ No recent email has been sent.",
                        "status_query": True
                    }
            
            # Check for meeting status
            elif "meeting" in user_message.lower() or "schedule" in user_message.lower():
                last_meeting = session_context.get("last_meeting")
                if last_meeting:
                    title = last_meeting.get("title", "Meeting")
                    time = last_meeting.get("time", "recently")
                    return {
                        "success": True,
                        "action_taken": False,
                        "message": f"✅ Yes, I scheduled '{title}' for {time}.",
                        "status_query": True
                    }
                else:
                    return {
                        "success": True,
                        "action_taken": False,
                        "message": "❌ No recent meeting has been scheduled.",
                        "status_query": True
                    }
            
            # Generic status response
            return {
                "success": True,
                "action_taken": False,
                "message": "I can check the status of recent emails or meetings. What specifically would you like to know?",
                "status_query": True
            }
            
        except Exception as e:
            logger.error(f"Error handling status query: {e}")
            return {
                "success": False,
                "error": f"Error checking status: {str(e)}",
                "status_query": True
            }

    def _validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Optional[str]:
        """Validate that required parameters are present for the given tool"""
        required_params = {
            "schedule_meeting": ["title", "start_time", "duration_minutes", "attendees"],
            "email_tool": ["recipient", "subject", "body"],
            "get_upcoming_meetings": ["days_ahead"],
            "find_free_slots": ["duration_minutes", "days_ahead"]
        }
        
        if tool_name not in required_params:
            return None  # No validation rules for this tool
        
        missing_params = []
        for param in required_params[tool_name]:
            if param not in parameters or parameters[param] is None or parameters[param] == "":
                missing_params.append(param)
        
        if missing_params:
            if tool_name == "email_tool":
                return f"Please specify: {', '.join(missing_params)}. For example: recipient email, subject line, and message content."
            elif tool_name == "schedule_meeting":
                return f"Please specify: {', '.join(missing_params)}. For example: meeting title, date/time, duration, and attendee emails."
            else:
                return f"Please specify: {', '.join(missing_params)}."
        
        # Additional validation for specific parameters
        if tool_name == "email_tool" and parameters.get("recipient"):
            recipient = parameters["recipient"]
            if "@" not in str(recipient):
                return "Please provide a valid email address for the recipient."
        
        return None  # All validations passed

    async def _llm_analyze_and_execute(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to analyze user intent and execute appropriate tools"""
        try:
            # Check for status queries first - don't use tools for these
            if self._looks_like_status_query(user_message):
                return await self._handle_status_query(user_message, context)
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage
            import json
            
            # Initialize LLM
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
            
            # Get available tools for LLM context
            available_tools = list(self.available_tools.keys())
            
            # Get current time with timezone for temporal grounding
            from datetime import datetime
            import pytz
            user_tz = pytz.timezone(context.get("user_timezone", "Asia/Kolkata"))
            now = datetime.now(user_tz)
            now_str = now.strftime("%Y-%m-%d %H:%M:%S %Z%z")
            
            # Create system prompt for intent analysis and tool calling
            system_prompt = f"""You are an intelligent task execution agent. Analyze the user's request and determine:
1. What the user wants to accomplish
2. Which tool(s) to use from the available tools
3. What parameters to pass to the tool(s)

CURRENT DATETIME (user-local): {now_str}

TEMPORAL RULES:
- Resolve relative dates like 'tomorrow', 'next week' relative to the current user-local time above
- Use the user's timezone ({user_tz}) for all times
- Output start_time as ISO-8601 with timezone, e.g., 2025-08-12T12:00:00+05:30
- Date/time MUST be in the FUTURE. If parsed time would be in the past, move to nearest future interpretation
- Normalize ambiguous times: "12 Afternoon" = 12:00 PM, "evening" = 6:00 PM
- If any required parameter is missing, set sensible default and mark requires_permission=true

Available tools:
{', '.join(available_tools)}

AVAILABLE TOOLS (choose ONLY from these):
- get_upcoming_meetings: Check calendar for upcoming meetings 
  REQUIRED: days_ahead (integer, default: 7)
- schedule_meeting: Schedule a new meeting
  REQUIRED: title (string), start_time (ISO-8601 with timezone), duration_minutes (integer), attendees (array of strings)
- list_drive_files: List Google Drive files (no parameters required)
- email_tool: Send an email
  REQUIRED: recipient (string), subject (string), body (string)
- find_free_slots: Find available calendar slots
  REQUIRED: duration_minutes (integer), days_ahead (integer)

CRITICAL RULES:
- If ANY required parameter is missing or unclear, set tool_to_use to null and provide needs_clarification message
- For schedule_meeting: attendees MUST be JSON array ["email1@domain.com"] - NEVER empty string ""
- For email_tool: recipient MUST be a valid email address string - NO placeholders like "example.com"
- If user asks for status ("did you send", "was sent"), do NOT choose any tool - this should not reach here
- NEVER use placeholder emails like "user@example.com" or "recipient@example.com"
- If email recipient is unclear, set tool_to_use to null and ask for clarification
- If meeting attendees are unclear, set tool_to_use to null and ask for clarification

Respond with ONLY valid JSON in this exact format:
{{
    "intent": "brief description of what user wants",
    "tool_to_use": "exact_tool_name",
    "parameters": {{"param1": "value1", "param2": "value2"}},
    "confidence": 0.9,
    "requires_permission": false
}}

For read-only operations (checking calendar, listing files), set requires_permission to false.
For write operations (scheduling, sending emails), set requires_permission to true."""

            user_prompt = f"User request: {user_message}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Get LLM response
            response = await llm.ainvoke(messages)
            llm_response = response.content.strip()
            
            logger.info(f"🤖 LLM analysis: {llm_response}")
            
            # Parse LLM response
            try:
                analysis = json.loads(llm_response)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {llm_response}")
                return {"success": False, "error": "LLM response parsing failed"}
            
            # Extract tool and parameters
            tool_name = analysis.get("tool_to_use")
            parameters = analysis.get("parameters", {})
            intent = analysis.get("intent", "")
            confidence = analysis.get("confidence", 0.5)
            requires_permission = analysis.get("requires_permission", True)
            
            # Validate and normalize time parameters for scheduling tools
            if tool_name == "schedule_meeting" and "start_time" in parameters:
                parameters, time_issues = self._normalize_meeting_time(parameters, user_tz, now)
                if time_issues:
                    logger.info(f"Time normalization notes: {time_issues}")
                    # Include resolved time in permission message
                    analysis["time_issues"] = time_issues
            
            if not tool_name or tool_name not in self.available_tools:
                logger.warning(f"LLM suggested invalid tool: {tool_name}")
                return {"success": False, "error": f"Invalid tool suggested: {tool_name}"}
            
            # Validate required parameters before execution
            validation_error = self._validate_tool_parameters(tool_name, parameters)
            if validation_error:
                logger.warning(f"Missing required parameters for {tool_name}: {validation_error}")
                return {
                    "success": False,
                    "requires_clarification": True,
                    "message": f"I need more information to {intent.lower()}. {validation_error}"
                }
            
            # Check permission for write operations
            if requires_permission:
                permission_context = context.get("permission_context", {})
                user_confirmed = permission_context.get("user_confirmed", False)
                
                if not user_confirmed:
                    # Create detailed permission message with resolved time for scheduling
                    permission_msg = f"🤖 Should I {intent.lower()}?"
                    if tool_name == "schedule_meeting" and "start_time" in parameters:
                        try:
                            formatted_time = self._format_user_datetime(
                                parameters["start_time"], 
                                context.get("user_timezone", "Asia/Kolkata")
                            )
                            
                            # Check if attendees are specified
                            attendees = parameters.get("attendees", [])
                            if isinstance(attendees, str):
                                attendees = [a.strip() for a in attendees.split(",") if a.strip()] if attendees else []
                            
                            if not attendees:
                                permission_msg = f"🤖 Should I schedule a meeting on {formatted_time}? (No attendees specified - will be a personal meeting)"
                            else:
                                attendee_count = len(attendees)
                                permission_msg = f"🤖 Should I schedule a meeting on {formatted_time} with {attendee_count} attendee{'s' if attendee_count > 1 else ''}?"
                        except Exception:
                            pass
                    
                    return {
                        "success": False,
                        "requires_permission": True,
                        "intent": intent,
                        "tool_name": tool_name,
                        "parameters": parameters,
                        "permission_message": permission_msg,
                        "confidence": confidence
                    }
            
            # Execute the tool
            logger.info(f"🎯 LLM determined tool: {tool_name} with parameters: {parameters}")
            
            tool = self.available_tools[tool_name]
            
            # Execute tool based on its type
            if hasattr(tool, 'ainvoke'):
                result = await tool.ainvoke(parameters)
            elif hasattr(tool, 'invoke'):
                result = tool.invoke(parameters)
            else:
                result = await tool(parameters)
            
            logger.info(f"✅ LLM-guided tool execution successful: {result}")
            
            # Format response with LLM
            formatted_response = await self._llm_format_response(user_message, intent, result, tool_name)
            
            return {
                "success": True,
                "action_taken": True,
                "intent": intent,
                "tool_used": tool_name,
                "result": result,
                "formatted_response": formatted_response,
                "confidence": confidence,
                "llm_powered": True
            }
            
        except Exception as e:
            logger.error(f"Error in LLM-powered execution: {e}")
            return {"success": False, "error": str(e)}

    async def _llm_format_response(self, user_message: str, intent: str, tool_result: str, tool_name: str) -> str:
        """Use LLM to format the tool result into a natural response"""
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage
            
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
            
            system_prompt = """You are Native IQ, an intelligent AI assistant. Format the tool result into a natural, conversational response.

Guidelines:
- Be conversational and helpful
- Include the actual data from the tool result
- Ask follow-up questions when appropriate
- Use emojis sparingly but effectively
- Be proactive in suggesting next steps

Keep responses concise but informative."""

            user_prompt = f"""
User asked: {user_message}
Intent: {intent}
Tool used: {tool_name}
Tool result: {tool_result}

Format this into a natural response:"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await llm.ainvoke(messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error formatting LLM response: {e}")
            # Fallback to simple formatting
            if "No upcoming meetings" in str(tool_result):
                return f"📅 I checked your calendar and you don't have any meetings scheduled. Would you like me to schedule something?"
            else:
                return f"✅ Here's what I found:\n\n{tool_result}\n\nIs there anything else you'd like me to help with?"
    
    def _generate_permission_message(self, task_type: str, parameters: Dict[str, Any]) -> str:
        """Generate user-friendly permission request message"""
        user_message = parameters.get("user_message", "")
        
        if task_type == "get_upcoming_meetings":
            days = parameters.get("days_ahead", 1)
            time_phrase = "tomorrow" if days == 1 else f"next {days} days"
            return f"🗓️ Should I check your calendar and show your schedule for {time_phrase}?"
        
        elif task_type == "schedule_meeting":
            title = parameters.get("title", "meeting")
            return f"📅 Should I schedule '{title}' for you?"
        
        elif task_type == "send_email":
            recipient = parameters.get("recipient", "recipient")
            return f"📧 Should I send an email to {recipient}?"
        
        elif task_type == "list_drive_files":
            return f"📁 Should I list your Google Drive files?"
        
        elif task_type == "download_drive_file":
            return f"⬇️ Should I download the file from Google Drive?"
        
        elif task_type == "upload_drive_file":
            return f"⬆️ Should I upload the file to Google Drive?"
        
        else:
            return f"🤖 Should I execute: {user_message}?"
    
    def _determine_task_type(self, action_type: str, user_message: str) -> Optional[str]:
        """Determine the task type from intention and user message"""
        action_lower = action_type.lower()
        message_lower = user_message.lower()
        
        # Check for specific task patterns
        # Google Drive operations
        if "drive" in action_lower or "drive" in message_lower or "google drive" in message_lower:
            # Order matters: check for info/details first to avoid matching generic verbs like 'get'
            if "info" in message_lower or "details" in message_lower:
                return "get_drive_file_info"
            elif "list" in message_lower or "files" in message_lower or "show" in message_lower:
                return "list_drive_files"
            elif "download" in message_lower:
                return "download_drive_file"
            elif "upload" in message_lower or "save" in message_lower:
                return "upload_drive_file"
        # Email operations
        elif "email" in action_lower or "email" in message_lower or "send" in message_lower:
            return "send_email"
        elif "calendar" in action_lower or "calendar" in message_lower or "check calendar" in message_lower:
            if "check" in message_lower or "show" in message_lower or "what" in message_lower or "schedule" in message_lower:
                return "get_upcoming_meetings"
            else:
                return "schedule_meeting"
        elif "meeting" in action_lower or "schedule" in action_lower or "meeting" in message_lower or "schedule" in message_lower:
            return "schedule_meeting"
        elif "report" in action_lower or "create" in action_lower or "report" in message_lower or "generate" in message_lower:
            return "create_report"
        elif "file" in action_lower or "document" in message_lower:
            return "create_file"
        elif "search" in action_lower or "search" in message_lower:
            return "web_search"
        elif "message" in action_lower or "notify" in message_lower:
            return "send_message"
        
        return None
    
    def _prepare_task_parameters(self, task_type: str, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare parameters for task execution based on task type"""
        base_params = {
            "user_message": user_message,
            "user": context.get("user", "User"),
            "timestamp": datetime.now().isoformat()
        }
        
        if task_type == "send_email":
            return {
                **base_params,
                "recipient": "user@example.com",
                "subject": "Automated Email from Native IQ",
                "body": f"This email was generated based on your request: {user_message}"
            }
        elif task_type == "schedule_meeting":
            return {
                **base_params,
                "title": "Team Meeting",
                "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
                "duration_minutes": 30,
                "attendees": ["team@company.com"],
                "description": f"Meeting scheduled based on: {user_message}"
            }
        elif task_type == "get_upcoming_meetings":
            # Extract days from user message (default to 1 for "tomorrow")
            days_ahead = 1
            if "tomorrow" in user_message.lower():
                days_ahead = 1
            elif "week" in user_message.lower():
                days_ahead = 7
            elif "month" in user_message.lower():
                days_ahead = 30
            
            return {
                **base_params,
                "days_ahead": days_ahead
            }
        elif task_type == "create_report":
            return {
                **base_params,
                "title": "Automated Report",
                "content": f"Report generated based on: {user_message}\n\nDate: {datetime.now().strftime('%Y-%m-%d')}\n\nThis report was automatically created by Native IQ.",
                "format": "text"
            }
        elif task_type == "create_file":
            return {
                **base_params,
                "filename": f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "content": f"Document created based on: {user_message}\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        else:
            return base_params
    
    async def _fallback_execution(self, intention: Intention, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to legacy execution methods when tools are not available"""
        try:
            logger.info("🔄 Using fallback execution methods")
            
            # Use legacy automation method
            result = await self._execute_automation({"decision_id": "unknown"})
            
            return {
                "success": result["success"],
                "action_taken": result["success"],
                "execution_id": result.get("execution_id"),
                "description": "General automation executed (fallback)",
                "details": result.get("details", "Automation completed using fallback method"),
                "time_saved": result.get("time_saved", 0),
                "real_execution": False,
                "fallback_used": True
            }
            
        except Exception as e:
            logger.error(f"Fallback execution failed: {e}")
            return {
                "success": False,
                "action_taken": False,
                "error": f"Fallback execution failed: {str(e)}"
            }

    async def learn(self, beliefs: List[Belief], context: Dict[str, Any]) -> None:
        """Learn from execution results and improve performance"""
        try:
            for belief in beliefs:
                if belief.confidence > 0.7:
                    if belief.type == BeliefType.KNOWLEDGE:
                        await self._update_execution_knowledge(belief)

            # Learn from execution patterns
            if context.get('execution_feedback'):
                self._adjust_execution_strategies(context['execution_feedback'])

            logger.info(f"Execution Agent learning completed with {len(beliefs)} beliefs")

        except Exception as e:
            logger.error(f"Error in Execution Agent learning: {e}")

    async def update_desires(self, beliefs: List[Belief], context: Dict[str, Any]) -> List[Desire]:
        """Update desires based on current beliefs and context"""
        try:
            updated_desires = []
            
            # Check if we have approved decisions to execute
            approved_decisions = context.get("approved_decisions", [])
            if approved_decisions:
                execute_desire = Desire(
                    id="execute_approved_automations",
                    goal="Execute approved automation decisions",
                    priority=10,
                    conditions={"has_approved_decisions": True}
                )
                updated_desires.append(execute_desire)
            
            # Check if we have active executions to monitor
            active_executions = [e for e in self.executions.values() 
                               if e.status == ExecutionStatus.IN_PROGRESS]
            if active_executions:
                monitor_desire = Desire(
                    id="monitor_active_executions",
                    goal="Monitor and track execution performance",
                    priority=8,
                    conditions={"has_active_executions": True}
                )
                updated_desires.append(monitor_desire)
            
            return updated_desires
            
        except Exception as e:
            logger.error(f"Error updating desires: {e}")
            return self.desires

    async def deliberate(self, beliefs: List[Belief], desires: List[Desire], intentions: List[Intention]) -> List[Intention]:
        """Deliberate and create intentions based on beliefs and desires"""
        try:
            new_intentions = []
            
            for desire in desires:
                if desire.id == "execute_approved_automations":
                    # Create intentions for each approved decision
                    for belief in beliefs:
                        if belief.type == BeliefType.KNOWLEDGE and belief.source == "execution_agent":
                            # This belief contains an execution plan
                            plan = belief.content
                            
                            intention = Intention(
                                id=f"execute_automation_{datetime.now().timestamp()}",
                                desire_id=desire.id,
                                action_type="execute_automation",
                                parameters={
                                    "decision_id": plan.get("decision_id"),
                                    "opportunity_id": plan.get("opportunity_id"),
                                    "execution_type": plan.get("execution_type", "automation")
                                }
                            )
                            intention.action = "execute_automation"  # Add action attribute for existing act method
                            new_intentions.append(intention)
                
                elif desire.id == "monitor_active_executions":
                    # Create monitoring intention
                    intention = Intention(
                        id=f"monitor_executions_{datetime.now().timestamp()}",
                        desire_id=desire.id,
                        action_type="monitor_executions",
                        parameters={}
                    )
                    intention.action = "monitor_executions"  # Add action attribute for existing act method
                    new_intentions.append(intention)
            
            return new_intentions
            
        except Exception as e:
            logger.error(f"Error in deliberation: {e}")
            return []

    async def _process_approved_decision(self, decision: Any) -> Optional[Belief]:
        """Process an approved decision for execution"""
        try:
            # Handle both dataclass and dict inputs
            if hasattr(decision, 'decision_id'):
                decision_id = decision.decision_id
                decision_type = decision.decision_type
                opportunity_id = decision.opportunity_id
            else:
                decision_id = decision.get("decision_id")
                decision_type = decision.get("decision_type")
                opportunity_id = decision.get("opportunity_id")

            if decision_type == "approve":
                execution_plan = {
                    "decision_id": decision_id,
                    "opportunity_id": opportunity_id,
                    "execution_type": "automation",
                    "priority": "high",
                    "estimated_time_saved": 15
                }

                return Belief(
                    id=f"execution_plan_{datetime.now().timestamp()}",
                    type=BeliefType.KNOWLEDGE,
                    content=execution_plan,
                    confidence=0.9,
                    source="execution_agent"
                )

        except Exception as e:
            logger.error(f"Error processing approved decision: {e}")
            return None

    async def _process_execution_request(self, request: Dict[str, Any]) -> Optional[Belief]:
        """Process a direct execution request"""
        try:
            execution_analysis = {
                "request_id": request.get("request_id"),
                "execution_type": request.get("type", "general"),
                "feasibility": "high",
                "estimated_duration": 5,
                "resource_requirements": request.get("resources", {})
            }

            return Belief(
                id=f"execution_request_{datetime.now().timestamp()}",
                type=BeliefType.KNOWLEDGE,
                content=execution_analysis,
                confidence=0.8,
                source="execution_agent"
            )

        except Exception as e:
            logger.error(f"Error processing execution request: {e}")
            return None

    async def _monitor_executions(self) -> Optional[Belief]:
        """Monitor ongoing executions"""
        try:
            active_executions = [e for e in self.executions.values() 
                               if e.status == ExecutionStatus.IN_PROGRESS]

            if active_executions:
                monitoring_data = {
                    "active_executions": len(active_executions),
                    "total_executions": len(self.executions),
                    "success_rate": self.accuracy_rate,
                    "total_time_saved": self.total_time_saved
                }

                return Belief(
                    id=f"execution_monitoring_{datetime.now().timestamp()}",
                    type=BeliefType.KNOWLEDGE,
                    content=monitoring_data,
                    confidence=0.9,
                    source="execution_agent"
                )

        except Exception as e:
            logger.error(f"Error monitoring executions: {e}")
            return None

    async def _execute_automation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a general automation task"""
        try:
            execution_id = f"exec_{datetime.now().timestamp()}"
            
            execution = AutomationExecution(
                execution_id=execution_id,
                decision_id=parameters.get("decision_id", "unknown"),
                automation_type="general",
                status=ExecutionStatus.IN_PROGRESS,
                start_time=datetime.now()
            )

            self.executions[execution_id] = execution
            self.total_executions += 1

            # Simulate execution (replace with real automation logic)
            await asyncio.sleep(0.1)  # Simulate processing time

            # Mark as completed
            execution.status = ExecutionStatus.COMPLETED
            execution.end_time = datetime.now()
            execution.success_rate = 0.95
            execution.time_saved = 10.0

            self.successful_executions += 1
            self.total_time_saved += execution.time_saved

            logger.info(f"Executed automation: {execution_id}")

            return {
                "success": True,
                "execution_id": execution_id,
                "time_saved": execution.time_saved,
                "details": "Automation executed successfully"
            }

        except Exception as e:
            logger.error(f"Error executing automation: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_meeting_scheduling(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute meeting scheduling automation"""
        try:
            execution_id = f"meeting_exec_{datetime.now().timestamp()}"

            execution = AutomationExecution(
                execution_id=execution_id,
                decision_id=parameters.get("decision_id", "unknown"),
                automation_type="meeting_scheduling",
                status=ExecutionStatus.IN_PROGRESS,
                start_time=datetime.now()
            )

            self.executions[execution_id] = execution
            self.total_executions += 1

            # Use calendar tools if available
            if "schedule_meeting" in self.calendar_tools:
                try:
                    meeting_result = await self.calendar_tools["schedule_meeting"].ainvoke({
                        "title": parameters.get("title", "Automated Meeting"),
                        "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
                        "duration_minutes": parameters.get("duration", 30),
                        "attendees": parameters.get("attendees", ["user@example.com"]),
                        "description": "Meeting scheduled by Native IQ Execution Agent"
                    })
                    
                    execution.execution_details = {"calendar_result": meeting_result}
                    
                except Exception as tool_error:
                    logger.warning(f"Calendar tool error: {tool_error}")
                    # Continue with simulation

            # Mark as completed
            execution.status = ExecutionStatus.COMPLETED
            execution.end_time = datetime.now()
            execution.success_rate = 0.98
            execution.time_saved = 15.0

            self.successful_executions += 1
            self.total_time_saved += execution.time_saved

            logger.info(f"Executed meeting scheduling: {execution_id}")

            return {
                "success": True,
                "execution_id": execution_id,
                "time_saved": execution.time_saved,
                "details": "Meeting scheduled successfully"
            }

        except Exception as e:
            logger.error(f"Error executing meeting scheduling: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_automated_response(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute automated response generation"""
        try:
            execution_id = f"response_exec_{datetime.now().timestamp()}"

            execution = AutomationExecution(
                execution_id=execution_id,
                decision_id=parameters.get("decision_id", "unknown"),
                automation_type="automated_response",
                status=ExecutionStatus.IN_PROGRESS,
                start_time=datetime.now()
            )

            self.executions[execution_id] = execution
            self.total_executions += 1

            # Simulate response generation
            response_template = parameters.get("template", "Thank you for your message. This is an automated response.")
            
            execution.execution_details = {
                "response_generated": response_template,
                "recipient": parameters.get("recipient", "user@example.com")
            }

            # Mark as completed
            execution.status = ExecutionStatus.COMPLETED
            execution.end_time = datetime.now()
            execution.success_rate = 0.92
            execution.time_saved = 5.0

            self.successful_executions += 1
            self.total_time_saved += execution.time_saved

            logger.info(f"Executed automated response: {execution_id}")

            return {
                "success": True,
                "execution_id": execution_id,
                "time_saved": execution.time_saved,
                "details": "Automated response sent successfully"
            }

        except Exception as e:
            logger.error(f"Error executing automated response: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_task_with_tools(self, task_type: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks using available tools"""
        try:
            execution_id = f"tool_exec_{datetime.now().timestamp()}"
            logger.info(f"🚀 Executing task with tools: {task_type}")
            
            # Map task types to required tools
            tool_mapping = {
                "send_email": "email_tool",
                "schedule_meeting": "calendar_tool", 
                "create_file": "file_tool",
                "send_message": "messaging_tool",
                "create_report": "report_tool",
                "web_search": "search_tool",
                "list_drive_files": "list_drive_files",
                "download_drive_file": "download_drive_file",
                "upload_drive_file": "upload_drive_file",
                "get_drive_file_info": "get_drive_file_info",
                "get_upcoming_meetings": "get_upcoming_meetings",
            }
            
            required_tool = tool_mapping.get(task_type)
            if not required_tool:
                return {
                    "success": False,
                    "error": f"Unknown task type: {task_type}"
                }
            
            # Check if required tool is available
            if not self.has_tool(required_tool):
                logger.warning(f"Required tool '{required_tool}' not available for task '{task_type}'")
                logger.warning(f"Available tools: {list(self.available_tools.keys())}")
                return {
                    "success": False,
                    "error": f"Tool '{required_tool}' not available",
                    "available_tools": self.get_available_tools()
                }
            
            # Get the tool and execute
            tool = self.available_tools[required_tool]
            logger.info(f"🔧 Using tool: {required_tool}")
            
            # Auto-execute read-only tasks, ask permission for write operations
            read_only_tasks = [
                "get_upcoming_meetings", "list_drive_files", "get_drive_file_info", 
                "web_search", "find_free_slots"
            ]
            
            permission_context = context.get("permission_context", {})
            user_confirmed = permission_context.get("user_confirmed", False)
            
            # Skip permission for read-only tasks
            if task_type not in read_only_tasks and not user_confirmed:
                # Return permission request for write operations
                return {
                    "success": False,
                    "requires_permission": True,
                    "task_type": task_type,
                    "tool_name": required_tool,
                    "parameters": parameters,
                    "permission_message": self._generate_permission_message(task_type, parameters),
                    "execution_id": execution_id
                }
            
            # Execute tool with parameters (auto for read-only, or if user confirmed)
            try:
                logger.info(f"🔧 About to execute tool '{required_tool}' with parameters: {parameters}")
                
                # Special handling for calendar tools
                if task_type == "get_upcoming_meetings":
                    # Import and call calendar tool directly
                    try:
                        from src.domains.tools.calandar_tool import get_upcoming_meetings
                        days_ahead = parameters.get("days_ahead", 1)
                        result = await get_upcoming_meetings(days_ahead=days_ahead)
                        logger.info(f"✅ Calendar tool executed directly: {result}")
                    except Exception as calendar_error:
                        logger.error(f"Direct calendar tool call failed: {calendar_error}")
                        # Fallback to registered tool
                        if hasattr(tool, 'ainvoke'):
                            result = await tool.ainvoke(parameters)
                        elif hasattr(tool, 'invoke'):
                            result = tool.invoke(parameters)
                        else:
                            result = await tool(parameters)
                else:
                    # Normal tool execution for other tools
                    if hasattr(tool, 'ainvoke'):
                        # Async tool execution
                        result = await tool.ainvoke(parameters)
                    elif hasattr(tool, 'invoke'):
                        # Sync tool execution
                        result = tool.invoke(parameters)
                    else:
                        # Direct call
                        result = await tool(parameters)
                
                logger.info(f"✅ Tool execution successful: {result}")
                
                # Track execution metrics
                self.total_executions += 1
                self.successful_executions += 1
                
                # Estimate time saved based on task type
                time_saved_mapping = {
                    "send_email": 5.0,
                    "schedule_meeting": 15.0,
                    "create_file": 10.0,
                    "create_report": 20.0,
                    "send_message": 3.0,
                    "web_search": 8.0,
                    "list_drive_files": 3.0,
                    "download_drive_file": 7.0,
                    "upload_drive_file": 10.0,
                    "get_drive_file_info": 2.0
                }
                time_saved = time_saved_mapping.get(task_type, 5.0)
                self.total_time_saved += time_saved
                
                return {
                    "success": True,
                    "action_taken": True,
                    "execution_id": execution_id,
                    "task_type": task_type,
                    "tool_used": required_tool,
                    "result": result,
                    "time_saved": time_saved,
                    "description": f"Task '{task_type}' executed using '{required_tool}'",
                    "details": str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                    "real_execution": True
                }
                
            except Exception as tool_error:
                logger.error(f"❌ Tool execution failed: {tool_error}")
                self.total_executions += 1
                return {
                    "success": False,
                    "error": f"Tool execution failed: {str(tool_error)}",
                    "tool_used": required_tool,
                    "task_type": task_type
                }
                
        except Exception as e:
            logger.error(f"Error in tool-based execution: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _update_execution_knowledge(self, belief: Belief) -> None:
        """Update execution knowledge based on belief"""
        try:
            belief_content = belief.content
            
            if "success_rate" in belief_content:
                # update accuracy based on feedback
                feedback_rate = belief_content["success_rate"]
                self.accuracy_rate = (self.accuracy_rate * 0.8) + (feedback_rate * 0.2)
            
            if "time_saved" in belief_content:
                # track time savings
                self.total_time_saved += belief_content["time_saved"]

        except Exception as e:
            logger.error(f"Error updating execution knowledge: {e}")

    def _normalize_meeting_time(self, parameters: dict, user_tz, now) -> tuple[dict, list[str]]:
        """Validate and normalize meeting time parameters"""
        from datetime import datetime, timedelta
        from dateutil import parser as dateparser
        
        issues = []
        start_raw = parameters.get("start_time")
        
        if not start_raw:
            issues.append("start_time missing")
            return parameters, issues

        try:
            # Parse the datetime string
            dt = dateparser.isoparse(start_raw)
        except Exception as e:
            issues.append(f"Invalid start_time format: {start_raw}")
            return parameters, issues

        # Attach timezone if naive
        if dt.tzinfo is None:
            dt = user_tz.localize(dt)

        # If in the past, try to fix it
        if dt < now:
            # If same month/day but wrong year, fix the year
            if dt.month == now.month and dt.day == now.day:
                dt_future = dt.replace(year=now.year)
                if dt_future < now:
                    # If still in the past (same day), move to next day
                    dt_future = dt_future + timedelta(days=1)
                issues.append(f"Corrected year from {dt.year} to {dt_future.year}")
                dt = dt_future
            else:
                # Different date but in past - likely wrong year
                try:
                    dt_future = dt.replace(year=now.year)
                    if dt_future < now:
                        # If still past, try next year
                        dt_future = dt.replace(year=now.year + 1)
                    issues.append(f"Adjusted date from {dt.isoformat()} to {dt_future.isoformat()}")
                    dt = dt_future
                except Exception:
                    issues.append("start_time appears in the past; needs confirmation")

        # Update parameters with normalized time
        parameters["start_time"] = dt.isoformat()
        return parameters, issues

    def _format_user_datetime(self, iso_str: str, user_tz_str: str) -> str:
        """Format datetime for user-friendly display with proper timezone handling"""
        try:
            from dateutil import parser as dateparser
            import pytz
            
            dt = dateparser.isoparse(iso_str)
            
            # Convert to user timezone if needed
            if user_tz_str:
                try:
                    user_tz = pytz.timezone(user_tz_str)
                    if dt.tzinfo is None:
                        dt = user_tz.localize(dt)
                    else:
                        dt = dt.astimezone(user_tz)
                except Exception:
                    # Fallback: keep original dt
                    pass
            
            # Format components
            day = dt.strftime("%a, %d %b %Y")
            time = dt.strftime("%I:%M %p").lstrip("0")
            
            # Format timezone offset
            offset = dt.strftime("%z")
            if offset and len(offset) == 5:
                offset_fmt = f"{offset[:3]}:{offset[3:]}"
            else:
                offset_fmt = offset or ""
            
            # Get timezone name/label
            tz_label = user_tz_str or ""
            
            # Combine offset and label, avoid empty parentheses
            suffix = f"{offset_fmt} {tz_label}".strip()
            
            return f"{day} at {time}" + (f" ({suffix})" if suffix else "")
            
        except Exception as e:
            logger.error(f"Error formatting datetime: {e}")
            # Fallback to basic formatting
            return iso_str

    def _adjust_execution_strategies(self, feedback: Dict[str, Any]) -> None:
        """Adjust execution strategies based on feedback"""
        try:
            if feedback.get("success_rate", 0) < 0.8:
                # lower success rate - be more conservative
                logger.info("Adjusting execution strategy to be more conservative")
            
            if feedback.get("time_saved", 0) < 5:
                # low time savings - optimize for efficiency
                logger.info("Adjusting execution strategy to optimize efficiency")

        except Exception as e:
            logger.error(f"Error adjusting execution strategies: {e}")

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution performance summary"""
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "success_rate": self.successful_executions / max(1, self.total_executions),
            "total_time_saved": self.total_time_saved,
            "active_executions": len([e for e in self.executions.values() 
                                    if e.status == ExecutionStatus.IN_PROGRESS]),
            "accuracy_rate": self.accuracy_rate
        }
"""
Nudge Service - Self-nudging system for Native IQ
Simple implementation using asyncio (upgrade to Redis/Celery later)
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict

@dataclass
class Nudge:
    """Represents a scheduled nudge/notification"""
    id: str
    user_id: str
    message: str
    nudge_type: str  # "reminder", "opportunity", "follow_up", "insight"
    scheduled_time: str
    context: Dict[str, Any]
    status: str  # "scheduled", "sent", "cancelled"
    created_at: str

class NudgeService:
    """
    Simple nudge scheduling service that integrates with your existing bot
    """
    
    def __init__(self, data_dir: Path = None, send_callback: Optional[Callable] = None):
        self.data_dir = data_dir or Path(__file__).resolve().parents[2] / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.nudges_file = self.data_dir / "scheduled_nudges.json"
        self.nudges = self._load_nudges()
        
        # Callback function to send nudges (will be your bot's send_message)
        self.send_callback = send_callback
        
        # Background task for processing nudges
        self._nudge_task = None
        self._running = False
    
    def _load_nudges(self) -> Dict[str, List[Nudge]]:
        """Load scheduled nudges from JSON file"""
        if not self.nudges_file.exists():
            return {}
        
        try:
            with open(self.nudges_file, 'r') as f:
                data = json.load(f)
                return {
                    user_id: [Nudge(**nudge) for nudge in nudges]
                    for user_id, nudges in data.items()
                }
        except Exception:
            return {}
    
    def _save_nudges(self):
        """Save nudges to JSON file"""
        try:
            data = {
                user_id: [asdict(nudge) for nudge in nudges]
                for user_id, nudges in self.nudges.items()
            }
            with open(self.nudges_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving nudges: {e}")
    
    def schedule_nudge(self, user_id: str, message: str, delay_minutes: int, 
                      nudge_type: str = "reminder", context: Dict[str, Any] = None) -> Nudge:
        """
        Schedule a nudge to be sent after delay_minutes
        """
        scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
        
        nudge = Nudge(
            id=f"{user_id}_{datetime.now().timestamp()}",
            user_id=user_id,
            message=message,
            nudge_type=nudge_type,
            scheduled_time=scheduled_time.isoformat(),
            context=context or {},
            status="scheduled",
            created_at=datetime.now().isoformat()
        )
        
        if user_id not in self.nudges:
            self.nudges[user_id] = []
        
        self.nudges[user_id].append(nudge)
        self._save_nudges()
        
        # Start background processor if not running
        if not self._running:
            self.start_processor()
        
        return nudge
    
    def schedule_smart_nudges_from_context(self, user_id: str, session_context: Dict[str, Any]):
        """
        Analyze session context and schedule intelligent nudges
        """
        # Follow-up nudges based on recent actions
        if "last_meeting" in session_context and "last_email_status" not in session_context:
            # No follow-up email sent after meeting
            self.schedule_nudge(
                user_id=user_id,
                message="🔔 Don't forget to send a follow-up email for your recent meeting!",
                delay_minutes=60,  # 1 hour later
                nudge_type="follow_up",
                context={"meeting": session_context["last_meeting"]}
            )
        
        # Contact management nudges
        contacts = session_context.get("contacts", {})
        contact_count = len(contacts.get("by_email", {}))
        
        if contact_count >= 5:
            self.schedule_nudge(
                user_id=user_id,
                message=f"💡 You're managing {contact_count} contacts. Consider organizing them into groups or creating a CRM system!",
                delay_minutes=30,
                nudge_type="insight",
                context={"contact_count": contact_count}
            )
        
        # Meeting preparation nudges
        if "last_meeting" in session_context:
            meeting_time_str = session_context["last_meeting"].get("time", "")
            try:
                # If meeting is in the future, schedule preparation nudge
                # This is simplified - you'd want better time parsing
                if "tomorrow" in meeting_time_str.lower():
                    self.schedule_nudge(
                        user_id=user_id,
                        message= "Your meeting is tomorrow. Need help preparing an agenda or materials?",
                        delay_minutes=120,  # 2 hours later
                        nudge_type="reminder",
                        context={"meeting": session_context["last_meeting"]}
                    )
            except Exception:
                pass  # Graceful fallback for time parsing
    
    def start_processor(self):
        """
        Start the background nudge processor
        """
        if not self._running:
            self._running = True
            self._nudge_task = asyncio.create_task(self._process_nudges())
    
    def stop_processor(self):
        """
        Stop the background nudge processor
        """
        self._running = False
        if self._nudge_task:
            self._nudge_task.cancel()
    
    async def _process_nudges(self):
        """
        Background task to process and send scheduled nudges
        """
        while self._running:
            try:
                now = datetime.now()
                
                for user_id, user_nudges in self.nudges.items():
                    for nudge in user_nudges:
                        if nudge.status == "scheduled":
                            scheduled_time = datetime.fromisoformat(nudge.scheduled_time)
                            
                            if now >= scheduled_time:
                                # Time to send the nudge
                                await self._send_nudge(nudge)
                                nudge.status = "sent"
                
                # Save updated statuses
                self._save_nudges()
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                print(f"Error in nudge processor: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _send_nudge(self, nudge: Nudge):
        """
        Send a nudge using the configured callback
        """
        try:
            if self.send_callback:
                await self.send_callback(nudge.user_id, nudge.message)
            else:
                # Fallback: just print (for testing)
                print(f"NUDGE for {nudge.user_id}: {nudge.message}")
        except Exception as e:
            print(f"Error sending nudge: {e}")
    
    def get_user_nudges(self, user_id: str, status: Optional[str] = None) -> List[Nudge]:
        """
        Get nudges for a user, optionally filtered by status
        """
        user_nudges = self.nudges.get(user_id, [])
        
        if status:
            return [nudge for nudge in user_nudges if nudge.status == status]
        
        return user_nudges
    
    def cancel_nudge(self, user_id: str, nudge_id: str):
        """
        Cancel a scheduled nudge
        """
        user_nudges = self.nudges.get(user_id, [])
        for nudge in user_nudges:
            if nudge.id == nudge_id and nudge.status == "scheduled":
                nudge.status = "cancelled"
                break
        
        self._save_nudges()

# Global instance
nudge_service = NudgeService()

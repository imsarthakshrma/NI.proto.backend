
"""
Dashboard Service - Enhanced observation tracking and opportunity detection
Extends your existing session context system for frontend dashboard
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class Opportunity:
    """Represents a business/productivity opportunity identified by Native IQ"""
    id: str
    type: str  # "obvious", "unobvious", "follow_up", "optimization"
    title: str
    description: str
    context: Dict[str, Any]
    priority: str  # "high", "medium", "low"
    status: str  # "identified", "in_progress", "completed", "dismissed"
    created_at: str
    updated_at: str
    user_id: str

@dataclass
class UserInsight:
    """Learning about user patterns and preferences"""
    category: str  # "communication_style", "meeting_patterns", "work_hours", etc.
    insight: str
    confidence: float  # 0.0 to 1.0
    evidence: List[str]
    created_at: str

class DashboardService:
    """
    Enhanced dashboard service that builds on your existing session context
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path(__file__).resolve().parents[2] / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Files for persistent storage (upgrade to Redis/DynamoDB later)
        self.opportunities_file = self.data_dir / "opportunities.json"
        self.insights_file = self.data_dir / "user_insights.json"
        
        # Load existing data
        self.opportunities = self._load_opportunities()
        self.insights = self._load_insights()
    
    def _load_opportunities(self) -> Dict[str, List[Opportunity]]:
        """Load opportunities from JSON file"""
        if not self.opportunities_file.exists():
            return {}
        
        try:
            with open(self.opportunities_file, 'r') as f:
                data = json.load(f)
                return {
                    user_id: [Opportunity(**opp) for opp in opps]
                    for user_id, opps in data.items()
                }
        except Exception:
            return {}
    
    def _save_opportunities(self):
        """Save opportunities to JSON file"""
        try:
            data = {
                user_id: [asdict(opp) for opp in opps]
                for user_id, opps in self.opportunities.items()
            }
            with open(self.opportunities_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving opportunities: {e}")
    
    def _load_insights(self) -> Dict[str, List[UserInsight]]:
        """Load user insights from JSON file"""
        if not self.insights_file.exists():
            return {}
        
        try:
            with open(self.insights_file, 'r') as f:
                data = json.load(f)
                return {
                    user_id: [UserInsight(**insight) for insight in insights]
                    for user_id, insights in data.items()
                }
        except Exception:
            return {}
    
    def _save_insights(self):
        """Save insights to JSON file"""
        try:
            data = {
                user_id: [asdict(insight) for insight in insights]
                for user_id, insights in self.insights.items()
            }
            with open(self.insights_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving insights: {e}")
    
    def log_opportunity(self, user_id: str, opportunity_type: str, title: str, 
                       description: str, context: Dict[str, Any], priority: str = "medium"):
        """
        Log a new opportunity identified by Native IQ
        """
        opportunity = Opportunity(
            id=f"{user_id}_{datetime.now().timestamp()}",
            type=opportunity_type,
            title=title,
            description=description,
            context=context,
            priority=priority,
            status="identified",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            user_id=user_id
        )
        
        if user_id not in self.opportunities:
            self.opportunities[user_id] = []
        
        self.opportunities[user_id].append(opportunity)
        self._save_opportunities()
        
        return opportunity
    
    def analyze_session_for_opportunities(self, user_id: str, session_context: Dict[str, Any]) -> List[Opportunity]:
        """
        Analyze session context to identify opportunities
        This extends your existing contact persistence and session tracking
        """
        opportunities = []
        now = datetime.now().isoformat()
        
        # Obvious opportunities
        if "last_meeting" in session_context and "last_email_status" not in session_context:
            opportunities.append(self.log_opportunity(
                user_id=user_id,
                opportunity_type="obvious",
                title="Send meeting follow-up email",
                description=f"Meeting '{session_context['last_meeting'].get('title', 'Untitled')}' was scheduled but no follow-up email was sent",
                context={"meeting_data": session_context["last_meeting"]},
                priority="high"
            ))
        
        # Unobvious opportunities - pattern detection
        contacts = session_context.get("contacts", {})
        if len(contacts.get("by_email", {})) > 3:
            opportunities.append(self.log_opportunity(
                user_id=user_id,
                opportunity_type="unobvious",
                title="Create contact groups",
                description="You're managing multiple contacts - consider organizing them into groups or projects",
                context={"contact_count": len(contacts.get("by_email", {}))},
                priority="medium"
            ))
        
        # Meeting pattern analysis
        if "last_meeting" in session_context:
            meeting_time = session_context["last_meeting"].get("time", "")
            if "afternoon" in meeting_time.lower() or "PM" in meeting_time:
                self.log_insight(
                    user_id=user_id,
                    category="meeting_patterns",
                    insight="Prefers afternoon meetings",
                    confidence=0.7,
                    evidence=[f"Scheduled meeting at {meeting_time}"]
                )
        
        return opportunities
    
    def log_insight(self, user_id: str, category: str, insight: str, 
                   confidence: float, evidence: List[str]):
        """
        Log a learning insight about the user
        """
        user_insight = UserInsight(
            category=category,
            insight=insight,
            confidence=confidence,
            evidence=evidence,
            created_at=datetime.now().isoformat()
        )
        
        if user_id not in self.insights:
            self.insights[user_id] = []
        
        self.insights[user_id].append(user_insight)
        self._save_insights()
        
        return user_insight
    
    def get_dashboard_data(self, user_id: str, session_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for frontend
        """
        # Analyze current session for new opportunities
        if session_context:
            self.analyze_session_for_opportunities(user_id, session_context)
        
        user_opportunities = self.opportunities.get(user_id, [])
        user_insights = self.insights.get(user_id, [])
        
        # Get recent opportunities (last 30 days)
        recent_cutoff = datetime.now() - timedelta(days=30)
        recent_opportunities = [
            opp for opp in user_opportunities
            if datetime.fromisoformat(opp.created_at) > recent_cutoff
        ]
        
        # Categorize opportunities
        obvious_opps = [opp for opp in recent_opportunities if opp.type == "obvious"]
        unobvious_opps = [opp for opp in recent_opportunities if opp.type == "unobvious"]
        
        # Learning insights by category
        insights_by_category = {}
        for insight in user_insights[-10:]:  # Last 10 insights
            if insight.category not in insights_by_category:
                insights_by_category[insight.category] = []
            insights_by_category[insight.category].append(asdict(insight))
        
        return {
            "opportunities": {
                "obvious": [asdict(opp) for opp in obvious_opps],
                "unobvious": [asdict(opp) for opp in unobvious_opps],
                "total_count": len(recent_opportunities),
                "high_priority_count": len([opp for opp in recent_opportunities if opp.priority == "high"])
            },
            "insights": insights_by_category,
            "learning_summary": {
                "total_insights": len(user_insights),
                "confidence_avg": sum(i.confidence for i in user_insights[-5:]) / min(5, len(user_insights)) if user_insights else 0,
                "top_categories": list(insights_by_category.keys())[:3]
            },
            "activity_summary": self._get_activity_summary(session_context or {})
        }
    
    def _get_activity_summary(self, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate activity summary from session context
        """
        summary = {
            "contacts_managed": len(session_context.get("contacts", {}).get("by_email", {})),
            "recent_meetings": 1 if "last_meeting" in session_context else 0,
            "recent_emails": 1 if "last_email_status" in session_context else 0,
            "last_activity": None
        }
        
        # Find most recent activity
        activities = []
        if "last_meeting" in session_context:
            activities.append(("meeting", session_context["last_meeting"].get("timestamp", "")))
        if "last_email_status" in session_context:
            activities.append(("email", session_context["last_email_status"].get("timestamp", "")))
        
        if activities:
            activities.sort(key=lambda x: x[1], reverse=True)
            summary["last_activity"] = {
                "type": activities[0][0],
                "timestamp": activities[0][1]
            }
        
        return summary
    
    def update_opportunity_status(self, user_id: str, opportunity_id: str, status: str):
        """
        Update opportunity status (for frontend interaction)
        """
        user_opportunities = self.opportunities.get(user_id, [])
        for opp in user_opportunities:
            if opp.id == opportunity_id:
                opp.status = status
                opp.updated_at = datetime.now().isoformat()
                break
        
        self._save_opportunities()

# Global instance for API usage
dashboard_service = DashboardService()

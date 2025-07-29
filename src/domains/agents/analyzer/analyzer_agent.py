"""
Analyzer Agent for DELA AI - Intelligence Analyzer
Processes Observer patterns into structured intelligence and provides insights for automation
"""

import asyncio
import logging
from datetime import datetime
from readline import insert_text
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from src.core.base_agent import BaseAgent, Belief, Desire, Intention


logger = logging.getLogger(__name__)

@dataclass
class AutomationOpportunity:
    opportunity_id: str
    opportunity_type: str
    description: str
    confidence: float
    frequency: int
    potential_time_saved: int
    complexity: str
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class BusinessInsight:
    insight_id: str
    insight_type: str
    title: str
    description: str
    confidence: float
    impact: str
    data_points: int
    created_at: datetime = field(default_factory=datetime.now)

class AnalyzerAgent(BaseAgent):
    """
    Analyzer Agent - Processes Observer data into structured intelligence and provides insights for automation
    """

    def __init__(self, agent_id: str = "analyzer_001"):
        super().__init__(agent_id, "analyzer", temperature=0.2)

        self.automation_opportunities: Dict[str, AutomationOpportunity] = {}
        self.business_insights: Dict[str, BusinessInsight] = {}
        self.communication_styles: Dict[str, Any] = {}

        self.min_pattern_frequency = 3
        self.min_confidence_threshold = 0.6

        self.desires = [
            Desire(
                desire_id="analyze_patterns",
                description="Analyze observer patterns for intelligence",
                priority=0.9,
                conditions={"has_observer_data": True}
            ),
            Desire(
                desire_id="identify_automation_opportunities",
                description="Identify automation opportunities from observer patterns",
                priority=0.8,
                conditions={"has_patterns": True}
            )
        ]

        logger.info(f"Analyzer Agent initialized: {self.agent_id}")

    async def perceive(self, messages: List[Any], context: Dict[str, Any]) -> List[Belief]:
        """Perceive Observer data and patterns"""

        beliefs = []

        try:
            observer_patterns = context.get("observer_patterns", {})
            observer_contacts = context.get("observer_contacts", {})

            if observer_patterns:
                comm_belief = await self._analyze_communication_patterns(observer_patterns)
                if comm_belief:
                    beliefs.append(comm_belief)
                
                automation_belief = await self._analyze_automation_opportunities(observer_patterns)
                if automation_belief:
                    beliefs.append(automation_belief)

            if observer_contacts:
                contact_belief = await self._analyze_contact_relationships(observer_contacts)
                if contact_belief:
                    beliefs.append(contact_belief)
                
            logger.info(f"Analyzer perceived {len(beliefs)} beliefs from observer data")
        
        except Exception as e:
            logger.error(f"Error in Analyzer perception: {e}")

        return beliefs

    async def update_desires(self, beliefs: List[Belief], context: Dict[str, Any]) -> List[Desire]:
        """Update agent desires based on analysis of observer data"""

        updated_desires = []

        
        for desire in self.desires:
            if desire.desire_id == "analyze_patterns":
                if any(b.belief_type == "communication_analysis" for b in beliefs):
                    desire.priority = 0.95
                    updated_desires.append(desire)
            
            elif desire.desire_id == "identify_automation":
                if len(self.automation_opportunities) < 15:
                    desire.priority = 0.85
                    updated_desires.append(desire)
            
        return updated_desires

    async def deliberate(self, beliefs: List[Belief], desires: List[Desire], current_intentions: List[Intention]) -> List[Intention]:
        """Deliberate on analysis actions"""
        intentions = []
        
        for desire in sorted(desires, key=lambda d: d.priority, reverse=True):
            if desire.desire_id == "analyze_patterns":
                intentions.append(Intention(
                    intention_id=f"analyze_patterns_{datetime.now().timestamp()}",
                    description="Analyze Observer patterns for intelligence",
                    action_type="pattern_analysis",
                    priority=desire.priority,
                    parameters={"beliefs": beliefs}
                ))
            
            elif desire.desire_id == "identify_automation":
                intentions.append(Intention(
                    intention_id=f"identify_automation_{datetime.now().timestamp()}",
                    description="Identify automation opportunities",
                    action_type="automation_identification",
                    priority=desire.priority,
                    parameters={"patterns": beliefs}
                ))
        
        return intentions[:2]

    async def act(self, intention: Intention, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an analysis action"""
        result = {"action_taken": False, "results": {} }
        
        try:
            if intention.action_type == "pattern_analysis":
                result = await self._execute_pattern_analysis(intention.parameters)
            elif intention.action_type == "automation_identification":
                result = await self._execute_automation_identification(intention.parameters)
            
            result["action_taken"] = True
            logger.info(f"Analyzer executed action: {intention.action_type}")
            
        except Exception as e:
            logger.error(f"Error executing Analyzer action: {e}", exc_info=True)
            result["error"] = str(e)
        
        return result

    
        
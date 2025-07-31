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

from src.core.base_agent import BaseAgent, Belief, Desire, Intention, BeliefType


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
                id="analyze_patterns",
                goal="Analyze observer patterns for intelligence",
                priority=9,
                conditions={"has_observer_data": True}
            ),
            Desire(
                id="identify_automation_opportunities", 
                goal="Identify automation opportunities from observer patterns",
                priority=8,
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
                contact_belief = await self._analyze_relationships(observer_contacts)
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
            if desire.id == "analyze_patterns":
                if any(belief.type == BeliefType.KNOWLEDGE for belief in beliefs):
                    desire.priority = 9
                    updated_desires.append(desire)
            
            elif desire.id == "identify_automation_opportunities":
                if len(self.automation_opportunities) < 15:
                    desire.priority = 8
                    updated_desires.append(desire)
            
        return updated_desires

    async def deliberate(self, beliefs: List[Belief], desires: List[Desire], current_intentions: List[Intention]) -> List[Intention]:
        """Deliberate on analysis actions"""
        intentions = []
        
        for desire in sorted(desires, key=lambda d: d.priority, reverse=True):
            if desire.id == "analyze_patterns":
                intentions.append(Intention(
                    id=f"analyze_patterns_{datetime.now().timestamp()}",
                    desire_id="analyze_patterns",
                    action_type="pattern_analysis",
                    # priority=desire.priority,
                    parameters={"beliefs": beliefs}
                ))
            
            elif desire.id == "identify_automation_opportunities":
                intentions.append(Intention(
                    id=f"identify_automation_opportunities_{datetime.now().timestamp()}",
                    desire_id="identify_automation_opportunities",
                    action_type="automation_identification",
                    # priority=desire.priority,
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

    async def learn(self, beliefs: List[Belief], intentions: List[Intention], context: Dict[str, Any]) -> None:
        """Learn from analysis results"""
        try:
            for belief in beliefs:
                if belief.confidence > self.min_confidence_threshold and belief.type == BeliefType.KNOWLEDGE:
                    if belief.type == BeliefType.KNOWLEDGE:
                        self._update_automation_confidence(belief)
            
            logger.info(f"Analyzer learning completed with {len(beliefs)} beliefs")
            
        except Exception as e:
            logger.error(f"Error in Analyzer learning: {e}", exc_info=True)

        
    async def _analyze_communication_patterns(self, patterns: Dict[str, Any]) -> Optional[Belief]:
        """Analyze communication patterns from Observer"""
        try:
            communication_analysis = {
                "total_patterns": len(patterns),
                "high_confidence_patterns": len([p for p in patterns.values() if p.confidence > 0.8]),
                "communication_styles_identified": 0,
                "tone_distribution": defaultdict(int)
            }
            
            for pattern in patterns.values():
                if pattern.pattern_type.startswith("comm_"):
                    communication_analysis["communication_styles_identified"] += 1
            
            return Belief(
                id=f"comm_analysis_{datetime.now().timestamp()}",
                type=BeliefType.KNOWLEDGE,
                content=communication_analysis,
                confidence=0.8,
                source="analyzer_agent"
            )
            
        except Exception as e:
            logger.error(f"Error analyzing communication patterns: {e}")
            return None

    async def _analyze_automation_opportunities(self, patterns: Dict[str, Any]) -> Optional[Belief]:
        """Identify automation opportunities"""
        try:
            opportunities = []
            
            for pattern in patterns.values():
                if pattern.frequency >= self.min_pattern_frequency and pattern.confidence >= 0.7:
                    
                    if pattern.pattern_type.startswith("comm_"):
                        opportunity = AutomationOpportunity(
                            opportunity_id=f"template_{len(self.automation_opportunities)}",
                            opportunity_type="template_response",
                            description=f"Automate {pattern.pattern_type} responses",
                            confidence=pattern.confidence,
                            frequency=pattern.frequency,
                            potential_time_saved=5,
                            complexity="low"
                        )
                        opportunities.append(opportunity)
                        self.automation_opportunities[opportunity.opportunity_id] = opportunity
                    
                    if "meeting" in pattern.pattern_type or "schedule" in pattern.pattern_type:
                        opportunity = AutomationOpportunity(
                            opportunity_id=f"meeting_{len(self.automation_opportunities)}",
                            opportunity_type="meeting_scheduling",
                            description=f"Automate meeting scheduling",
                            confidence=pattern.confidence,
                            frequency=pattern.frequency,
                            potential_time_saved=15,
                            complexity="medium"
                        )
                        opportunities.append(opportunity)
                        self.automation_opportunities[opportunity.opportunity_id] = opportunity
            
            return Belief(
                id=f"automation_opportunities_{datetime.now().timestamp()}",
                type=BeliefType.KNOWLEDGE,
                content={"opportunities_found": len(opportunities), "opportunities": opportunities},
                confidence=0.8,
                source="analyzer_agent"
            )
            
        except Exception as e:
            logger.error(f"Error analyzing automation opportunities: {e}")
            return None

    async def _analyze_relationships(self, relationships: Dict[str, Any]) -> Optional[Belief]:
        """Analyze relationships from Observer"""
        try:
            if not relationships:
                return None
        
            relationship_types = defaultdict(int)
            high_confidence_count = 0

            for rel in relationships.values():
                if getattr(rel, "confidence", 0) > 0.8:
                    high_confidence_count += 1
                r_type = getattr(rel, "relationship_type", "unknown")
                relationship_types[r_type] += 1
        
            relationship_analysis = {
                "total_relationships": len(relationships),
                "high_confidence_relationships": high_confidence_count,
                "relationship_types": dict(relationship_types)
            }

            # confidence metric could be ratio of high confidence
            computed_confidence = high_confidence_count / max(len(relationships), 1)

            return Belief(
                id=f"relationship_analysis_{datetime.now().timestamp()}",
                type=BeliefType.KNOWLEDGE,
                content=relationship_analysis,
                confidence=computed_confidence,
                source="analyzer_agent"
            )

        except Exception as e:
            logger.error(f"Error analyzing relationships: {e}")
            return None

    async def _execute_pattern_analysis(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pattern analysis"""
        beliefs = parameters.get("beliefs", [])
        
        analysis_results = {
            "patterns_analyzed": len(beliefs),
            "insights_generated": 0,
            "automation_opportunities": 0
        }
        
        for belief in beliefs:
            if belief.content.get("type") == "communication_analysis":
                analysis_results["insights_generated"] += 1
                
                insight = BusinessInsight(
                    insight_id=f"comm_insight_{len(self.business_insights)}",
                    insight_type="communication_pattern",
                    title="Communication Pattern Analysis",
                    description=f"Analyzed {belief.content.get('total_patterns', 0)} patterns",
                    confidence=belief.confidence,
                    impact="medium",
                    data_points=belief.content.get('total_patterns', 0)
                )
                self.business_insights[insight.insight_id] = insight
        
        return analysis_results
    
    async def _execute_automation_identification(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute automation opportunity identification"""
        return {
            "opportunities_identified": len(self.automation_opportunities),
            "high_priority_opportunities": len([
                opp for opp in self.automation_opportunities.values() if opp.confidence > 0.8
            ]),
            "potential_time_savings": sum([
                opp.potential_time_saved * opp.frequency 
                for opp in self.automation_opportunities.values()
            ])
        }
    
    def _update_automation_confidence(self, belief: Belief):
        """Update automation opportunity confidence"""
        opportunities = belief.content.get("opportunities", [])
        for opp in opportunities:
            if opp.opportunity_id in self.automation_opportunities:
                self.automation_opportunities[opp.opportunity_id].confidence = min(
                    self.automation_opportunities[opp.opportunity_id].confidence + 0.1, 1.0
                )
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get analysis summary for reporting"""
        return {
            "automation_opportunities": len(self.automation_opportunities),
            "business_insights": len(self.business_insights),
            "communication_styles": len(self.communication_styles),
            "high_confidence_opportunities": len([
                opp for opp in self.automation_opportunities.values() 
                if opp.confidence > 0.8
            ]),
            "total_time_savings_potential": sum([
                opp.potential_time_saved * opp.frequency 
                for opp in self.automation_opportunities.values()
            ])
        }
    
    def get_top_automation_opportunities(self, limit: int = 10) -> List[AutomationOpportunity]:
        """Get top automation opportunities"""
        return sorted(
            self.automation_opportunities.values(),
            key=lambda x: (x.confidence * x.frequency * x.potential_time_saved),
            reverse=True
        )[:limit]
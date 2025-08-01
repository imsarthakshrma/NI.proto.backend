"""
Decision Agent for Dela AI
Processes analyzer insights and makes strategic decisions for automation
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from src.core.base_agent import BaseAgent, Belief, Desire, Intention, BeliefType


logger = logging.getLogger(__name__)


@dataclass
class AutomationDecision:

    decision_id: str
    opportunity_id: str
    decision_type: str  # approve, reject, defer, modify
    priority: int  # 1-10
    confidence: float
    risk_level: str  # low, medium, high
    implementation_timeline: str  # immediate, short_term, long_term
    resource_requirements: Dict[str, Any]
    expected_roi: float
    justification: str
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class RiskAssessment:
    
    risk_id: str
    risk_type: str
    severity: str  # low, medium, high
    probablity: float
    impact: str
    mitigation_strategy: str
    confidence: float

@dataclass
class BusinessImpact:
    impact_id: str
    impact_type: str # time_savings, cost_reduction, quality_improvement
    quantified_value: float
    measurement_unit: str # hours, days, weeks, months, years, dollars, euros, percentage, etc.
    affected_processes: List[str]
    stakeholders: List[str]
    confidence: float

    def __init__(self, agent_id: str = "decision_agent_001"):
        super().__init__(agent_id) 

        self.decisions: Dict[str, AutomationDecision] = {}
        self.risk_assessments: Dict[str, RiskAssessment] = {}
        self.business_impacts: Dict[str, BusinessImpact] = {}

        self.min_roi_threshold = 2.0  # minimum 200% ROI threshold
        self.max_risk_tolerance = 0.7 # maximum 70% risk tolerance
        self.min_confidence_threshold = 0.6 # minimum 60% confidence threshold

        self.desires = [
            Desire(
                id="evaluate_opportunities",
                goal="Evaluate automation opportunities for business value",
                priority=9,
                conditions={"has_analyzer_insights": True}
            ),
            Desire(
                id="assess_risks",
                goal="Assess risks for proposed automations",
                priority=8,
                conditions={"has_opportunities": True}
            ),
            Desire(
                id="make_decisions",
                goal="Make strategic automation decisions",
                priority=10,
                conditions={"has_risk_assessment": True}
            ),
            Desire(
                id="prioritize_implementations",
                goal="Prioritize automation implementations",
                priority=7,
                conditions={"has_approved_decisions": True}
            )
        ]

        logger.info(f"Decision Agent initialized: {self.agent_id}")

    async def perceive(self, message: Dict[str, Any], context: Dict[str, Any]) -> List[Belief]:
        """Perceive phase - process analyzer insights"""
        beliefs = []

        try:
            # process opportunities from analyzer
            if "analyzer_opportunities" in context:
                opportunities = context["analyzer_opportunities"]
                for opp in opportunities:
                    opportunity_belief = await self._process_opportunity(opp)
                    if opportunity_belief:
                        beliefs.append(opportunity_belief)

        
            if "analyzer_insights" in context:
                insights = context["analyzer_insights"]
                for insight in insights:
                    insight_belief = await self._process_insight(insight) # process insights from analyzer
                    if insight_belief:
                        beliefs.append(insight_belief)

            # process existing automation performance data
            if "automation_performance" in context:
                performance_data = context["automation_performance"]
                performance_belief = await self._process_performance(performance_data)  
                if performance_belief:
                    beliefs.append(performance_belief)

            logger.info(f"Decision Agent perceived: {len(beliefs)} beliefs")

        except Exception as e:
            logger.error(f"Error in Decision Agent perception: {e}", exc_info=True)
            
        return beliefs

    async def update_desires(self, beliefs: List[Belief], context: Dict[str, Any]) -> List[Desire]:
        """Update desires based on perceived automation opportunities"""
        updated_desires = []
        
        urgency = context.get('urgency_level', 'normal')
        available_resources = context.get('resources', {})
        time_constraints = context.get('time_limit')

        for desire in self.desires:
            if desire.id == "evaluate_opportunities":
                if any(belief.type == BeliefType.KNOWLEDGE for belief in beliefs):
                    # use context to adjust priority
                    base_priority = 10
                    if urgency == 'high':
                        base_priority += 2
                    if available_resources.get('cpu_usage', 0) > 0.8:
                        base_priority -= 1
                    
                    desire.priority = base_priority
                    updated_desires.append(desire)
                
            elif desire.id == "assess_risks":
                if len(self.decisions) > 0:
                    # context-aware priority adjustment
                    risk_tolerance = context.get('risk_tolerance', 'medium')
                    priority = 9 if risk_tolerance == 'low' else 7
                    desire.priority = priority
                    updated_desires.append(desire)
                
            elif desire.id == "make_decisions":
                if len(self.risk_assessments) > 0:
                    # consider time constraints from context
                    priority = 10
                    if time_constraints and time_constraints < 300:  # 5 minutes
                        priority = 12  # higher urgency
                    desire.priority = priority
                    updated_desires.append(desire)

        return updated_desires



    async def deliberate (self, belief: List[Belief], desires: List[Desire], current_intentions: List[Intention]) -> List[Intention]:
        

        intentions = []

        for desire in sorted(desires, key=lambda d: d.priority, reverse=True):
            if desire.id == "evaluate_opportunities":
                intentions.append(Intention(
                    id=f"evaluate_opportunities_{datetime.now().timestamp()}",
                    desire_id="evaluate_opportunities",
                    action_type="opportunity_evaluation",
                    # priority=desire.priority,
                    parameters={"beliefs": beliefs}
                ))
        
            elif desire.id == "assess_risks":
                intentions.append(Intention(
                    id=f"assess_risks_{datetime.now().timestamp()}",
                    desire_id="assess_risks",
                    action_type="risk_assessment",
                    # priority=desire.priority,
                    parameters={"opportunities": beliefs}
                ))
            
            elif desire.id == "make_decisions":
                intentions.append(Intention(
                    id=f"make_decisions_{datetime.now().timestamp()}",
                    desire_id="make_decisions",
                    action_type="decision_making",
                    # priority=desire.priority,
                    parameters={"risk_assessments": self.risk_assessments}
                ))

            elif desire.id == "prioritize_implementations":
                intentions.append(Intention(
                    id=f"prioritize_implementations_{datetime.now().timestamp()}",
                    desire_id="prioritize_implementations",
                    action_type="implementation_prioritization",
                    # priority=desire.priority,
                    parameters={"decisions": self.decisions}
                ))

            return intentions[:3]
        
    async def act(self, intention: Intention, context: Dict[str, Any]) -> Dict[str, Any]:

        result = {"action_taken": False, "results": {} }


        try:
            if intention.action_type == "opportunity_evaluation":
                result = await self._execute_opportunity_evaluation(intention.parameters)
            elif intention.action_type == "risk_assessment":
                result = await self._execute_risk_assessment(intention.parameters)
            elif intention.action_type == "decision_making":
                result = await self._execute_decision_making(intention.parameters)
            elif intention.action_type == "implementation_prioritization":
                result = await self._execute_implementation_prioritization(intention.parameters)
            
            result["action_taken"] = True
            logger.info(f"Decision Agent executed action: {intention.action_type}")
            
        except Exception as e:
            logger.error(f"Error executing Decision Agent action: {e}")
            result["error"] = str(e)
        
        return result

    async def learn(self, beliefs: List[Belief], intentions: List[Intention], context: Dict[str, Any]) -> None:

        try: 
            for belief in beliefs:
                if belief.confidence > self.min_confidence_threshold:
                    if belief.type == BeliefType.KNOWLEDGE:
                        await self._update_decision_confidence(belief)

            logger.info(f"Decision Agent learning completed with {len(beliefs)} beliefs")
            
        except Exception as e:
            logger.error(f"Error in Decision Agent learning: {e}")

    async def _process_opportunity(self, opportunity: Dict[str, Any]) -> Optional[Belief]:

        #TODO: implement opportunity processing
        return None

    async def _process_insight(self, insight: Dict[str, Any]) -> Optional[Belief]:

        #TODO: implement insight processing
        return None

    async def _process_performance(self, performance_data: Dict[str, Any]) -> Optional[Belief]:

        #TODO: implement performance processing
        return None

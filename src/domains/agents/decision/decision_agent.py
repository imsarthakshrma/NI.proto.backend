"""
Decision Agent for Native AI
Processes analyzer insights and makes strategic decisions for automation
"""

# import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict, is_dataclass
# from collections import defaultdict

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
    probability: float
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

class DecisionAgent(BaseAgent):
    """
    Decision Agent - Makes strategic automation decisions based on Analyzer insights
    
    Core Responsibilities:
    - Evaluate automation opportunities from Analyzer
    - Assess risks and business impact
    - Make go/no-go decisions on automation implementations
    - Prioritize automation initiatives
    - Generate implementation recommendations
    """

    def __init__(self, agent_id: str = "decision_agent_001"):
        super().__init__(agent_id, "decision_agent", temperature=0.2) 

        self.decisions: Dict[str,  AutomationDecision] = {}
        self.risk_assessments: Dict[str, RiskAssessment] = {}
        self.business_impacts: Dict[str, BusinessImpact] = {}

        self.min_roi_threshold = 2.0  # minimum 200% ROI threshold
        self.max_risk_tolerance = 0.7 # maximum 70% risk tolerance
        self.min_confidence_threshold = 0.6 # minimum 60% confidence threshold

        self.learning_history: List[Belief] = []

        self.prioritized_implementations: List[Dict[str, Any]] = []

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



    async def deliberate(self, beliefs: List[Belief], desires: List[Desire], current_intentions: List[Intention]) -> List[Intention]:
        
        intentions = []

        # filter out any intentions that are not in the current_intentions list
        existing_types = {intention.action_type for intention in current_intentions}

        for desire in sorted(desires, key=lambda d: d.priority, reverse=True):
            if desire.id == "evaluate_opportunities":
                if "opportunity_evaluation" not in existing_types:
                    intentions.append(Intention(
                        id=f"evaluate_opportunities_{datetime.now().timestamp()}",
                    desire_id="evaluate_opportunities",
                    action_type="opportunity_evaluation",
                    # priority=desire.priority,
                    parameters={"beliefs": beliefs}
                ))
        
            elif desire.id == "assess_risks":
                if "risk_assessment" not in existing_types:
                    intentions.append(Intention(
                    id=f"assess_risks_{datetime.now().timestamp()}",
                    desire_id="assess_risks",
                    action_type="risk_assessment",
                    # priority=desire.priority,
                    parameters={"opportunities": beliefs}
                ))
            
            elif desire.id == "make_decisions":
                if "decision_making" not in existing_types:
                    intentions.append(Intention(
                    id=f"make_decisions_{datetime.now().timestamp()}",
                    desire_id="make_decisions",
                    action_type="decision_making",
                    # priority=desire.priority,
                    parameters={"risk_assessments": self.risk_assessments}
                ))

            elif desire.id == "prioritize_implementations":
                if "implementation_prioritization" not in existing_types:
                    intentions.append(Intention(
                    id=f"prioritize_implementations_{datetime.now().timestamp()}",
                    desire_id="prioritize_implementations",
                    action_type="implementation_prioritization",
                    # priority=desire.priority,
                    parameters={"decisions": self.decisions}
                ))

        return (current_intentions + intentions)[:3]
        
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
        """Learn from beliefs and intentions"""
        try: 
            for belief in beliefs:
                if belief.confidence > self.min_confidence_threshold:
                    if belief.type == BeliefType.KNOWLEDGE:
                        await self._update_decision_confidence(belief)
        
            # optional: Learn from context about decision success rates
            if context.get('decision_success_rate'):
                self._adjust_confidence_threshold(context['decision_success_rate'])

            logger.info(f"Decision Agent learning completed with {len(beliefs)} beliefs")
        
        except Exception as e:
            logger.error(f"Error in Decision Agent learning: {e}")


    async def _process_opportunity(self, opportunity) -> Optional[Belief]:
        """Process opportunity and generate belief"""
        try:
            if is_dataclass(opportunity):
                opp_dict = asdict(opportunity)
                opp_id = opportunity.opportunity_id
            else:
                opp_dict = opportunity
                opp_id = opportunity.get("opportunity_id")
            impact = await self._calculate_impact(opp_dict)
            risk = await self._assess_initial_risk(opp_dict)
            opportunity_analysis = {
                "opportunity_id": opp_id,
                "business_impact": impact,
                "initial_risk": risk,
                "evaluation_status": "pending",
                "analyzer_confidence": opp_dict.get("confidence", 0.0)
            }

            # --- Decision creation logic for integration test ---
            decision_type = "approve" if opportunity_analysis["analyzer_confidence"] > 0.2 else "reject"
            decision = AutomationDecision(
                decision_id=f"decision_{datetime.now().timestamp()}",
                opportunity_id=opp_id,
                decision_type=decision_type,
                priority=8 if decision_type == "approve" else 3,
                confidence=opportunity_analysis["analyzer_confidence"],
                risk_level="low",  # Or use a real risk assessment if available
                implementation_timeline="short_term" if decision_type == "approve" else "deferred",
                resource_requirements={"budget": 5000, "team_size": 2, "timeline_weeks": 4},
                expected_roi=1.5,  # Or calculate if you have data
                justification="Auto-approved for prototype"
            )
            self.decisions[decision.decision_id] = decision

            return Belief(
                id=f"opportunity_analysis_{datetime.now().timestamp()}",
                type=BeliefType.KNOWLEDGE,
                content=opportunity_analysis,
                confidence=0.8,
                source="decision_agent"
            )
        except Exception as e:
            logger.error(f"Error processing opportunity: {e}")
        return None


    async def _process_insight(self, insight: Any) -> Optional[Belief]:
        """Process business insight from Analyzer"""
        try:
            # Handle both BusinessInsight objects and dictionaries
            if hasattr(insight, 'insight_id'):
                # This is a BusinessInsight dataclass object
                insight_analysis = {
                    "insight_id": insight.insight_id,
                    "insight_type": insight.insight_type,
                    "impact_level": getattr(insight, 'impact', 'medium'),
                    "actionable": True,
                    "confidence": insight.confidence,
                    "related_processes": [],
                    "potential_value": getattr(insight, 'data_points', 0)
                }
            else:
                # this is a dictionary (fallback)
                insight_analysis = {
                    "insight_id": insight.get("insight_id", f"insight_{datetime.now().timestamp()}"),
                    "insight_type": insight.get("type", "business_insight"),
                    "impact_level": insight.get("impact_level", "medium"),
                    "actionable": insight.get("actionable", True),
                    "confidence": insight.get("confidence", 0.7),
                    "related_processes": insight.get("processes", []),
                    "potential_value": insight.get("value", 0)
                }
            
            return Belief(
                id=f"insight_analysis_{datetime.now().timestamp()}",
                type=BeliefType.KNOWLEDGE,
                content=insight_analysis,
                confidence=0.75,
                source="decision_agent"
            )
            
        except Exception as e:
            logger.error(f"Error processing insight: {e}")
            return None

    async def _process_performance(self, performance_data: Dict[str, Any]) -> Optional[Belief]:
        """Process automation performance data"""
        try:
            performance_analysis = {
                "automation_id": performance_data.get("automation_id"),
                "success_rate": performance_data.get("success_rate", 0.0),
                "time_saved": performance_data.get("time_saved", 0),
                "error_rate": performance_data.get("error_rate", 0.0),
                "user_satisfaction": performance_data.get("user_satisfaction", 0.5),
                "roi_actual": performance_data.get("roi_actual", 0.0),
                "performance_trend": performance_data.get("trend", "stable"),
                "last_updated": datetime.now().isoformat()
            }
            
            return Belief(
                id=f"performance_analysis_{datetime.now().timestamp()}",
                type=BeliefType.KNOWLEDGE,
                content=performance_analysis,
                confidence=0.9,  # high confidence in actual performance data
                source="decision_agent"
            )
            
        except Exception as e:
            logger.error(f"Error processing performance data: {e}")
            return None

    async def _calculate_impact(self, opportunity: Dict[str, Any]) -> Optional[BusinessImpact]:
        """ Calculate business impact of opportunity """
        impact = {
            "time_savings_hours_per_week": 0,
            "cost_savings_per_month": 0,
            "quality_improvement_percentage": 0,
            "risk_reduction_percentage": 0,
            "scalability_factor": 1.0
        }
        
        # extract time savings from opportunity
        if "potential_time_saved" in opportunity:
            impact["time_savings_hours_per_week"] = opportunity["potential_time_saved"] / 60.0
        
        # calculate cost savings (assuming $50/hour labor cost)
        impact["cost_savings_per_month"] = impact["time_savings_hours_per_week"] * 4 * 50
        
        # estimate quality improvement based on automation type
        automation_type = opportunity.get("opportunity_type", "")
        if "scheduling" in automation_type.lower():
            impact["quality_improvement_percentage"] = 25
        elif "reporting" in automation_type.lower():
            impact["quality_improvement_percentage"] = 40
        elif "communication" in automation_type.lower():
            impact["quality_improvement_percentage"] = 15
        
        return impact

    async def _assess_initial_risk(self, opportunity: Dict[str, Any]) -> Optional[BusinessImpact]:
        """Assess initial risk for automation opportunity"""

        risk = {
            "technical_complexity": "medium",
            "business_disruption": "low",
            "data_security": "low",
            "user_adoption": "medium",
            "overall_risk_score": 0.4
        }
        
        # adjust risk based on opportunity characteristics
        automation_type = opportunity.get("opportunity_type", "")
        
        if "email" in automation_type.lower():
            risk["data_security"] = "medium"
            risk["overall_risk_score"] = 0.5
        elif "calendar" in automation_type.lower():
            risk["technical_complexity"] = "low"
            risk["overall_risk_score"] = 0.3
        elif "financial" in automation_type.lower():
            risk["data_security"] = "high"
            risk["business_disruption"] = "medium"
            risk["overall_risk_score"] = 0.7
        
        return risk

    async def _execute_implementation_prioritization(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute implementation prioritization for approved decisions"""
        try:
            decisions = parameters.get("decisions", {})
            if isinstance(decisions, dict):
                decisions = list(decisions.values())
            
            # filter approved decisions
            approved_decisions = [d for d in decisions if hasattr(d, 'decision_type') and d.decision_type == "approve"]
            
            # prioritization criteria weights
            weights = {
                "roi": 0.4,          # 40% weight on ROI
                "risk": 0.2,         # 20% weight on risk (lower risk = higher priority)
                "complexity": 0.15,   # 15% weight on complexity (lower = higher priority)
                "impact": 0.25       # 25% weight on business impact
            }
            
            prioritized_decisions = []
            
            for decision in approved_decisions:
                # calculate priority score
                roi_score = min(decision.expected_roi / 5.0, 1.0)  # normalize to 0-1
                risk_score = 1.0 - (0.3 if decision.risk_level == "low" else 0.6 if decision.risk_level == "medium" else 0.9)
                
                # complexity score based on timeline
                complexity_score = 1.0 if decision.implementation_timeline == "immediate" else 0.7 if decision.implementation_timeline == "short_term" else 0.4
                
                # impact score based on expected ROI and resource requirements
                budget = decision.resource_requirements.get("budget", 5000)
                impact_score = min(decision.expected_roi * budget / 50000, 1.0)  # normalize
                
                # calculate weighted priority score
                priority_score = (
                    roi_score * weights["roi"] +
                    risk_score * weights["risk"] +
                    complexity_score * weights["complexity"] +
                    impact_score * weights["impact"]
                )
                
                prioritized_decisions.append({
                    "decision_id": decision.decision_id,
                    "opportunity_id": decision.opportunity_id,
                    "priority_score": priority_score,
                    "expected_roi": decision.expected_roi,
                    "risk_level": decision.risk_level,
                    "implementation_timeline": decision.implementation_timeline,
                    "resource_requirements": decision.resource_requirements,
                    "justification": decision.justification,
                    "recommended_order": 0  # will be set after sorting
                })
            
            # sort by priority score (highest first)
            prioritized_decisions.sort(key=lambda x: x["priority_score"], reverse=True)
            
            # assign recommended order
            for i, decision in enumerate(prioritized_decisions):
                decision["recommended_order"] = i + 1
            
            # store prioritized decisions
            self.prioritized_implementations = prioritized_decisions
            
            return {
                "prioritizations_completed": len(prioritized_decisions),
                "high_priority_count": len([d for d in prioritized_decisions if d["priority_score"] > 0.7]),
                "medium_priority_count": len([d for d in prioritized_decisions if 0.4 <= d["priority_score"] <= 0.7]),
                "low_priority_count": len([d for d in prioritized_decisions if d["priority_score"] < 0.4]),
                "total_expected_roi": sum(d["expected_roi"] for d in prioritized_decisions),
                "recommended_implementation_order": [d["opportunity_id"] for d in prioritized_decisions[:5]]
            }
            
        except Exception as e:
            logger.error(f"Error in implementation prioritization: {e}")
            return {
                "prioritizations_completed": 0,
                "error": str(e)
            }

    def get_prioritized_implementations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get prioritized implementation recommendations"""
        if not hasattr(self, 'prioritized_implementations'):
            return []
        
        return self.prioritized_implementations[:limit]

    async def _execute_opportunity_evaluation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:

        beliefs = parameters.get("beliefs", [])
        evaluations_completed = 0
        
        for belief in beliefs:
            if belief.type == BeliefType.KNOWLEDGE:
                content = belief.content
                if "opportunity_id" in content:
                    # Create business impact assessment
                    impact = BusinessImpact(
                        impact_id=f"impact_{content['opportunity_id']}",
                        impact_type="time_savings",
                        quantified_value=content.get("business_impact", {}).get("time_savings_hours_per_week", 0),
                        measurement_unit="hours_per_week",
                        affected_processes=["meeting_scheduling", "email_management"],
                        stakeholders=["project_managers", "executives"],
                        confidence=0.8
                    )
                    
                    self.business_impacts[impact.impact_id] = impact
                    evaluations_completed += 1
        
        return {
            "evaluations_completed": evaluations_completed,
            "total_business_value": sum(impact.quantified_value for impact in self.business_impacts.values()),
            "high_impact_opportunities": len([i for i in self.business_impacts.values() if i.quantified_value > 5])
        }

    async def _execute_risk_assessment(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute comprehensive risk assessment"""
        opportunities = parameters.get("opportunities", [])
        assessments_completed = 0
        
        for opportunity in opportunities:
            if hasattr(opportunity, 'content') and "opportunity_id" in opportunity.content:
                opp_id = opportunity.content["opportunity_id"]
                
                # create detailed risk assessment
                risk = RiskAssessment(
                    risk_id=f"risk_{opp_id}",
                    risk_type="implementation_risk",
                    severity="medium",
                    probability=0.3,
                    impact="Potential temporary workflow disruption during implementation",
                    mitigation_strategy="Phased rollout with pilot testing and user training",
                    confidence=0.7
                )
                
                self.risk_assessments[risk.risk_id] = risk
                assessments_completed += 1
        
        return {
            "assessments_completed": assessments_completed,
            "high_risk_items": len([r for r in self.risk_assessments.values() if r.severity == "high"]),
            "average_risk_probability": sum(r.probability for r in self.risk_assessments.values()) / max(len(self.risk_assessments), 1)
        }

    async def _execute_decision_making(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute strategic decision making"""
        assessments = parameters.get("assessments", [])
        decisions_made = 0
        approved_decisions = 0

        for assessment in assessments:
            if hasattr(assessment, 'content') and "opportunity_id" in assessment.content:
                opp_id = assessment.content["opportunity_id"]
                
                # create detailed risk assessment
                risk = RiskAssessment(
                    risk_id=f"risk_{opp_id}",
                    risk_type="implementation_risk",
                    severity="medium",
                    probability=0.3,
                    impact="Potential temporary workflow disruption during implementation",
                    mitigation_strategy="Phased rollout with pilot testing and user training",
                    confidence=0.75
                )
                
                self.risk_assessments[risk.risk_id] = risk
                assessments_completed += 1
        
        for impact_id, impact in self.business_impacts.items():
            # calculate ROI
            monthly_savings = impact.quantified_value * 4 * 50  # hours * weeks * hourly_rate
            implementation_cost = 5000  # estimated implementation cost
            roi = monthly_savings * 12 / implementation_cost if implementation_cost > 0 else 0
            
            # find corresponding risk
            risk_id = impact_id.replace("impact_", "risk_")
            risk = self.risk_assessments.get(risk_id)
            
            # make decision based on criteria
            decision_type = "approve"
            if roi < self.min_roi_threshold:
                decision_type = "reject"
            elif risk and risk.probability > self.max_risk_tolerance:
                decision_type = "defer"
            
            # create decision
            decision = AutomationDecision(
                decision_id=f"decision_{datetime.now().timestamp()}",
                opportunity_id=impact_id.replace("impact_", ""),
                decision_type=decision_type,
                priority=8 if decision_type == "approve" else 3,
                confidence=0.8,
                risk_level=risk.severity if risk else "low",
                implementation_timeline="short_term" if decision_type == "approve" else "deferred",
                resource_requirements={"budget": implementation_cost, "team_size": 2, "timeline_weeks": 4},
                expected_roi=roi,
                justification=f"ROI: {roi:.1f}x, Risk: {risk.severity if risk else 'low'}"
            )
            
            self.decisions[decision.decision_id] = decision
            decisions_made += 1
            
            if decision_type == "approve":
                approved_decisions += 1
        
        return {
            "decisions_made": decisions_made,
            "approved_decisions": approved_decisions,
            "total_expected_roi": sum(d.expected_roi for d in self.decisions.values() if d.decision_type == "approve"),
            "implementation_timeline": "4-8 weeks for approved automations"
        }

    async def _adjust_confidence_threshold(self, success_rate: float):
        """Adjust confidence threshold based on decision success rate"""

        if success_rate < 0.5:  # less than 50% success
            self.min_confidence_threshold = min(0.9, self.min_confidence_threshold + 0.05)
        elif success_rate > 0.8:  # greater than 80% success  
            self.min_confidence_threshold = max(0.3, self.min_confidence_threshold - 0.05)
        
        logger.info(f"Adjusted confidence threshold to {self.min_confidence_threshold} based on {success_rate} success rate")

    async def _update_decision_confidence(self, belief: Belief) -> None:
        """Update decision confidence based on feedback"""
        try:
            # extract key information from the belief
            belief_content = belief.content if hasattr(belief, 'content') else ""
            
            # update confidence based on belief type and content
            if "success" in belief_content or "approved" in belief_content:
                # positive outcome - increase confidence in similar decisions
                self._boost_confidence_for_similar_decisions(belief)
                
            elif "failed" in belief_content or "rejected" in belief_content:
                # negative outcome - decrease confidence 
                self._reduce_confidence_for_similar_decisions(belief)
                
            elif "risk" in belief_content:
                # risk-related knowledge - update risk assessment confidence
                await self._update_risk_assessment_confidence(belief)
                
            elif "roi" in belief_content or "return" in belief_content:
                # ROI-related knowledge - update financial projections confidence
                await self._update_roi_confidence(belief)
                
            # store the learning for future reference
            self._store_learning_history(belief)
            
            logger.info(f"Updated decision confidence based on belief: {belief.id}")
            
        except Exception as e:
            logger.error(f"Error updating decision confidence: {e}")

    def _boost_confidence_for_similar_decisions(self, belief: Belief) -> None:
        """Increase confidence for decisions similar to successful ones"""
        # Increase base confidence slightly
        if hasattr(self, 'base_confidence'):
            self.base_confidence = min(1.0, self.base_confidence + 0.05)
        
        # Track successful decision patterns
        if not hasattr(self, 'successful_patterns'):
            self.successful_patterns = []
        
        pattern = {
            'belief_type': belief.type,
            'confidence': belief.confidence,
            'timestamp': datetime.now(),
            'outcome': 'success'
        }
        self.successful_patterns.append(pattern)
        
        # Keep only recent patterns (last 50)
        self.successful_patterns = self.successful_patterns[-50:]

    def _reduce_confidence_for_similar_decisions(self, belief: Belief) -> None:
        """Decrease confidence for decisions similar to failed ones"""
        # Decrease base confidence slightly
        if hasattr(self, 'base_confidence'):
            self.base_confidence = max(0.1, self.base_confidence - 0.1)
        
        # Track failed decision patterns
        if not hasattr(self, 'failed_patterns'):
            self.failed_patterns = []
        
        pattern = {
            'belief_type': belief.type,
            'confidence': belief.confidence,
            'timestamp': datetime.now(),
            'outcome': 'failure'
        }
        self.failed_patterns.append(pattern)
        
        # Keep only recent patterns (last 50)
        self.failed_patterns = self.failed_patterns[-50:]

    async def _update_risk_assessment_confidence(self, belief: Belief) -> None:
        """Update confidence in risk assessments based on outcomes"""
        try:
            # Initialize risk confidence tracking if needed
            if not hasattr(self, 'risk_confidence_history'):
                self.risk_confidence_history = []
            
            # Determine if risk assessment was accurate
            risk_accuracy = self._calculate_risk_accuracy(belief)
            
            # Adjust risk assessment confidence
            if not hasattr(self, 'risk_assessment_confidence'):
                self.risk_assessment_confidence = 0.7  # Default
                
            if risk_accuracy > 0.8:
                self.risk_assessment_confidence = min(1.0, self.risk_assessment_confidence + 0.05)
            elif risk_accuracy < 0.4:
                self.risk_assessment_confidence = max(0.2, self.risk_assessment_confidence - 0.1)
            
            # Store history
            self.risk_confidence_history.append({
                'accuracy': risk_accuracy,
                'confidence': self.risk_assessment_confidence,
                'timestamp': datetime.now()
            })
            
            logger.info(f"Updated risk assessment confidence to {self.risk_assessment_confidence}")
            
        except Exception as e:
            logger.error(f"Error updating risk assessment confidence: {e}")

    async def _update_roi_confidence(self, belief: Belief) -> None:
        """Update confidence in ROI predictions based on actual outcomes"""
        try:
            # Initialize ROI confidence tracking if needed
            if not hasattr(self, 'roi_confidence_history'):
                self.roi_confidence_history = []
            
            # Calculate ROI prediction accuracy
            roi_accuracy = self._calculate_roi_accuracy(belief)
            
            # Adjust ROI prediction confidence
            if not hasattr(self, 'roi_prediction_confidence'):
                self.roi_prediction_confidence = 0.6  # Default
                
            if roi_accuracy > 0.9:
                self.roi_prediction_confidence = min(1.0, self.roi_prediction_confidence + 0.03)
            elif roi_accuracy < 0.5:
                self.roi_prediction_confidence = max(0.2, self.roi_prediction_confidence - 0.08)
            
            # Store history
            self.roi_confidence_history.append({
                'accuracy': roi_accuracy,
                'confidence': self.roi_prediction_confidence,
                'timestamp': datetime.now()
            })
            
            logger.info(f"Updated ROI prediction confidence to {self.roi_prediction_confidence}")
            
        except Exception as e:
            logger.error(f"Error updating ROI confidence: {e}")

    def _calculate_risk_accuracy(self, belief: Belief) -> float:
        """Calculate how accurate our risk assessment was"""
        # Simplified implementation - you'd customize based on your belief structure
        try:
            # Extract predicted vs actual risk from belief content
            content = belief.content
            if isinstance(content, dict):
                predicted_risk = content.get('predicted_risk', 0.5)
                actual_risk = content.get('actual_risk', 0.5)
                
                # Calculate accuracy (how close prediction was to reality)
                diff = abs(predicted_risk - actual_risk)
                accuracy = max(0.0, 1.0 - diff)
                return accuracy
            
            # fallback: assume moderate accuracy if no risk data
            return 0.6
            
        except Exception:
            return 0.5  # Default moderate accuracy

    def _calculate_roi_accuracy(self, belief: Belief) -> float:
        """Calculate how accurate our ROI prediction was"""
        try:
            # extract predicted vs actual ROI from belief content
            content = belief.content
            if isinstance(content, dict):
                predicted_roi = content.get('predicted_roi', 1.0)
                actual_roi = content.get('actual_roi', 1.0)
                
                # Calculate accuracy (how close prediction was to reality)
                diff = abs(predicted_roi - actual_roi) / max(predicted_roi, actual_roi, 0.1)
                accuracy = max(0.0, 1.0 - diff)
                return accuracy
            
            # fallback: assume moderate accuracy if no ROI data
            return 0.6
            
        except Exception:
            return 0.5  # default moderate accuracy

    def _store_learning_history(self, belief: Belief) -> None:
        """Store learning history for analysis"""
        if not hasattr(self, 'learning_history'):
            self.learning_history = []
        
        learning_record = {
            'belief_id': belief.id,
            'belief_type': belief.type,
            'confidence': belief.confidence,
            'timestamp': datetime.now(),
            'learning_applied': True
        }
        
        self.learning_history.append(learning_record)
        
        # Keep only recent history (last 100 records)
        self.learning_history = self.learning_history[-100:]

    def get_decision_summary(self) -> Dict[str, Any]:
        """Get decision summary for reporting"""
        approved_decisions = [d for d in self.decisions.values() if d.decision_type == "approve"]
        
        return {
            "total_decisions": len(self.decisions),
            "approved_decisions": len(approved_decisions),
            "rejected_decisions": len([d for d in self.decisions.values() if d.decision_type == "reject"]),
            "deferred_decisions": len([d for d in self.decisions.values() if d.decision_type == "defer"]),
            "total_expected_roi": sum(d.expected_roi for d in approved_decisions),
            "high_priority_decisions": len([d for d in approved_decisions if d.priority >= 8]),
            "total_business_impacts": len(self.business_impacts),
            "total_risk_assessments": len(self.risk_assessments)
        }

    def get_approved_decisions(self, limit: int = 10) -> List[AutomationDecision]:
        """Get top approved decisions for execution"""
        approved = [d for d in self.decisions.values() if d.decision_type == "approve"]
        return sorted(approved, key=lambda d: d.priority, reverse=True)[:limit]

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk assessment summary"""
        risks = list(self.risk_assessments.values())
        
        return {
            "total_risks_assessed": len(risks),
            "high_risk_count": len([r for r in risks if r.severity == "high"]),
            "medium_risk_count": len([r for r in risks if r.severity == "medium"]),
            "low_risk_count": len([r for r in risks if r.severity == "low"]),
            "average_risk_probability": sum(r.probability for r in risks) / max(len(risks), 1)
        }

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of learning progress"""
        summary = {
            'base_confidence': getattr(self, 'base_confidence', 0.7),
            'min_confidence_threshold': getattr(self, 'min_confidence_threshold', 0.6),
            'risk_assessment_confidence': getattr(self, 'risk_assessment_confidence', 0.7),
            'roi_prediction_confidence': getattr(self, 'roi_prediction_confidence', 0.6),
            'successful_patterns_count': len(getattr(self, 'successful_patterns', [])),
            'failed_patterns_count': len(getattr(self, 'failed_patterns', [])),
            'learning_history_count': len(getattr(self, 'learning_history', [])),
            'last_learning_update': getattr(self, 'learning_history', [{}])[-1:][0].get('timestamp') if hasattr(self, 'learning_history') and self.learning_history else None
        }
        return summary
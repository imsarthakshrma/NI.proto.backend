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


    async def _process_opportunity(self, opportunity: Dict[str, Any]) -> Optional[Belief]:
        """Process opportunity and generate belief"""
        try:
            impact = await self._calculate_impact(opportunity)

            risk = await self._assess_initial_risk(opportunity)

            opportunity_analysis = {
                "opportunity_id": opportunity.get("opportunity_id"),
                "business_impact": impact,
                "initial_risk": risk,
                "evaluation_status": "pending",
                "analyzer_confidence": opportunity.get("confidence", 0.0)
            }

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
            await self.min_confidence_threshold = min(0.9, self.min_confidence_threshold + 0.05)
        elif success_rate > 0.8:  # greater than 80% success  
           await self.min_confidence_threshold = max(0.3, self.min_confidence_threshold - 0.05)
        
        logger.info(f"Adjusted confidence threshold to {self.min_confidence_threshold} based on {success_rate} success rate")

    async def _update_decision_confidence(self, belief: Belief) -> None:
        """Update decision confidence based on feedback"""
        try:
            # extract key information from the belief
            belief_content = belief.content.lower() if hasattr(belief, 'content') else ""
            
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

    def _store_learning_history(self, belief: Belief) -> None:
        """Store learning history for future reference"""
        self.learning_history.append(belief)

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
"""
Decision Agent for Native IQ
LLM-Powered Decision Agent - Processes analyzer insights and makes strategic decisions for automation
"""

# import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict, is_dataclass
# from collections import defaultdict

from src.core.base_agent import BaseAgent, Belief, Desire, Intention, BeliefType
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


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
    proactive_suggestion: bool = False  # Whether this should be suggested proactively
    user_confirmation_required: bool = True  # Whether to ask user before executing
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
    LLM-Powered Decision Agent - Makes strategic automation decisions based on Analyzer insights
    
    Core Responsibilities:
    - Evaluate automation opportunities from Analyzer using LLM intelligence
    - Assess risks and business impact with contextual understanding
    - Make go/no-go decisions on automation implementations
    - Determine when to act proactively vs wait for user confirmation
    - Generate implementation recommendations with timing
    """

    def __init__(self, agent_id: str = "decision_agent_001"):
        super().__init__(agent_id, "decision_agent", temperature=0.2) 

        # Initialize LLM for intelligent decision making
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,  # Lower temperature for consistent decisions
            max_tokens=1500
        )

        self.decisions: Dict[str,  AutomationDecision] = {}
        self.risk_assessments: Dict[str, RiskAssessment] = {}
        self.business_impacts: Dict[str, BusinessImpact] = {}

        self.min_roi_threshold = 2.0  # minimum 200% ROI threshold
        self.max_risk_tolerance = 0.7 # maximum 70% risk tolerance
        self.min_confidence_threshold = 0.6 # minimum 60% confidence threshold

        self.learning_history: List[Belief] = []

        self.prioritized_implementations: List[Dict[str, Any]] = []

        # Enhanced desires for proactive decision making
        self.desires = [
            Desire(
                id="evaluate_opportunities",
                goal="Evaluate automation opportunities with LLM intelligence",
                priority=10,
                conditions={"has_analyzer_insights": True}
            ),
            Desire(
                id="assess_risks",
                goal="Assess implementation risks and business impact",
                priority=9,
                conditions={"has_opportunities": True}
            ),
            Desire(
                id="make_decisions",
                goal="Make strategic automation decisions",
                priority=8,
                conditions={"has_risk_assessments": True}
            ),
            Desire(
                id="determine_proactivity",
                goal="Decide when to act proactively vs ask user",
                priority=7,
                conditions={"has_decisions": True}
            )
        ]

        logger.info(f"LLM-Powered Decision Agent initialized: {self.agent_id}")

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
                # Trigger decision making when we have opportunity analyses
                opportunity_beliefs = [b for b in beliefs if "opportunity_analysis" in b.id]
                if len(opportunity_beliefs) > 0:
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
                    # Get automation opportunities from beliefs for decision making
                    opportunities = []
                    for belief in beliefs:
                        if "opportunity_analysis" in belief.id:
                            opportunities.append(belief.content)
                    
                    intentions.append(Intention(
                    id=f"make_decisions_{datetime.now().timestamp()}",
                    desire_id="make_decisions",
                    action_type="decision_making",
                    # priority=desire.priority,
                    parameters={"opportunities": opportunities}
                ))

            elif desire.id == "determine_proactivity":
                if "proactivity_determination" not in existing_types:
                    intentions.append(Intention(
                    id=f"determine_proactivity_{datetime.now().timestamp()}",
                    desire_id="determine_proactivity",
                    action_type="proactivity_determination",
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
            elif intention.action_type == "proactivity_determination":
                result = await self._execute_proactivity_determination(intention.parameters)
            
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


    async def _make_automation_decisions(self, opportunities: List[Dict[str, Any]]) -> List[AutomationDecision]:
        """LLM-powered decision making for automation opportunities"""
        try:
            if not opportunities:
                return []

            # Prepare opportunities for LLM analysis
            opportunities_summary = self._prepare_opportunities_for_llm(opportunities)
            
            # LLM prompt for decision making
            system_prompt = """You are an expert business automation decision maker. Analyze automation opportunities and make strategic go/no-go decisions.

For each opportunity, decide:
1. decision_type: approve, reject, defer, or modify
2. priority: 1-10 (10 = highest priority)
3. confidence: 0.0-1.0 confidence in this decision
4. risk_level: low, medium, high
5. implementation_timeline: immediate, short_term (1-2 weeks), long_term (1+ months)
6. expected_roi: Expected return on investment (2.0 = 200% ROI)
7. justification: Clear reasoning for the decision
8. proactive_suggestion: true/false - Should Native suggest this proactively?
9. user_confirmation_required: true/false - Ask user before executing?

Decision Criteria:
- APPROVE if: High frequency, significant time savings, low risk, clear ROI
- DEFER if: Good opportunity but needs more data or resources
- MODIFY if: Good concept but needs adjustments
- REJECT if: Low value, high risk, or not feasible

Proactive Suggestions Guidelines:
- Suggest proactively for: Low-risk, high-frequency, proven patterns
- Require confirmation for: Medium-risk, new automations, user-facing changes
- Never suggest proactively: High-risk, complex, or sensitive operations

Be conservative but practical. Focus on high-value, low-risk automations first."""

            user_prompt = f"""Make decisions for these automation opportunities:

{opportunities_summary}

For each opportunity, provide a clear decision with reasoning. Focus on business value and implementation feasibility."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            # Get LLM decision analysis
            response = await self.llm.ainvoke(messages)
            llm_analysis = response.content

            # Parse LLM response into structured decisions
            decisions = self._parse_automation_decisions(llm_analysis, opportunities)
            
            return decisions

        except Exception as e:
            logger.error(f"Error in LLM decision making: {e}")
            return []

    def _prepare_opportunities_for_llm(self, opportunities: List[Dict[str, Any]]) -> str:
        """Prepare opportunities data for LLM decision analysis"""
        try:
            opportunities_text = "AUTOMATION OPPORTUNITIES FOR DECISION:\n\n"
            
            for i, opp in enumerate(opportunities, 1):
                if isinstance(opp, dict) and 'opportunities' in opp:
                    # Handle nested structure from analyzer
                    for sub_opp in opp['opportunities']:
                        opportunities_text += f"Opportunity {i}:\n"
                        opportunities_text += f"Type: {sub_opp.get('type', 'Unknown')}\n"
                        opportunities_text += f"Description: {sub_opp.get('description', 'No description')}\n"
                        opportunities_text += f"Confidence: {sub_opp.get('confidence', 0.0):.2f}\n"
                        opportunities_text += f"Potential Time Saved: {sub_opp.get('time_saved', 0)} minutes\n"
                        opportunities_text += f"Frequency: Regular usage pattern\n"
                        opportunities_text += "---\n"
                else:
                    # Handle direct opportunity structure
                    opportunities_text += f"Opportunity {i}:\n"
                    opportunities_text += f"Type: {opp.get('type', 'Unknown')}\n"
                    opportunities_text += f"Description: {opp.get('description', 'No description')}\n"
                    opportunities_text += f"Confidence: {opp.get('confidence', 0.0):.2f}\n"
                    opportunities_text += f"Time Saved: {opp.get('time_saved', 0)} minutes\n"
                    opportunities_text += "---\n"
            
            return opportunities_text
            
        except Exception as e:
            logger.error(f"Error preparing opportunities for LLM: {e}")
            return "No opportunities available for decision making."

    def _parse_automation_decisions(self, llm_response: str, opportunities: List[Dict[str, Any]]) -> List[AutomationDecision]:
        """Parse LLM response into structured AutomationDecision objects"""
        decisions = []
        
        try:
            # Simple parsing - in production, use structured output
            lines = llm_response.split('\n')
            current_decision = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Look for decision markers
                if 'decision' in line.lower() and ':' in line:
                    if current_decision:
                        # Save previous decision
                        decision = self._create_decision_from_dict(current_decision, opportunities)
                        if decision:
                            decisions.append(decision)
                    current_decision = {'description': line}
                
                elif 'decision_type:' in line.lower() or 'decision:' in line.lower():
                    decision_type = line.split(':', 1)[1].strip().lower()
                    current_decision['decision_type'] = decision_type
                elif 'priority:' in line.lower():
                    try:
                        current_decision['priority'] = int(line.split(':', 1)[1].strip())
                    except:
                        current_decision['priority'] = 5
                elif 'confidence:' in line.lower():
                    try:
                        current_decision['confidence'] = float(line.split(':', 1)[1].strip())
                    except:
                        current_decision['confidence'] = 0.7
                elif 'risk_level:' in line.lower() or 'risk:' in line.lower():
                    current_decision['risk_level'] = line.split(':', 1)[1].strip().lower()
                elif 'timeline:' in line.lower():
                    current_decision['timeline'] = line.split(':', 1)[1].strip().lower()
                elif 'roi:' in line.lower():
                    try:
                        import re
                        numbers = re.findall(r'\d+\.?\d*', line)
                        if numbers:
                            current_decision['roi'] = float(numbers[0])
                    except:
                        current_decision['roi'] = 2.0
                elif 'proactive:' in line.lower():
                    current_decision['proactive'] = 'true' in line.lower()
                elif 'confirmation:' in line.lower():
                    current_decision['confirmation'] = 'true' in line.lower()
                elif 'justification:' in line.lower():
                    current_decision['justification'] = line.split(':', 1)[1].strip()
            
            # Don't forget the last decision
            if current_decision:
                decision = self._create_decision_from_dict(current_decision, opportunities)
                if decision:
                    decisions.append(decision)
                    
        except Exception as e:
            logger.error(f"Error parsing automation decisions: {e}")
            
        return decisions

    def _create_decision_from_dict(self, decision_dict: Dict[str, Any], opportunities: List[Dict[str, Any]]) -> Optional[AutomationDecision]:
        """Create AutomationDecision from parsed dictionary"""
        try:
            decision_id = f"decision_{datetime.now().timestamp()}"
            opportunity_id = f"opp_{len(opportunities)}"  # Simple mapping
            
            return AutomationDecision(
                decision_id=decision_id,
                opportunity_id=opportunity_id,
                decision_type=decision_dict.get('decision_type', 'defer'),
                priority=decision_dict.get('priority', 5),
                confidence=decision_dict.get('confidence', 0.7),
                risk_level=decision_dict.get('risk_level', 'medium'),
                implementation_timeline=decision_dict.get('timeline', 'short_term'),
                resource_requirements={'time': 'low', 'complexity': 'medium'},
                expected_roi=decision_dict.get('roi', 2.0),
                justification=decision_dict.get('justification', 'LLM-based decision'),
                proactive_suggestion=decision_dict.get('proactive', False),
                user_confirmation_required=decision_dict.get('confirmation', True)
            )
            
        except Exception as e:
            logger.error(f"Error creating decision: {e}")
            return None

    async def _execute_opportunity_evaluation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute opportunity evaluation process"""
        try:
            opportunities = parameters.get("opportunities", [])
            results = {
                "opportunities_evaluated": 0,
                "high_value_opportunities": 0,
                "evaluation_results": []
            }
            
            for opportunity in opportunities:
                # Process each opportunity
                belief = await self._process_opportunity(opportunity)
                if belief:
                    results["opportunities_evaluated"] += 1
                    if belief.content.get("analyzer_confidence", 0) > 0.7:
                        results["high_value_opportunities"] += 1
                    results["evaluation_results"].append(belief.content)
            
            logger.info(f"Evaluated {results['opportunities_evaluated']} opportunities")
            return results
            
        except Exception as e:
            logger.error(f"Error in opportunity evaluation: {e}")
            return {"opportunities_evaluated": 0, "error": str(e)}

    async def _execute_risk_assessment(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute risk assessment process"""
        try:
            opportunities = parameters.get("opportunities", [])
            results = {
                "risks_assessed": 0,
                "high_risk_count": 0,
                "risk_assessments": []
            }
            
            for opportunity in opportunities:
                risk_assessment = await self._assess_initial_risk(opportunity)
                if risk_assessment:
                    results["risks_assessed"] += 1
                    if risk_assessment.get("overall_risk_score", 0) > 0.6:
                        results["high_risk_count"] += 1
                    results["risk_assessments"].append(risk_assessment)
            
            logger.info(f"Assessed risks for {results['risks_assessed']} opportunities")
            return results
            
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            return {"risks_assessed": 0, "error": str(e)}

    async def _execute_decision_making(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute decision making process - creates decisions based on evaluations and risk assessments"""
        try:
            # Production confidence threshold (temporarily lowered for testing)
            PRODUCTION_CONFIDENCE_THRESHOLD = 0.3  # Will be 0.75 in production
            
            results = {
                "decisions_made": 0,
                "approved_decisions": 0,
                "rejected_decisions": 0,
                "deferred_decisions": 0
            }
            
            # Get evaluated opportunities from parameters or beliefs
            opportunities = parameters.get("opportunities", [])
            if not opportunities:
                # Fallback to beliefs if no opportunities in parameters
                opportunity_beliefs = [b for b in self.beliefs if "opportunity_analysis" in b.id]
                opportunities = [b.content for b in opportunity_beliefs]
            
            decisions = await self._make_automation_decisions(opportunities)
            
            for decision in decisions:
                # Store decision
                self.decisions[decision.decision_id] = decision
                results["decisions_made"] += 1
                
                if decision.decision_type == "approve":
                    results["approved_decisions"] += 1
                elif decision.decision_type == "reject":
                    results["rejected_decisions"] += 1
                else:
                    results["deferred_decisions"] += 1
                
                logger.info(f"Decision made: {decision.decision_type} for opportunity {decision.opportunity_id} (confidence: {decision.confidence:.2f})")
            
            logger.info(f"Decision making completed: {results['decisions_made']} decisions made")
            return results
            
        except Exception as e:
            logger.error(f"Error in decision making: {e}")
            return {"decisions_made": 0, "error": str(e)}

    async def _execute_proactivity_determination(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Determine proactivity for decisions"""
        try:
            decisions = parameters.get("decisions", [])
            results = {
                "proactivity_determined": 0,
                "proactive_suggestions": 0,
                "user_confirmation_required": 0
            }
            
            for decision in decisions:
                if decision.proactive_suggestion:
                    results["proactive_suggestions"] += 1
                if decision.user_confirmation_required:
                    results["user_confirmation_required"] += 1
                
                results["proactivity_determined"] += 1
            
            logger.info(f"Proactivity determined for {results['proactivity_determined']} decisions")
            return results
            
        except Exception as e:
            logger.error(f"Error in proactivity determination: {e}")
            return {"proactivity_determined": 0, "error": str(e)}

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
        
        return BusinessImpact(
            impact_id=f"impact_{datetime.now().timestamp()}",
            impact_type="time_savings",
            quantified_value=impact["time_savings_hours_per_week"],
            measurement_unit="hours",
            affected_processes=[],
            stakeholders=[],
            confidence=0.8
        )

    async def _assess_initial_risk(self, opportunity: Dict[str, Any]) -> Optional[RiskAssessment]:
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
        
        return RiskAssessment(
            risk_id=f"risk_{datetime.now().timestamp()}",
            risk_type="initial_risk",
            severity="low",
            probability=risk["overall_risk_score"],
            impact="low",
            mitigation_strategy="",
            confidence=0.8
        )

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
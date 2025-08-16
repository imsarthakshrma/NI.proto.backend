"""
Analyzer Agent for Native IQ - Intelligence Analyzer
Processes Observer patterns into structured intelligence and provides insights for automation
"""

import logging
from datetime import datetime
# from readline import insert_text
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from uuid import uuid4

from src.core.base_agent import BaseAgent, Belief, Desire, Intention, BeliefType
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

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
    LLM-Powered Analyzer Agent - Processes Observer data into structured intelligence and provides insights for automation
    """

    def __init__(self, agent_id: str = "analyzer_001"):
        super().__init__(agent_id, "analyzer", temperature=0.2)

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=2000
        )

        self.automation_opportunities: Dict[str, AutomationOpportunity] = {}
        self.business_insights: Dict[str, BusinessInsight] = {}
        self.communication_styles: Dict[str, Any] = {}

        self.min_pattern_frequency = 1
        self.min_confidence_threshold = 0.2

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

        logger.info(f"LLM-Powered Analyzer Agent initialized: {self.agent_id}")

    async def perceive(self, messages: List[Any], context: Dict[str, Any]) -> List[Belief]:
        """Perceive Observer data and patterns"""

        beliefs = []

        try:
            observer_patterns = context.get("observer_patterns", {})
            observer_contacts = context.get("observer_contacts", {})
            
            # Store patterns for later use in automation identification
            self._current_observer_patterns = observer_patterns

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
                # print("DEBUG pattern:", pattern, getattr(pattern, 'pattern_type', None), getattr(pattern, 'frequency', None), getattr(pattern, 'confidence', None))
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
        """LLM-powered automation opportunity analysis"""
        try:
            if not patterns:
                return None

            # 1) Filter patterns using thresholds to reduce noise
            filtered_patterns = {
                pid: p
                for pid, p in patterns.items()
                if getattr(p, "frequency", 0) >= self.min_pattern_frequency
                and getattr(p, "confidence", 0.0) >= self.min_confidence_threshold
            }
            if not filtered_patterns:
                logger.info("No patterns passed thresholds; skipping LLM analysis.")
                return None

            # 2) Prepare summarized, stable, ID-inclusive prompt content
            patterns_summary = self._prepare_patterns_for_llm(filtered_patterns)

            # 3) Instruct the LLM to return strict JSON with provenance
            system_prompt = (
                "You are an expert business automation analyst. "
                "Return ONLY valid JSON (no extra text) representing a list of 1-3 automation opportunities. "
                "Each item MUST include keys: "
                "opportunity_type (str), description (str), confidence (float 0-1), "
                "frequency (int), potential_time_saved (int), complexity (low|medium|high), "
                "trigger_conditions (str or list), source_pattern_ids (list[str])."
            )
            user_prompt = (
                "Analyze these user behavior patterns and identify the top 3 most valuable automation opportunities. "
                "Always reference pattern IDs in source_pattern_ids.\n\n"
                f"{patterns_summary}"
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            # 4) Invoke LLM
            response = await self.llm.ainvoke(messages)
            raw = response.content

            # 5) Parse JSON; fallback to heuristic text parser if needed
            try:
                import json
                parsed = json.loads(raw)
            except Exception:
                logger.warning("LLM response not valid JSON; using fallback text parser")
                parsed = raw  # will be handled by fallback

            # 6) Build domain objects
            opportunities = self._parse_automation_opportunities(parsed, filtered_patterns)

            # 7) Persist
            for opp in opportunities:
                self.automation_opportunities[opp.opportunity_id] = opp

            # 8) Return belief with rich content
            return Belief(
                id=f"automation_analysis_{datetime.now().timestamp()}",
                type=BeliefType.KNOWLEDGE,
                content={
                    "llm_raw": raw,
                    "opportunities_found": len(opportunities),
                    "opportunities": [
                        {
                            "id": opp.opportunity_id,
                            "type": opp.opportunity_type,
                            "description": opp.description,
                            "confidence": opp.confidence,
                            "frequency": opp.frequency,
                            "time_saved": opp.potential_time_saved,
                            "complexity": opp.complexity,
                            "trigger_conditions": opp.trigger_conditions,
                            "source_pattern_ids": opp.source_pattern_ids,
                        }
                        for opp in opportunities
                    ],
                },
                confidence=0.9,
                source="llm_analyzer_agent",
            )

        except Exception:
            logger.exception("Error in LLM automation analysis")
            return None
    
    def _prepare_patterns_for_llm(self, patterns: Dict[str, Any]) -> str:
        """Prepare patterns data in a format suitable for LLM analysis"""
        try:
            patterns_text = "USER BEHAVIOR PATTERNS:\n\n"
            for pattern_id, pattern in patterns.items():
                patterns_text += f"Pattern ID: {pattern_id}\n"
                patterns_text += f"Type: {pattern.pattern_type}\n"
                patterns_text += f"Description: {pattern.description}\n"
                patterns_text += f"Frequency: {pattern.frequency} times\n"
                patterns_text += f"Confidence: {pattern.confidence:.2f}\n"
                patterns_text += f"Context: {getattr(pattern, 'context', 'N/A')}\n"
                examples = getattr(pattern, 'examples', 'N/A')
                examples_str = examples if isinstance(examples, str) else str(examples)
                patterns_text += f"Examples: {examples_str[:200]}...\n"
                patterns_text += "---\n"
            return patterns_text
        except Exception as e:
            logger.error(f"Error preparing patterns for LLM: {e}")
            return "No patterns available for analysis."

    def _parse_automation_opportunities_from_text(self, llm_response: str, patterns: Dict[str, Any]) -> List[AutomationOpportunity]:
        """Heuristic parsing for non-JSON responses (best-effort)."""
        opportunities: List[AutomationOpportunity] = []
        try:
            import re

            lines = llm_response.splitlines()
            current: Dict[str, Any] = {}

            def flush():
                if current:
                    opp = self._create_opportunity_from_dict(current)
                    if opp:
                        opportunities.append(opp)

            for raw in lines:
                line = raw.strip()
                if not line:
                    continue

                # Start of a new opportunity block
                if re.search(r"\b(opportunity|automation)\b", line, re.I) and ":" in line:
                    flush()
                    current = {"description": line}

                elif "type:" in line.lower():
                    current["type"] = line.split(":", 1)[1].strip()

                elif "confidence:" in line.lower():
                    try:
                        current["confidence"] = float(line.split(":", 1)[1].strip())
                    except Exception:
                        current["confidence"] = 0.7

                elif "frequency:" in line.lower():
                    nums = re.findall(r"\d+", line)
                    if nums:
                        current["frequency"] = int(nums[0])

                elif "time saved:" in line.lower() or "minutes" in line.lower():
                    nums = re.findall(r"\d+", line)
                    if nums:
                        current["time_saved"] = int(nums[0])

                elif "complexity:" in line.lower():
                    current["complexity"] = line.split(":", 1)[1].strip().lower()

                elif "trigger" in line.lower():
                    current["trigger_conditions"] = line.split(":", 1)[-1].strip()

                elif "pattern" in line.lower() and "id" in line.lower():
                    # Try to collect IDs loosely
                    ids = re.findall(r"[A-Za-z0-9_\-]+", line)
                    # Heuristic: keep tokens that exist in patterns
                    current["source_pattern_ids"] = [tok for tok in ids if tok in patterns]

            flush()

        except Exception:
            logger.exception("Error parsing automation opportunities (fallback text)")

        return opportunities

    def _create_opportunity_from_dict(self, opp_dict: Dict[str, Any]) -> Optional[AutomationOpportunity]:
        """Create AutomationOpportunity from parsed dictionary"""
        try:
            return AutomationOpportunity(
                opportunity_id=f"auto_opp_{uuid4().hex}",
                opportunity_type=str(opp_dict.get("type", "general_automation")),
                description=str(opp_dict.get("description", "Automation opportunity identified")),
                confidence=float(opp_dict.get("confidence", 0.7)),
                frequency=int(opp_dict.get("frequency", 3)),
                potential_time_saved=int(opp_dict.get("time_saved", 10)),
                complexity=str(opp_dict.get("complexity", "medium")).lower(),
                trigger_conditions=opp_dict.get("trigger_conditions"),
                source_pattern_ids=list(opp_dict.get("source_pattern_ids", [])),
            )
        except Exception:
            logger.exception("Error creating opportunity")
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
            # Check if this is a communication analysis belief
            if "total_patterns" in belief.content and "communication_styles_identified" in belief.content:
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
                print(f"Created business insight: {insight.insight_id}")
        
        return analysis_results
    
    async def _execute_automation_identification(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute automation opportunity identification"""
        patterns = parameters.get("patterns", [])
        opportunities_created = 0
        
        # Get observer patterns from context if available
        observer_patterns = {}
        for belief in patterns:
            if hasattr(belief, 'source') and belief.source == "analyzer_agent":
                # This is our own belief, skip it
                continue
            # Try to extract patterns from belief content or context
            if hasattr(belief, 'content') and isinstance(belief.content, dict):
                observer_patterns.update(belief.content)
        
        # If we have access to actual observer patterns, use them
        if hasattr(self, '_current_observer_patterns'):
            observer_patterns = self._current_observer_patterns
        
        # Create opportunities based on patterns
        for pattern_id, pattern in observer_patterns.items():
            if hasattr(pattern, 'frequency') and hasattr(pattern, 'confidence'):
                if pattern.frequency >= self.min_pattern_frequency and pattern.confidence >= self.min_confidence_threshold:
                    
                    if hasattr(pattern, 'pattern_type') and pattern.pattern_type.startswith("comm_"):
                        opportunity = AutomationOpportunity(
                            opportunity_id=f"template_{len(self.automation_opportunities)}",
                            opportunity_type="template_response",
                            description=f"Automate {pattern.pattern_type} responses",
                            confidence=pattern.confidence,
                            frequency=pattern.frequency,
                            potential_time_saved=5,
                            complexity="low"
                        )
                        self.automation_opportunities[opportunity.opportunity_id] = opportunity
                        opportunities_created += 1
                        print(f"Created automation opportunity: {opportunity.opportunity_id}")
                    
                    if hasattr(pattern, 'pattern_type') and ("meeting" in pattern.pattern_type or "schedule" in pattern.pattern_type):
                        opportunity = AutomationOpportunity(
                            opportunity_id=f"meeting_{len(self.automation_opportunities)}",
                            opportunity_type="meeting_scheduling",
                            description=f"Automate meeting scheduling",
                            confidence=pattern.confidence,
                            frequency=pattern.frequency,
                            potential_time_saved=15,
                            complexity="medium"
                        )
                        self.automation_opportunities[opportunity.opportunity_id] = opportunity
                        opportunities_created += 1
                        print(f"Created automation opportunity: {opportunity.opportunity_id}")
        
        return {
            "opportunities_identified": len(self.automation_opportunities),
            "opportunities_created": opportunities_created,
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
    
    def get_business_insights(self, limit: int = 10) -> list:
        """Return a list of business insights found by the Analyzer."""
        return list(self.business_insights.values())[:limit]

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
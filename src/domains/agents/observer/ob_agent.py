"""
Observer Agent for Native IQ - Intelligence Collector
Learns complete communication patterns for automation
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from src.core.base_agent import (
    BaseAgent, 
    Belief, 
    Desire, 
    Intention, 
    BeliefType,
    AgentStatus
)
from langchain_core.messages import BaseMessage


@dataclass
class Pattern:
    """Represents a detected communication pattern"""
    pattern_type: str # email_approval, client_response, vendor_rejection, etc
    triggers: List[str] = field(default_factory=list) # keyword or conditions that trigger the pattern
    typical_response: str = "" # how user typically responds to this pattern
    confidence: float = 0.0 # how confidenct we are about this pattern
    frequency: int = 0 # how often this pattern has been occuring
    last_seen: datetime = field(default_factory=datetime.now) # when was this pattern last seen
    context_clues: Dict[str, Any] = field(default_factory=dict) # additional context about the pattern

@dataclass
class Contact:
    """Represents a contact and relationship"""
    name: str
    email: Optional[str] = None
    relationship: str = "unknown"  # client, vendor, team_member, etc.
    communication_style: str = "formal"  # formal, casual, direct, etc.
    response_priority: str = "normal"  # high, normal, low
    typical_topics: List[str] = field(default_factory=list)
    last_interaction: datetime = field(default_factory=datetime.now)

class ObserverAgent(BaseAgent):
    """
    Observer Agent for Native IQ - Intelligence Collector

    Capabilities:
    1. Full content analysis of communications
    2. Business relationship mapping
    3. Decision pattern recognition
    4. Communication style analysis/learning
    5. Workflow automation opportunities identification
    """
    
    def __init__(self, agent_id: str = "observer_001"):
        super().__init__(
            agent_id=agent_id,
            agent_type="ObserverAgent",
            model_name="gpt-4o",
            temperature=0.1
        )
    
        # intelligence storage
        self.patterns: Dict[str, Pattern] = {}
        self.contacts: Dict[str, Contact] = {}
        self.decision_history: List[Dict[str, Any]] = []
        
        # pattern detection thresholds
        self.pattern_confidence_threshold = 0.7
        self.automation_suggestion_threshold = 0.8

        # initialize core desires
        self._initialize_goals()

        # initialize last activity
        self.last_activity = datetime.now()
    
    def _initialize_goals(self):
        """
        Initialize the core intelligence goals
        """
        core_desires = [
            Desire(
                goal="learn_communication_patterns",
                priority=1,
                conditions={"min_messages": 5}
            ),
            Desire(
                goal="map_relationships", 
                priority=2,
                conditions={"min_contacts": 3}
            ),
            Desire(
                goal="identify_automation_opportunities",
                priority=3,
                conditions={"pattern_confidence": 0.8}
            ),
            Desire(
                goal="understand_decision_context",
                priority=1,
                conditions={"has_decision_data": True}
            )
        ]
        self.desires.extend(core_desires)
    
    async def perceive(
        self, 
        messages: List[BaseMessage], 
        context: Dict[str, Any]
    ) -> List[Belief]:
        """
        Analyze communications and extract intelligence
        Full content analysis for automation
        """
        beliefs = []
        
        for message in messages:
            content = str(message.content)

            # extract communication beliefs
            comm_beliefs = await self._analyze_communication(content, context)
            if comm_beliefs:
                beliefs.append(comm_beliefs)
            
            # extract relationship beliefs
            relationship_belief = await self._analyze_relationships(content, context)
            if relationship_belief:
                beliefs.append(relationship_belief)

            # extract decision pattern belief
            decision_belief = await self._analyze_decision_patterns(content, context)
            if decision_belief:
                beliefs.append(decision_belief)
            
            # extract automation opportunity belief
            automation_belief = await self._identify_automation_opportunities(content, context)
            if automation_belief:
                beliefs.append(automation_belief)
        
        return beliefs 


    async def _analyze_communication(self, content: str, context: Dict[str, Any]) -> Optional[Belief]:
        """Analyze communication style and patterns"""

        # extract communication metadata
        comm_data = {
            "content_length": len(content), # what is the length of the message in characters
            "tone": self._detect_tone(content), # formal, informal, neutral / what tone is the message
            "urgency": self._detect_urgency(content), # high, normal, low / how urgent is the message
            "topics": self._extract_topics(content), # what are the main topics in the message
            "sentiment": self._analyze_sentiment(content), # positive, negative, neutral / what is the sentiment of the message
            "communication_type": context.get("message_type", "unknown"), # email, chat, etc.
            "timestamp": datetime.now().isoformat(), # when was the message sent in ISO format
            "full_content": content  # store full content for business learning
        }

        return Belief(
            type=BeliefType.OBSERVATION,
            content=comm_data,
            confidence=0.9,
            source="communication_analyzer"
        )

    async def _analyze_relationships(
        self, 
        content: str, 
        context: Dict[str, Any]
    ) -> Optional[Belief]:
        """Analyze relationships and contacts"""

        # extract relationship metadata
        contacts = self._extract_contacts(content)

        if not contacts:
            return None
        
        relationship_data = {
            "contacts_mentioned": contacts, # list of contacts mentioned in the message
            "relationship_context": self._infer_relationship_context(content), # inferred relationship context
            "interaction_type": self._classify_interaction(content), # type of interaction
            "power_dynamic": self._analyze_power_dynamic(content), # power dynamic between parties
            "communication_frequency": context.get("frequency", "unknown") # frequency of communication
        }

        return Belief(
            type=BeliefType.PATTERN,
            content=relationship_data,
            confidence=0.9,
            source="relationship_analyzer"
        )
    
    async def _analyze_decision_patterns(
        self, 
        content: str, 
        context: Dict[str, Any]
    ) -> Optional[Belief]:
        """Analyze decision-making patterns"""

        # look for decision indicators
        decision_indicators = [
            "approve", "reject", "accept", "decline", "yes", "no",
            "agree", "disagree", "proceed", "cancel", "postpone",
            "support", "oppose", "endorse", "withdraw", "defer"
        ]  # this is for simple decision making by keywords

        # look for decision patterns
        decisions_found = []
        for indicator in decision_indicators:
            if indicator.lower() in content.lower():
                decisions_found.append({
                    "decision": indicator,
                    "context": self._extract_decision_context(content, indicator),
                    "reasoning": self._extract_reasoning(content, indicator)
                })
        
        if not decisions_found:
            return None
        
        # create decision pattern belief
        decision_data = {
            "decisions": decisions_found,
            "decision_speed": self._analyze_decision_speed(context),
            "factors_considered": self._extract_decision_factors(content),
            "outcome_preference": self._infer_outcome_preference(content)
        }

        return Belief(
            type=BeliefType.KNOWLEDGE,
            content=decision_data,
            confidence=0.85,
            source="decision_analyzer"
        )
    
    async def _identify_automation_opportunities(self, content: str, context: Dict[str, Any]) -> Optional[Belief]:
        """Identify opportunities for business automation"""
        
        # look for repetitive patterns
        automation_signals = [
            "same as last time", "usual response", "standard procedure",
            "as always", "like before", "typical", "routine", 
        ]
        
        # find opportunities for automation
        opportunities = []
        for signal in automation_signals:
            if signal in content.lower():
                opportunities.append({
                    "type": "repetitive_response",
                    "signal": signal,
                    "automation_potential": 0.8,
                    "suggested_action": "create_template_response"
                })
        
        # check for template-able responses
        if self._is_templatable_response(content, context):
            opportunities.append({
                "type": "template_response",
                "template_potential": 0.9,
                "suggested_action": "create_response_template",
                "template_variables": self._extract_template_variables(content)
            })
        
        # return automation opportunities
        if not opportunities:
            return None
        
        # create automation opportunity belief
        automation_data = {
            "opportunities": opportunities,
            "automation_confidence": max([opp.get("automation_potential", 0) for opp in opportunities]),
            "business_impact": self._assess_business_impact(opportunities),
            "implementation_complexity": self._assess_complexity(opportunities)
        }
        
        return Belief(
            type=BeliefType.PATTERN,
            content=automation_data,
            confidence=0.75,
            source="automation_analyzer"
        )

    
    async def update_desires(self, beliefs: List[Belief], context: Dict[str, Any]) -> List[Desire]:
        """Update intelligence goals based on observations"""
        
        updated_desires = self.desires.copy()
        
        # check if we have enough data for advanced analysis
        comm_beliefs = [b for b in beliefs if b.source == "communication_analyzer"]
        decision_beliefs = [b for b in beliefs if b.source == "decision_analyzer"]
        automation_beliefs = [b for b in beliefs if b.source == "automation_analyzer"]
        
        # add desire for pattern consolidation if we have enough data
        if len(comm_beliefs) >= 10:
            updated_desires.append(Desire(
                goal="consolidate_communication_patterns",
                priority=2,
                conditions={"sufficient_data": True}
            ))
        
        # add desire for automation suggestions if patterns are strong
        if automation_beliefs and any(b.confidence > 0.8 for b in automation_beliefs):
            updated_desires.append(Desire(
                goal="generate_automation_suggestions",
                priority=1,
                conditions={"high_confidence_patterns": True}
            ))

        # add desire for decision suggestions if patterns are strong
        if decision_beliefs and any(b.confidence > 0.8 for b in decision_beliefs): # not sure if to keep this or not. 
            updated_desires.append(Desire(
                goal="generate_decision_suggestions",
                priority=1,
                conditions={"high_confidence_patterns": True}
            )) 

        return updated_desires

    

    async def deliberate(
        self, 
        beliefs: List[Belief], 
        desires: List[Desire], 
        current_intentions: List[Intention]
    ) -> List[Intention]:
        """Generate intelligence action plans"""
        
        new_intentions = [] # list of new intentions to be added
        
        # generate intentions based on desires
        for desire in desires:
            if desire.goal == "learn_communication_patterns":
                intention = Intention(
                    desire_id=desire.id,
                    plan=[
                        {"action": "analyze_communication_styles", "status": "pending"},
                        {"action": "update_pattern_database", "status": "pending"},
                        {"action": "calculate_pattern_confidence", "status": "pending"}
                    ]
                )
                new_intentions.append(intention)
            
            elif desire.goal == "identify_automation_opportunities":
                intention = Intention(
                    desire_id=desire.id,
                    plan=[
                        {"action": "scan_for_repetitive_patterns", "status": "pending"},
                        {"action": "assess_automation_potential", "status": "pending"},
                        {"action": "generate_automation_suggestions", "status": "pending"}
                    ]
                )
                new_intentions.append(intention)
            
            elif desire.goal == "map_relationships":
                intention = Intention(
                    desire_id=desire.id,
                    plan=[
                        {"action": "extract_contact_information", "status": "pending"},
                        {"action": "classify_relationships", "status": "pending"},
                        {"action": "update_relationship_graph", "status": "pending"}
                    ]   
                )
                new_intentions.append(intention)
            
            elif desire.goal == "generate_decision_suggestions":
                intention = Intention(
                    desire_id=desire.id,
                    plan=[
                        {"action": "generate_decision_suggestions", "status": "pending"}
                    ]
                )
                new_intentions.append(intention)
        
        return new_intentions 
    
    
    async def act(
        self, 
        intention: Intention, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute intelligence actions"""
        # get next action
        next_action = intention.next_action()
        if not next_action:
            return {"success": False, "reason": "no_action_available"}
        
        action_name = next_action["action"]
        
        # execute action
        try:
            if action_name == "analyze_communication_styles":
                result = await self._execute_communication_analysis()
            elif action_name == "scan_for_repetitive_patterns":
                result = await self._execute_pattern_scanning()
            elif action_name == "generate_automation_suggestions":
                result = await self._execute_automation_suggestions()
            elif action_name == "generate_decision_suggestions":
                result = await self._execute_decision_suggestions()
            elif action_name == "update_relationship_graph":
                result = await self._execute_relationship_mapping()
            else:
                result = {"success": True, "message": f"Executed {action_name}"}
            
            next_action["status"] = "completed"
            return {"success": True, "action": action_name, "result": result}
            
        except Exception as e:
            next_action["status"] = "failed"
            return {"success": False, "action": action_name, "error": str(e)}

    # TODO: implement learn and _detect_tone and _extract_topics

    async def learn(self, beliefs: List[Belief], intentions: List[Intention], context: Dict[str, Any]) -> None:
        """Learn and improve business intelligence capabilities"""
        
        # update pattern confidence based on successful predictions
        completed_intentions = [i for i in intentions if i.status == "completed"]
        
        # learn from communication patterns
        comm_beliefs = [b for b in beliefs if b.source == "communication_analyzer"]
        for belief in comm_beliefs:
            await self._update_communication_patterns(belief.content)
        
        # learn from decision patterns
        decision_beliefs = [b for b in beliefs if b.source == "decision_analyzer"]
        for belief in decision_beliefs:
            await self._update_decision_patterns(belief.content)
        
        # update automation confidence
        automation_beliefs = [b for b in beliefs if b.source == "automation_analyzer"]
        for belief in automation_beliefs:
            await self._update_automation_patterns(belief.content)
        
        print(f"Observer learned from {len(beliefs)} observations and {len(completed_intentions)} actions")
    
    # helper methods for intelligence
    def _detect_tone(self, content: str) -> str:
        """Detect communication tone"""
        formal_indicators = ["dear", "sincerely", "regards", "please find attached", "please find the attached", "please find the following", "please find the enclosed", "i've attached it to this"]
        casual_indicators = ["hey", "thanks", "cool", "awesome", "hi", "hello", "hi there", "hello there"]
        
        formal_count = sum(1 for indicator in formal_indicators if indicator in content.lower())
        casual_count = sum(1 for indicator in casual_indicators if indicator in content.lower())
        
        if formal_count > casual_count:
            return "formal"
        elif casual_count > formal_count:
            return "casual"
        else:
            return "neutral"
    
    def _detect_urgency(self, content: str) -> str:
        """Detect message urgency"""
        urgent_indicators = ["urgent", "asap", "immediately", "emergency", "critical"]
        
        if any(indicator in content.lower() for indicator in urgent_indicators):
            return "high"
        elif "?" in content or "when" in content.lower():
            return "medium"
        else:
            return "low"
    
    def _extract_topics(self, content: str) -> List[str]:
        """Extract main topics from content"""
        # simple keyword extraction - can be enhanced with NLP
        business_keywords = [
            "meeting", "project", "deadline", "budget", "proposal", 
            "contract", "invoice", "payment", "delivery", "schedule",
            "relationship", "contact", "communication", "interaction", "collaboration",
            "decision", "approval", "rejection", "acceptance", "decline", "yes", "no",
            "agree", "disagree", "proceed", "cancel", "postpone", "support", "oppose", "endorse", "withdraw", "defer"
        ]
        
        topics = []
        for keyword in business_keywords:
            if keyword in content.lower():
                topics.append(keyword)
        
        return topics
    
    def _analyze_sentiment(self, content: str) -> str:
        """Analyze message sentiment"""
        positive_words = ["great", "excellent", "good", "pleased", "happy"]
        negative_words = ["problem", "issue", "concern", "disappointed", "frustrated"]
        
        positive_count = sum(1 for word in positive_words if word in content.lower())
        negative_count = sum(1 for word in negative_words if word in content.lower())
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _extract_contacts(self, content: str) -> List[str]:
        """Extract contact names/emails from content"""
        # simple email extraction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        
        # simple name extraction (can be enhanced)
        name_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
            r'\b[A-Z]\. [A-Z][a-z]+\b'       # F. Last
        ]
        
        names = []
        for pattern in name_patterns:
            names.extend(re.findall(pattern, content))
        
        return emails + names
    
    def _is_templatable_response(self, content: str, context: Dict[str, Any]) -> bool:
        """Check if response can be turned into a template"""
        template_indicators = [
            "thank you for", "we will", "please find", "as requested",
            "i am writing to", "following up on"
        ]
        
        return any(indicator in content.lower() for indicator in template_indicators)
    
    def _extract_template_variables(self, content: str) -> List[str]:
        """Extract variables that could be templated"""
        # look for dates, names, amounts, etc.
        variables = []
        
        # date patterns
        if re.search(r'\d{1,2}/\d{1,2}/\d{4}', content):
            variables.append("date")
        
        # amount patterns
        if re.search(r'\$\d+', content):
            variables.append("amount")
        
        # name patterns
        if re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', content):
            variables.append("name")
        
        return variables
    
    # execution methods
    async def _execute_communication_analysis(self) -> Dict[str, Any]:
        """Execute communication style analysis"""
        return {
            "patterns_analyzed": len(self.patterns),
            "communication_styles_identified": 3,
            "confidence_improvement": 0.1
        }
    
    async def _execute_pattern_scanning(self) -> Dict[str, Any]:
        """Execute pattern scanning for automation opportunities"""
        return {
            "patterns_scanned": len(self.beliefs),
            "automation_opportunities": 2,
            "potential_time_savings": "2 hours/week"
        }
    
    async def _execute_automation_suggestions(self) -> Dict[str, Any]:
        """Generate automation suggestions"""
        suggestions = [
            {
                "type": "template_response",
                "description": "Create template for vendor rejection emails",
                "confidence": 0.9,
                "time_savings": "30 minutes/week"
            },
            {
                "type": "auto_scheduling",
                "description": "Automatically suggest meeting times based on patterns",
                "confidence": 0.8,
                "time_savings": "1 hour/week"
            }
        ]
        
        return {
            "suggestions": suggestions,
            "total_suggestions": len(suggestions),
            "estimated_savings": "1.5 hours/week"
        }
    
    async def _execute_relationship_mapping(self) -> Dict[str, Any]:
        """Execute relationship mapping"""
        return {
            "contacts_mapped": len(self.contacts),
            "relationships_classified": 5,
            "communication_preferences_learned": 3
        }

    async def _execute_decision_suggestions(self) -> Dict[str, Any]:
        """Execute decision suggestions"""
        return {
            "suggestions": [],
            "total_suggestions": 0,
            "estimated_savings": "0 hours/week"
        }

    # Learning methods --->
    async def _update_communication_patterns(self, content: Dict[str, Any]) -> None:
        """Update communication pattern knowledge"""
        try:
            # extract pattern key from communication data
            tone = content.get("tone", "neutral")
            communication_type = content.get("communication_type", "unknown")
            topics = content.get("topics", [])
            
            # create pattern key
            pattern_key = f"comm_{tone}_{communication_type}"
            
            # update or create communication pattern
            if pattern_key in self.patterns:
                # update existing pattern
                pattern = self.patterns[pattern_key]
                pattern.frequency += 1
                pattern.last_seen = datetime.now()
                
                # update confidence based on frequency
                pattern.confidence = min(0.95, pattern.confidence + 0.05)
                
                # update triggers with new topics
                for topic in topics:
                    if topic not in pattern.triggers:
                        pattern.triggers.append(topic)
                
                # update context clues
                pattern.context_clues.update({
                    "avg_length": (pattern.context_clues.get("avg_length", 0) + content.get("content_length", 0)) / 2,
                    "common_sentiment": content.get("sentiment", "neutral"),
                    "urgency_level": content.get("urgency", "low")
                })
                
            else:
                # create new communication pattern
                new_pattern = Pattern(
                    pattern_type=f"communication_{tone}_{communication_type}",
                    triggers=topics,
                    typical_response=f"Typical {tone} {communication_type} response",
                    confidence=0.3,  # start with low confidence
                    frequency=1,
                    last_seen=datetime.now(),
                    context_clues={
                        "tone": tone,
                        "type": communication_type,
                        "avg_length": content.get("content_length", 0),
                        "sentiment": content.get("sentiment", "neutral"),
                        "urgency": content.get("urgency", "low")
                    }
                )
                self.patterns[pattern_key] = new_pattern
            
            print(f"Updated communication pattern: {pattern_key}")
            
        except Exception as e:
            print(f"Error updating communication patterns: {e}")
    
    async def _update_decision_patterns(self, content: Dict[str, Any]) -> None:
        """Update decision pattern knowledge"""
        try:
            decisions = content.get("decisions", [])
            
            for decision_data in decisions:
                decision = decision_data.get("decision", "unknown")
                context = decision_data.get("context", "")
                reasoning = decision_data.get("reasoning", "")
                
                # create pattern key for this decision type
                pattern_key = f"decision_{decision.lower()}"
                
                if pattern_key in self.patterns:
                    # update existing decision pattern
                    pattern = self.patterns[pattern_key]
                    pattern.frequency += 1
                    pattern.last_seen = datetime.now()
                    
                    # Increase confidence with more examples
                    pattern.confidence = min(0.95, pattern.confidence + 0.1)
                    
                    # Update typical response based on reasoning
                    if reasoning and reasoning not in pattern.typical_response:
                        pattern.typical_response += f" | {reasoning}"
                    
                    # Update context clues
                    pattern.context_clues.update({
                        "decision_speed": content.get("decision_speed", "medium"),
                        "factors": content.get("factors_considered", []),
                        "outcome_preference": content.get("outcome_preference", "efficiency"),
                        "recent_context": context
                    })
                    
                else:
                    # create new decision pattern
                    new_pattern = Pattern(
                        pattern_type=f"decision_{decision.lower()}",
                        triggers=[decision.lower()],
                        typical_response=reasoning or f"Standard {decision} response",
                        confidence=0.4,  # start with moderate confidence for decisions
                        frequency=1,
                        last_seen=datetime.now(),
                        context_clues={
                            "decision_type": decision,
                            "decision_speed": content.get("decision_speed", "medium"),
                            "factors": content.get("factors_considered", []),
                            "outcome_preference": content.get("outcome_preference", "efficiency"),
                            "context": context,
                            "reasoning": reasoning
                        }
                    )
                    self.patterns[pattern_key] = new_pattern
                
                # store in decision history for trend analysis
                self.decision_history.append({
                    "decision": decision,
                    "context": context,
                    "reasoning": reasoning,
                    "timestamp": datetime.now().isoformat(),
                    "confidence": self.patterns[pattern_key].confidence
                })
            
            print(f"Updated decision patterns for {len(decisions)} decisions")
            
        except Exception as e:
            print(f"Error updating decision patterns: {e}")

    
    async def _update_automation_patterns(self, content: Dict[str, Any]) -> None:
        """Update automation pattern knowledge"""
        try:
            opportunities = content.get("opportunities", [])
            
            for opportunity in opportunities:
                opp_type = opportunity.get("type", "unknown")
                automation_potential = opportunity.get("automation_potential", 0.0)
                suggested_action = opportunity.get("suggested_action", "")
                
                # create pattern key for automation opportunity
                pattern_key = f"automation_{opp_type}"
                
                if pattern_key in self.patterns:
                    # update existing automation pattern
                    pattern = self.patterns[pattern_key]
                    pattern.frequency += 1
                    pattern.last_seen = datetime.now()
                    
                    # update confidence based on automation potential
                    new_confidence = (pattern.confidence + automation_potential) / 2
                    pattern.confidence = min(0.95, new_confidence)
                    
                    # update typical response with suggested action
                    if suggested_action and suggested_action not in pattern.typical_response:
                        pattern.typical_response = suggested_action
                    
                    # update context clues
                    pattern.context_clues.update({
                        "automation_potential": automation_potential,
                        "business_impact": content.get("business_impact", "medium"),
                        "implementation_complexity": content.get("implementation_complexity", "low"),
                        "suggested_action": suggested_action,
                        "automation_confidence": content.get("automation_confidence", 0.0)
                    })
                    
                else:
                    # create new automation pattern
                    new_pattern = Pattern(
                        pattern_type=f"automation_{opp_type}",
                        triggers=[opp_type],
                        typical_response=suggested_action,
                        confidence=automation_potential,
                        frequency=1,
                        last_seen=datetime.now(),
                        context_clues={
                            "opportunity_type": opp_type,
                            "automation_potential": automation_potential,
                            "business_impact": content.get("business_impact", "medium"),
                            "implementation_complexity": content.get("implementation_complexity", "low"),
                            "suggested_action": suggested_action,
                            "automation_confidence": content.get("automation_confidence", 0.0)
                        }
                    )
                    self.patterns[pattern_key] = new_pattern
            
            # clean up low-confidence automation patterns (below threshold)
            patterns_to_remove = []
            for key, pattern in self.patterns.items():
                if (key.startswith("automation_") and 
                    pattern.confidence < self.automation_suggestion_threshold and 
                    pattern.frequency < 3):
                    patterns_to_remove.append(key)
            
            for key in patterns_to_remove:
                del self.patterns[key]
                print(f"🗑️  Removed low-confidence automation pattern: {key}")
            
            print(f"Updated automation patterns for {len(opportunities)} opportunities")
            
        except Exception as e:
            print(f"Error updating automation patterns: {e}")
    
    # additional helper methods
    def _infer_relationship_context(self, content: str) -> str:
        """Infer the business relationship context"""
        return "professional"
    
    def _classify_interaction(self, content: str) -> str:
        """Classify the type of business interaction"""
        return "email_communication"
    
    def _analyze_power_dynamic(self, content: str) -> str:
        """Analyze power dynamics in communication"""
        return "equal"
    
    def _extract_decision_context(self, content: str, decision: str) -> str:
        """Extract context around a decision"""
        return f"Context for {decision}"
    
    def _extract_reasoning(self, content: str, decision: str) -> str:
        """Extract reasoning behind a decision"""
        return f"Reasoning for {decision}"
    
    def _analyze_decision_speed(self, context: Dict[str, Any]) -> str:
        """Analyze how quickly decisions are made"""
        return "medium"
    
    def _extract_decision_factors(self, content: str) -> List[str]:
        """Extract factors that influence decisions"""
        return ["cost", "timeline", "quality"]
    
    def _infer_outcome_preference(self, content: str) -> str:
        """Infer preferred outcomes"""
        return "efficiency"
    
    def _assess_business_impact(self, opportunities: List[Dict[str, Any]]) -> str:
        """Assess business impact of automation opportunities"""
        return "medium"
    
    def _assess_complexity(self, opportunities: List[Dict[str, Any]]) -> str:
        """Assess implementation complexity"""
        return "low"
    
    def get_intelligence_summary(self) -> Dict[str, Any]:
        """Get a summary of learned business intelligence"""
        return {
            "agent_id": self.agent_id,
            "patterns_learned": len(self.patterns),
            "contacts_mapped": len(self.contacts),
            "decisions_analyzed": len(self.decision_history),
            "automation_opportunities": len([p for p in self.patterns.values() if p.confidence > 0.8]),
            "learning_confidence": sum(p.confidence for p in self.patterns.values()) / max(len(self.patterns), 1),
            "last_activity": self.last_activity.isoformat()
        }
"""
Test file for Observer Agent - Business Intelligence Testing
Comprehensive test suite for ObserverAgent functionality
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Observer Agent components
try:
    from src.domains.agents.observer.ob_agent import ObserverAgent, Pattern, Contact
    from src.core.base_agent import Belief, Desire, Intention, BeliefType
    from langchain_core.messages import HumanMessage
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure to implement the missing components first")
    IMPORTS_AVAILABLE = False


class ObserverAgentTest:
    """Comprehensive test suite for Observer Agent"""
    
    def __init__(self):
        self.test_messages = [
            "Hi John, I've reviewed the vendor proposal and I'm rejecting it due to budget constraints. Please send them our standard rejection email.",
            "Thanks for the meeting request. I approve this and let's schedule it for next Friday at 2 PM.",
            "Following up on our conversation yesterday - when can we expect the project deliverables?",
            "I disagree with this approach. Let's postpone the decision until we have more data.",
            "Great work on the presentation! I'm pleased with the results and we should proceed with implementation.",
            "This is urgent - we need to cancel the vendor contract immediately due to compliance issues.",
            "As always, please use the standard template for client communications.",
            "Same as last time, I'll need the usual budget report by end of week.",
        ]
        
        self.test_contexts = [
            {"message_type": "email", "sender": "boss@company.com", "priority": "normal", "frequency": "weekly"},
            {"message_type": "slack", "sender": "team_lead", "priority": "high", "frequency": "daily"},
            {"message_type": "email", "sender": "client@business.com", "priority": "high", "frequency": "monthly"},
            {"message_type": "email", "sender": "vendor@supplier.com", "priority": "low", "frequency": "quarterly"},
            {"message_type": "teams", "sender": "team_member", "priority": "normal", "frequency": "weekly"},
            {"message_type": "email", "sender": "compliance@company.com", "priority": "high", "frequency": "rarely"},
            {"message_type": "email", "sender": "assistant@company.com", "priority": "low", "frequency": "daily"},
            {"message_type": "slack", "sender": "manager@company.com", "priority": "normal", "frequency": "weekly"},
        ]
    
    async def test_observer_initialization(self):
        """Test Observer Agent creation and initialization"""
        print("Testing Observer Agent Initialization")
        print("-" * 50)
        
        try:
            observer = ObserverAgent(agent_id="test_observer_001")
            
            print(f"Agent created successfully")
            print(f"Agent ID: {observer.agent_id}")
            print(f"Agent Type: {observer.agent_type}")
            print(f"Initial patterns: {len(observer.patterns)}")
            print(f"Initial contacts: {len(observer.contacts)}")
            print(f"Initial desires: {len(observer.desires)}")
            print(f"Pattern confidence threshold: {observer.pattern_confidence_threshold}")
            print(f"Automation suggestion threshold: {observer.automation_suggestion_threshold}")
            
            status = observer.get_status()
            print(f"Initial status: {status}")
            
            return observer
            
        except Exception as e:
            print(f"Observer creation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def test_communication_analysis(self, observer: ObserverAgent):
        """Test communication analysis capabilities"""
        print("\nTesting Communication Analysis")
        print("-" * 40)
        
        try:
            for i, (message, context) in enumerate(zip(self.test_messages[:3], self.test_contexts[:3])):
                print(f"\nProcessing message {i+1}:")
                print(f"Content: {message[:60]}...")
                print(f"Context: {context}")
                
                # Test individual analysis methods
                comm_belief = await observer._analyze_communication(message, context)
                if comm_belief:
                    print("Communication analysis successful")
                    print(f"  Tone: {comm_belief.content.get('tone')}")
                    print(f"  Urgency: {comm_belief.content.get('urgency')}")
                    print(f"  Topics: {comm_belief.content.get('topics')}")
                    print(f"  Sentiment: {comm_belief.content.get('sentiment')}")
                    print(f"  Confidence: {comm_belief.confidence}")
                else:
                    print("Communication analysis returned None")
                    
        except Exception as e:
            print(f"Communication analysis test failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_decision_pattern_analysis(self, observer: ObserverAgent):
        """Test decision pattern recognition"""
        print("\nTesting Decision Pattern Analysis")
        print("-" * 40)
        
        decision_messages = [
            "I approve this proposal and we should proceed immediately.",
            "I'm rejecting this vendor due to high costs.",
            "I disagree with this approach, let's postpone the decision.",
            "Yes, I support this initiative.",
            "No, I oppose this change."
        ]
        
        try:
            for i, message in enumerate(decision_messages):
                print(f"\nAnalyzing decision message {i+1}: {message}")
                
                decision_belief = await observer._analyze_decision_patterns(message, {"message_type": "email"})
                if decision_belief:
                    decisions = decision_belief.content.get('decisions', [])
                    print(f"Found {len(decisions)} decisions:")
                    for decision in decisions:
                        print(f"  Decision: {decision.get('decision')}")
                        print(f"  Context: {decision.get('context')}")
                        print(f"  Reasoning: {decision.get('reasoning')}")
                else:
                    print("No decisions detected")
                    
        except Exception as e:
            print(f"Decision pattern analysis test failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_automation_opportunity_detection(self, observer: ObserverAgent):
        """Test automation opportunity identification"""
        print("\nTesting Automation Opportunity Detection")
        print("-" * 45)
        
        automation_messages = [
            "As always, please send the standard rejection email to the vendor.",
            "Same as last time, I'll need the usual weekly report.",
            "Please find attached the typical response template.",
            "Following up on our conversation, I am writing to confirm the meeting."
        ]
        
        try:
            for i, message in enumerate(automation_messages):
                print(f"\nAnalyzing automation message {i+1}: {message}")
                
                automation_belief = await observer._identify_automation_opportunities(message, {"message_type": "email"})
                if automation_belief:
                    opportunities = automation_belief.content.get('opportunities', [])
                    print(f"Found {len(opportunities)} automation opportunities:")
                    for opp in opportunities:
                        print(f"  Type: {opp.get('type')}")
                        print(f"  Potential: {opp.get('automation_potential', 0)}")
                        print(f"  Suggested action: {opp.get('suggested_action')}")
                else:
                    print("No automation opportunities detected")
                    
        except Exception as e:
            print(f"Automation opportunity detection test failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_relationship_analysis(self, observer: ObserverAgent):
        """Test relationship and contact analysis"""
        print("\nTesting Relationship Analysis")
        print("-" * 35)
        
        relationship_messages = [
            "Hi John Smith, thanks for your email about the project. Please contact mary.johnson@company.com for details.",
            "Following up with Dr. Wilson and sarah@vendor.com regarding the contract.",
            "Meeting with CEO tomorrow, also invite team@department.com to the discussion."
        ]
        
        try:
            for i, message in enumerate(relationship_messages):
                print(f"\nAnalyzing relationship message {i+1}: {message[:50]}...")
                
                relationship_belief = await observer._analyze_relationships(message, {"message_type": "email"})
                if relationship_belief:
                    contacts = relationship_belief.content.get('contacts_mentioned', [])
                    print(f"Found {len(contacts)} contacts: {contacts}")
                    print(f"Interaction type: {relationship_belief.content.get('interaction_type')}")
                    print(f"Relationship context: {relationship_belief.content.get('relationship_context')}")
                else:
                    print("No relationships detected")
                    
        except Exception as e:
            print(f"Relationship analysis test failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_full_perception_cycle(self, observer: ObserverAgent):
        """Test the complete perception cycle"""
        print("\nTesting Full Perception Cycle")
        print("-" * 35)
        
        try:
            test_message = "Hi John, I've reviewed the vendor proposal and I'm rejecting it due to budget constraints. As always, please send them our standard rejection email."
            context = {"message_type": "email", "sender": "boss@company.com", "priority": "normal"}
            
            print(f"Processing complete message: {test_message}")
            print(f"Context: {context}")
            
            human_msg = HumanMessage(content=test_message)
            beliefs = await observer.perceive([human_msg], context)
            
            print(f"\nGenerated {len(beliefs)} beliefs:")
            for i, belief in enumerate(beliefs):
                print(f"  Belief {i+1}:")
                print(f"    Type: {belief.type.value}")
                print(f"    Source: {belief.source}")
                print(f"    Confidence: {belief.confidence}")
                print(f"    Content keys: {list(belief.content.keys())}")
                
        except Exception as e:
            print(f"Full perception cycle test failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_learning_capabilities(self, observer: ObserverAgent):
        """Test learning and pattern updating"""
        print("\nTesting Learning Capabilities")
        print("-" * 35)
        
        try:
            # Create test beliefs for learning
            comm_belief = Belief(
                type=BeliefType.OBSERVATION,
                content={
                    "tone": "formal",
                    "communication_type": "email",
                    "topics": ["meeting", "project"],
                    "sentiment": "positive",
                    "urgency": "medium",
                    "content_length": 150
                },
                confidence=0.9,
                source="communication_analyzer"
            )
            
            decision_belief = Belief(
                type=BeliefType.KNOWLEDGE,
                content={
                    "decisions": [
                        {
                            "decision": "approve",
                            "context": "project proposal",
                            "reasoning": "meets budget requirements"
                        }
                    ],
                    "decision_speed": "fast",
                    "factors_considered": ["budget", "timeline"],
                    "outcome_preference": "efficiency"
                },
                confidence=0.85,
                source="decision_analyzer"
            )
            
            automation_belief = Belief(
                type=BeliefType.PATTERN,
                content={
                    "opportunities": [
                        {
                            "type": "template_response",
                            "automation_potential": 0.9,
                            "suggested_action": "create_email_template"
                        }
                    ],
                    "automation_confidence": 0.9,
                    "business_impact": "high",
                    "implementation_complexity": "low"
                },
                confidence=0.8,
                source="automation_analyzer"
            )
            
            beliefs = [comm_belief, decision_belief, automation_belief]
            intentions = []  # Empty for this test
            context = {"test": True}
            
            print("Testing learning with sample beliefs...")
            initial_patterns = len(observer.patterns)
            
            await observer.learn(beliefs, intentions, context)
            
            final_patterns = len(observer.patterns)
            print(f"Patterns before learning: {initial_patterns}")
            print(f"Patterns after learning: {final_patterns}")
            print(f"New patterns learned: {final_patterns - initial_patterns}")
            
            # Test pattern analysis
            if hasattr(observer, '_analyze_pattern_trends'):
                trends = observer._analyze_pattern_trends()
                print(f"Pattern trends: {trends}")
                
        except Exception as e:
            print(f"Learning capabilities test failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_bdi_cycle(self, observer: ObserverAgent):
        """Test the complete BDI processing cycle"""
        print("\nTesting Complete BDI Cycle")
        print("-" * 30)
        
        try:
            test_input = {
                "message": "I approve this vendor proposal. Please proceed with the contract and send them our standard approval email template.",
                "context": {
                    "message_type": "email",
                    "sender": "ceo@company.com",
                    "priority": "high",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            print("Processing business scenario:")
            print(f"Message: {test_input['message']}")
            print(f"Context: {test_input['context']}")
            
            initial_status = observer.get_status()
            print("\nInitial agent status:")
            for key, value in initial_status.items():
                print(f"  {key}: {value}")
            
            # Run full BDI cycle
            result = await observer.process(test_input, test_input["context"])
            
            print("\nBDI cycle completed successfully")
            print("Processing result:")
            for key, value in result.items():
                if key != "result":  # Don't print the full result object
                    print(f"  {key}: {value}")
            
            final_status = observer.get_status()
            print("\nFinal agent status:")
            for key, value in final_status.items():
                print(f"  {key}: {value}")
            
            # Get intelligence summary
            if hasattr(observer, 'get_intelligence_summary'):
                summary = observer.get_intelligence_summary()
                print("\nIntelligence summary:")
                for key, value in summary.items():
                    print(f"  {key}: {value}")
                
        except Exception as e:
            print(f"BDI cycle test failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_helper_methods(self, observer: ObserverAgent):
        """Test helper methods for analysis"""
        print("\nTesting Helper Methods")
        print("-" * 25)
        
        test_content = "Hi John Smith, thanks for your urgent email about the meeting project. I'm pleased with the proposal and approve proceeding. Please find attached the contract dated 12/25/2024 for $50,000."
        
        try:
            print(f"Testing with content: {test_content[:60]}...")
            
            # Test tone detection
            tone = observer._detect_tone(test_content)
            print(f"Detected tone: {tone}")
            
            # Test urgency detection
            urgency = observer._detect_urgency(test_content)
            print(f"Detected urgency: {urgency}")
            
            # Test topic extraction
            topics = observer._extract_topics(test_content)
            print(f"Extracted topics: {topics}")
            
            # Test sentiment analysis
            sentiment = observer._analyze_sentiment(test_content)
            print(f"Analyzed sentiment: {sentiment}")
            
            # Test contact extraction
            contacts = observer._extract_contacts(test_content)
            print(f"Extracted contacts: {contacts}")
            
            # Test template detection
            is_templatable = observer._is_templatable_response(test_content, {})
            print(f"Is templatable: {is_templatable}")
            
            # Test template variables
            variables = observer._extract_template_variables(test_content)
            print(f"Template variables: {variables}")
            
        except Exception as e:
            print(f"Helper methods test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_environment_setup():
    """Test environment and dependencies"""
    print("Testing Environment Setup")
    print("-" * 30)
    
    # Test API keys
    api_keys = ["OPENAI_API_KEY", "LANGSMITH_API_KEY"]
    for key in api_keys:
        if os.environ.get(key):
            print(f"{key} is configured")
        else:
            print(f"{key} not found (may be optional)")
    
    # Test database configurations
    db_configs = [
        ("NEO4J_URI", "Neo4j Knowledge Graph"),
        ("MILVUS_HOST", "Milvus Vector DB"),
    ]
    
    for env_var, db_name in db_configs:
        if os.environ.get(env_var):
            print(f"{db_name} configuration found")
        else:
            print(f"{db_name} configuration missing")


async def main():
    """Main test runner"""
    print("DELA AI - Observer Agent Comprehensive Testing")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print()
    
    if not IMPORTS_AVAILABLE:
        print("Cannot run tests - missing imports")
        print("Please implement the Observer Agent first")
        return
    
    # Test environment
    await test_environment_setup()
    print()
    
    # Initialize test suite
    test_suite = ObserverAgentTest()
    
    # Create observer agent
    observer = await test_suite.test_observer_initialization()
    if not observer:
        print("Cannot continue - Observer creation failed")
        return
    
    # Run comprehensive tests
    await test_suite.test_communication_analysis(observer)
    await test_suite.test_decision_pattern_analysis(observer)
    await test_suite.test_automation_opportunity_detection(observer)
    await test_suite.test_relationship_analysis(observer)
    await test_suite.test_full_perception_cycle(observer)
    await test_suite.test_learning_capabilities(observer)
    await test_suite.test_bdi_cycle(observer)
    await test_suite.test_helper_methods(observer)
    
    print("\nTesting completed successfully!")
    print("=" * 60)
    
    # Final comprehensive summary
    print("Final Observer Agent Summary:")
    final_status = observer.get_status()
    for key, value in final_status.items():
        print(f"  {key}: {value}")
    
    if hasattr(observer, 'get_intelligence_summary'):
        intelligence_summary = observer.get_intelligence_summary()
        print("\nFinal Intelligence Summary:")
        for key, value in intelligence_summary.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTesting interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
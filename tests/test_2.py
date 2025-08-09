"""
Advanced Integration Test for Native IQ System
Tests Observer → Analyzer → Decision → Execution → Calendar Tool with Complex Scenarios
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Native IQ imports
from src.domains.agents.observer.ob_agent import ObserverAgent
from src.domains.agents.analyzer.analyzer_agent import AnalyzerAgent
from src.domains.agents.decision.decision_agent import DecisionAgent
from src.domains.agents.execution.execution_agent import ExecutionAgent
from src.domains.tools.calandar_tool import get_calendar_tools, schedule_meeting, find_free_slots

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NativeAdvancedIntegrationTest:
    """Advanced Native IQ integration test with complete 4-agent workflow"""

    def __init__(self):
        self.observer_agent = None
        self.analyzer_agent = None
        self.decision_agent = None
        self.execution_agent = None
        self.calendar_tools = get_calendar_tools()
        self.test_results = {}

        # Complex, cross-domain business scenarios
        self.test_messages = [
            {
                "message": (
                    "Hi team, please generate and send the weekly sales report to all regional managers by Friday noon. "
                    "Automate the data pull from Salesforce and schedule an email with the attached PDF. "
                    "Also, set a recurring calendar event for every Friday 10am to review the report."
                ),
                "sender": "alice@company.com",
                "context": {"message_type": "report_request", "automation_hint": "reporting, email, scheduling"}
            },
            {
                "message": (
                    "Reminder: All project leads must submit their timesheets by 5pm today. "
                    "Can we automate a reminder system that sends notifications 2 hours before deadline?"
                ),
                "sender": "hr@company.com", 
                "context": {"message_type": "reminder", "automation_hint": "notifications, deadlines"}
            },
            {
                "message": (
                    "Client onboarding for Acme Corp is scheduled for next Monday at 2pm. "
                    "Please prepare the welcome package and schedule follow-up meetings for weeks 2 and 4."
                ),
                "sender": "sales@company.com",
                "context": {"message_type": "onboarding", "automation_hint": "scheduling, client management"}
            },
            {
                "message": (
                    "Can we set up an automated workflow to track overdue invoices? "
                    "Send payment reminders at 30, 60, and 90 days past due."
                ),
                "sender": "finance@company.com",
                "context": {"message_type": "finance_automation", "automation_hint": "invoicing, reminders"}
            },
            {
                "message": (
                    "Monthly IT maintenance is next Wednesday. Automate sending notifications "
                    "to all users 48 hours and 2 hours before the maintenance window."
                ),
                "sender": "it@company.com",
                "context": {"message_type": "maintenance", "automation_hint": "notifications, scheduling"}
            },
            {
                "message": (
                    "For our Q3 planning, please automate the collection of project status reports "
                    "from all team leads and compile them into a master dashboard."
                ),
                "sender": "management@company.com",
                "context": {"message_type": "planning", "automation_hint": "reporting, data collection"}
            },
            {
                "message": (
                    "Can we automate the process of gathering customer feedback after support tickets are closed? "
                    "Send a survey 24 hours after resolution."
                ),
                "sender": "support@company.com",
                "context": {"message_type": "customer_feedback", "automation_hint": "surveys, follow-up"}
            },
            {
                "message": (
                    "Schedule a recurring executive meeting every first Monday of the month at 9am. "
                    "Include agenda preparation and pre-meeting document sharing automation."
                ),
                "sender": "executive@company.com",
                "context": {"message_type": "meeting", "automation_hint": "scheduling, document management"}
            },
            {
                "message": (
                    "Whenever a deal is marked as closed-won in Salesforce, automatically schedule "
                    "a kickoff meeting with the implementation team within 48 hours."
                ),
                "sender": "sales@company.com",
                "context": {"message_type": "deal_closure", "automation_hint": "CRM integration, scheduling"}
            },
            {
                "message": (
                    "Automate the weekly backup of all shared drive folders and send confirmation "
                    "emails to IT administrators with backup status reports."
                ),
                "sender": "it@company.com",
                "context": {"message_type": "backup", "automation_hint": "data management, reporting"}
            }
        ]

    async def setup_agents(self):
        """Initialize all 4 agents"""
        try:
            print("🤖 Initializing Native IQ 4-Agent System...")
            
            # Initialize Observer Agent
            self.observer_agent = ObserverAgent(agent_id="advanced_observer_001")
            print(f"✅ Observer Agent initialized: {self.observer_agent.agent_id}")
            
            # Initialize Analyzer Agent
            self.analyzer_agent = AnalyzerAgent(agent_id="advanced_analyzer_001")
            print(f"✅ Analyzer Agent initialized: {self.analyzer_agent.agent_id}")
            
            # Initialize Decision Agent
            self.decision_agent = DecisionAgent(agent_id="advanced_decision_001")
            print(f"✅ Decision Agent initialized: {self.decision_agent.agent_id}")
            
            # Initialize Execution Agent
            self.execution_agent = ExecutionAgent(agent_id="advanced_execution_001")
            self.execution_agent.set_calendar_tools(self.calendar_tools)
            print(f"✅ Execution Agent initialized: {self.execution_agent.agent_id}")
            
            print(f"✅ Calendar tools loaded: {len(self.calendar_tools)} tools available")
            
        except Exception as e:
            logger.error(f"Error setting up agents: {e}")
            raise

    async def test_automation_detection(self):
        """Test automation opportunity detection across all agents"""
        print("\n🔍 Testing 4-Agent Automation Detection Pipeline...")
        
        try:
            # Step 1: Observer learns from messages
            observer_patterns = {}
            observer_contacts = {}
            
            for i, msg_data in enumerate(self.test_messages, 1):
                print(f"  Processing message {i}: {msg_data['message'][:60]}...")
                
                result = await self.observer_agent.process(
                    [msg_data['message']], 
                    context={
                        "sender": msg_data['sender'],
                        "timestamp": datetime.now(),
                        **msg_data['context']
                    }
                )
                
                observer_patterns.update(self.observer_agent.patterns)
                observer_contacts.update(self.observer_agent.contacts)
                print(f"    ✅ Learned {result['beliefs_count']} patterns")

            print(f"  Observer patterns learned: {len(observer_patterns)}")
            print(f"  Observer contacts mapped: {len(observer_contacts)}")

            # Step 2: Analyzer processes Observer data
            # Store observer patterns for automation identification
            self.analyzer_agent._current_observer_patterns = observer_patterns
            
            analyzer_beliefs = await self.analyzer_agent.perceive(
                messages=[],
                context={
                    "observer_patterns": observer_patterns,
                    "observer_contacts": observer_contacts
                }
            )

            # Execute Analyzer actions using BDI workflow
            analyzer_desires = await self.analyzer_agent.update_desires(analyzer_beliefs, {
                "observer_patterns": observer_patterns,
                "observer_contacts": observer_contacts
            })
            analyzer_intentions = await self.analyzer_agent.deliberate(analyzer_beliefs, analyzer_desires, [])
            
            for intention in analyzer_intentions:
                await self.analyzer_agent.act(intention, {
                    "observer_patterns": observer_patterns,
                    "observer_contacts": observer_contacts
                })
            
            await self.analyzer_agent.learn(analyzer_beliefs, analyzer_intentions, {
                "observer_patterns": observer_patterns,
                "observer_contacts": observer_contacts
            })

            # Step 3: Decision Agent processes Analyzer insights
            decision_context = {
                "automation_opportunities": list(self.analyzer_agent.automation_opportunities.values()),
                "business_insights": list(self.analyzer_agent.business_insights.values()),
                "analyzer_opportunities": list(self.analyzer_agent.automation_opportunities.values()),
                "analyzer_insights": list(self.analyzer_agent.business_insights.values())
            }

            decision_beliefs = await self.decision_agent.perceive(
                message={},
                context=decision_context
            )

            # Execute Decision actions using BDI workflow
            decision_desires = await self.decision_agent.update_desires(decision_beliefs, decision_context)
            decision_intentions = await self.decision_agent.deliberate(decision_beliefs, decision_desires, [])
            
            for intention in decision_intentions:
                await self.decision_agent.act(intention, decision_context)
            
            await self.decision_agent.learn(decision_beliefs, decision_intentions, decision_context)

            # Step 4: Execution Agent processes approved decisions
            approved_decisions = [d for d in self.decision_agent.decisions.values() 
                                if d.decision_type == "approve"]

            print(f"  DEBUG: Found {len(approved_decisions)} approved decisions")
            for i, decision in enumerate(approved_decisions):
                print(f"    Decision {i+1}: {decision.decision_id} - {decision.decision_type}")

            execution_context = {
                "approved_decisions": approved_decisions,
                "automation_opportunities": list(self.analyzer_agent.automation_opportunities.values())
            }

            execution_beliefs = await self.execution_agent.perceive(
                messages=[],
                context=execution_context
            )

            print(f"  DEBUG: ExecutionAgent perceived {len(execution_beliefs)} beliefs")
            for i, belief in enumerate(execution_beliefs):
                print(f"    Belief {i+1}: {belief.id} - source: {belief.source}")

            # Execute automation tasks using BDI workflow
            execution_desires = await self.execution_agent.update_desires(execution_beliefs, execution_context)
            print(f"  DEBUG: ExecutionAgent has {len(execution_desires)} desires")
            
            execution_intentions = await self.execution_agent.deliberate(execution_beliefs, execution_desires, [])
            print(f"  DEBUG: ExecutionAgent created {len(execution_intentions)} intentions")
            
            # ExecutionAgent.act() takes a list of intentions
            execution_results = await self.execution_agent.act(execution_intentions)
            
            print(f"  DEBUG: ExecutionAgent results: {execution_results}")
            
            await self.execution_agent.learn(execution_beliefs, execution_context)

            # Collect results
            analyzer_summary = {
                "automation_opportunities": len(self.analyzer_agent.automation_opportunities),
                "business_insights": len(self.analyzer_agent.business_insights),
                "high_confidence_opportunities": len([op for op in self.analyzer_agent.automation_opportunities.values() 
                                                    if op.confidence > 0.7]),
                "time_savings_potential": sum([op.potential_time_saved for op in self.analyzer_agent.automation_opportunities.values()])
            }

            decision_summary = self.decision_agent.get_decision_summary()
            execution_summary = self.execution_agent.get_execution_summary()

            print(f"\n📊 Analyzer Intelligence Summary:")
            print(f"  Automation opportunities: {analyzer_summary['automation_opportunities']}")
            print(f"  Business insights: {analyzer_summary['business_insights']}")
            print(f"  High confidence opportunities: {analyzer_summary['high_confidence_opportunities']}")
            print(f"  Time savings potential: {analyzer_summary['time_savings_potential']} minutes")

            print(f"\n🧠 Decision Intelligence Summary:")
            print(f"  Total decisions: {decision_summary['total_decisions']}")
            print(f"  Approved decisions: {decision_summary['approved_decisions']}")
            print(f"  Rejected decisions: {decision_summary['rejected_decisions']}")
            print(f"  Total expected ROI: {decision_summary['total_expected_roi']:.1f}x")

            print(f"\n⚡ Execution Performance Summary:")
            print(f"  Total executions: {execution_summary['total_executions']}")
            print(f"  Successful executions: {execution_summary['successful_executions']}")
            print(f"  Success rate: {execution_summary['success_rate']:.1%}")
            print(f"  Total time saved: {execution_summary['total_time_saved']:.1f} minutes")
            print(f"  Accuracy rate: {execution_summary['accuracy_rate']:.1%}")

            # Store results
            self.test_results = {
                "automation_opportunities": analyzer_summary['automation_opportunities'],
                "business_insights": analyzer_summary['business_insights'],
                "decisions": decision_summary['total_decisions'],
                "approved": decision_summary['approved_decisions'],
                "executions": execution_summary['total_executions'],
                "execution_success_rate": execution_summary['success_rate'],
                "total_time_saved": execution_summary['total_time_saved'],
                "roi": decision_summary['total_expected_roi']
            }

            # Success criteria for 4-agent system
            return (
                analyzer_summary['automation_opportunities'] >= 2 and
                decision_summary['total_decisions'] >= 1 and
                execution_summary['total_executions'] >= 1 and
                execution_summary['success_rate'] >= 0.8
            )

        except Exception as e:
            logger.error(f"Error in automation detection test: {e}")
            return False

    async def test_calendar_integration(self):
        """Test calendar integration with Execution Agent"""
        print("\n📅 Testing Calendar Integration with Execution Agent...")
        
        try:
            # Test meeting scheduling through Execution Agent
            meeting_params = {
                "decision_id": "test_meeting_decision",
                "title": "Native IQ Integration Test Meeting",
                "duration": 30,
                "attendees": ["test@example.com", "demo@example.com"]
            }

            result = await self.execution_agent._execute_meeting_scheduling(meeting_params)
            
            if result["success"]:
                print(f"  ✅ Meeting scheduled successfully")
                print(f"  ⏰ Time saved: {result['time_saved']} minutes")
                return True
            else:
                print(f"  ❌ Meeting scheduling failed: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Error in calendar integration test: {e}")
            return False

    async def run(self):
        print("🚀 Starting Native IQ Advanced 4-Agent Integration Test")
        print("=" * 60)
        await self.setup_agents()
        auto_success = await self.test_automation_detection()
        calendar_success = await self.test_calendar_integration()
        
        print("\n✅ Test Results:")
        print(self.test_results)
        
        overall_success = auto_success and calendar_success
        
        if overall_success:
            print("\n🎉 Native IQ 4-Agent Integration Test: SUCCESS")
            print("🚀 Complete Observer → Analyzer → Decision → Execution → Calendar workflow functional!")
        else:
            print("\n⚠️ Native IQ 4-Agent Integration Test: NEEDS ATTENTION")

if __name__ == "__main__":
    asyncio.run(NativeAdvancedIntegrationTest().run())
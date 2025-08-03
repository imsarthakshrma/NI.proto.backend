"""
Advanced Integration Test for Native AI System
Tests Observer → Analyzer → Decision → Calendar Tool with Complex Scenarios
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Native AI imports
from src.domains.agents.observer.ob_agent import ObserverAgent
from src.domains.agents.analyzer.analyzer_agent import AnalyzerAgent
from src.domains.agents.decision.decision_agent import DecisionAgent
from src.domains.tools.calandar_tool import get_calendar_tools, schedule_meeting, find_free_slots

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NativeAdvancedIntegrationTest:
    """Advanced Native AI integration test with complex automation scenarios"""

    def __init__(self):
        self.observer_agent = None
        self.analyzer_agent = None
        self.decision_agent = None
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
                    "Reminder: All project leads must submit their timesheets by 5pm Thursday. "
                    "Can we automate Slack reminders and integrate timesheet submission with our HR system?"
                ),
                "sender": "hr@company.com",
                "context": {"message_type": "reminder", "automation_hint": "slack, hr_integration"}
            },
            {
                "message": (
                    "Client onboarding for Acme Corp is scheduled for next Monday. "
                    "Please automate the onboarding checklist, send the welcome email, and create a shared drive folder. "
                    "Add the client to our CRM and calendar."
                ),
                "sender": "onboarding@company.com",
                "context": {"message_type": "onboarding", "automation_hint": "crm, email, drive, calendar"}
            },
            {
                "message": (
                    "Can we set up an automated workflow to track overdue invoices? "
                    "Send escalation emails to finance and schedule a follow-up call if payment is not received in 3 days."
                ),
                "sender": "finance@company.com",
                "context": {"message_type": "finance_automation", "automation_hint": "invoice_tracking, escalation, email, scheduling"}
            },
            {
                "message": (
                    "Monthly IT maintenance is next Wednesday. "
                    "Automate sending notifications to all employees, block time in their calendars, and log a ticket in the helpdesk system."
                ),
                "sender": "it@company.com",
                "context": {"message_type": "maintenance", "automation_hint": "notification, calendar, helpdesk"}
            },
            {
                "message": (
                    "For our Q3 planning, please automate the collection of project proposals, "
                    "send reminders to department heads, and generate a summary report by July 15th."
                ),
                "sender": "ceo@company.com",
                "context": {"message_type": "planning", "automation_hint": "proposal_collection, reminders, reporting"}
            },
            {
                "message": (
                    "Can we automate the process of gathering customer feedback after each support ticket is closed? "
                    "Send a follow-up survey email and log responses in the analytics dashboard."
                ),
                "sender": "support@company.com",
                "context": {"message_type": "customer_feedback", "automation_hint": "survey, analytics, email"}
            },
            {
                "message": (
                    "Schedule a recurring executive meeting every first Monday of the month at 9am. "
                    "Send agenda requests automatically and share meeting notes with all participants."
                ),
                "sender": "admin@company.com",
                "context": {"message_type": "meeting", "automation_hint": "recurring_meeting, agenda, notes"}
            },
            {
                "message": (
                    "Whenever a deal is marked as closed-won in Salesforce, "
                    "automatically trigger a celebration Slack message and schedule a debrief meeting with the sales team."
                ),
                "sender": "salesops@company.com",
                "context": {"message_type": "deal_closure", "automation_hint": "salesforce, slack, scheduling"}
            },
            {
                "message": (
                    "Automate the weekly backup of all shared drive folders and send a confirmation email to IT."
                ),
                "sender": "it@company.com",
                "context": {"message_type": "backup", "automation_hint": "drive_backup, email"}
            },
        ]

    async def setup_agents(self):
        try:
            self.observer_agent = ObserverAgent(agent_id="advanced_observer_001")
            print(f"✅ Observer Agent initialized: {self.observer_agent.agent_id}")

            self.analyzer_agent = AnalyzerAgent(agent_id="advanced_analyzer_001")
            print(f"✅ Analyzer Agent initialized: {self.analyzer_agent.agent_id}")

            self.decision_agent = DecisionAgent(agent_id="advanced_decision_001")
            print(f"✅ Decision Agent initialized: {self.decision_agent.agent_id}")

            print(f"✅ Calendar tools loaded: {len(self.calendar_tools)} tools available")
            return True
        except Exception as e:
            logger.error(f"Error setting up agents: {e}")
            return False

    async def test_automation_detection(self):
        print("\n🔍 Testing Automation Detection in Complex Scenarios...")
        try:
            # Simulate Observer learning from messages
            for i, msg in enumerate(self.test_messages):
                print(f"  Processing message {i+1}: {msg['message'][:60]}...")
                result = await self.observer_agent.process(msg, msg["context"])
                if result.get("beliefs_count", 0) > 0:
                    print(f"    ✅ Learned {result['beliefs_count']} patterns")
                else:
                    print(f"    ⚠️ No patterns learned from this message")
                
            observer_patterns = getattr(self.observer_agent, "patterns", {})
            observer_contacts = getattr(self.observer_agent, "contacts", {})

            print(f"  Observer patterns learned: {len(observer_patterns)}")
            print(f"  Observer contacts mapped: {len(observer_contacts)}")

            # Analyzer processes patterns
            analyzer_context = {
                "observer_patterns": observer_patterns,
                "observer_contacts": observer_contacts,
            }
            analyzer_beliefs = await self.analyzer_agent.perceive(
                self.test_messages, analyzer_context
            )
            analyzer_desires = await self.analyzer_agent.update_desires(analyzer_beliefs, analyzer_context)
            analyzer_intentions = await self.analyzer_agent.deliberate(analyzer_beliefs, analyzer_desires, [])
            for intention in analyzer_intentions:
                await self.analyzer_agent.act(intention, analyzer_context)
            await self.analyzer_agent.learn(analyzer_beliefs, analyzer_intentions, analyzer_context)

            analysis_summary = self.analyzer_agent.get_analysis_summary()
            print("\n📊 Analyzer Intelligence Summary:")
            print(f"  Automation opportunities: {analysis_summary.get('automation_opportunities', 0)}")
            print(f"  Business insights: {analysis_summary.get('business_insights', 0)}")
            print(f"  High confidence opportunities: {analysis_summary.get('high_confidence_opportunities', 0)}")
            print(f"  Time savings potential: {analysis_summary.get('total_time_savings_potential', 0)} minutes")

            self.test_results["automation_opportunities"] = analysis_summary.get("automation_opportunities", 0)
            self.test_results["business_insights"] = analysis_summary.get("business_insights", 0)
            return analysis_summary.get("automation_opportunities", 0) > 0

        except Exception as e:
            logger.error(f"Error in automation detection: {e}")
            return False

    async def test_decision_agent(self):
        print("\n🧠 Testing Decision Agent in Complex Scenarios...")
        try:
            analyzer_opportunities = self.analyzer_agent.get_top_automation_opportunities(10)
            analyzer_insights = self.analyzer_agent.get_business_insights(10)

            decision_context = {
                "analyzer_opportunities": analyzer_opportunities,
                "analyzer_insights": analyzer_insights,
                "urgency_level": "high",
                "resources": {"cpu_usage": 0.2, "budget": 100000}
            }
            beliefs = await self.decision_agent.perceive({}, decision_context)
            desires = await self.decision_agent.update_desires(beliefs, decision_context)
            intentions = await self.decision_agent.deliberate(beliefs, desires, [])
            for intention in intentions:
                await self.decision_agent.act(intention, decision_context)
            await self.decision_agent.learn(beliefs, intentions, decision_context)

            decision_summary = self.decision_agent.get_decision_summary()
            print("\n📊 Decision Intelligence Summary:")
            print(f"  Total decisions: {decision_summary.get('total_decisions', 0)}")
            print(f"  Approved decisions: {decision_summary.get('approved_decisions', 0)}")
            print(f"  Rejected decisions: {decision_summary.get('rejected_decisions', 0)}")
            print(f"  Total expected ROI: {decision_summary.get('total_expected_roi', 0):.1f}x")

            self.test_results["decisions"] = decision_summary.get("total_decisions", 0)
            self.test_results["approved"] = decision_summary.get("approved_decisions", 0)
            self.test_results["roi"] = decision_summary.get("total_expected_roi", 0)
            return decision_summary.get("approved_decisions", 0) > 0

        except Exception as e:
            logger.error(f"Error in Decision Agent testing: {e}")
            return False

    async def run(self):
        print("🚀 Starting Native AI Advanced Integration Test")
        print("=" * 60)
        await self.setup_agents()
        auto_success = await self.test_automation_detection()
        decision_success = await self.test_decision_agent()
        print("\n✅ Test Results:")
        print(self.test_results)
        if auto_success and decision_success:
            print("\n🎉 Native AI Advanced Integration Test: SUCCESS")
        else:
            print("\n⚠️ Native AI Advanced Integration Test: NEEDS ATTENTION")

if __name__ == "__main__":
    asyncio.run(NativeAdvancedIntegrationTest().run())
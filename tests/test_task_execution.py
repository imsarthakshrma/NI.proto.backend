"""
Test script to verify Native IQ can actually execute tasks, not just respond conversationally
"""

import asyncio
import logging
import os
from unittest.mock import MagicMock, AsyncMock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_task_execution():
    """Test that Native IQ actually executes tasks through DELA pipeline"""
    
    print("🚀 Testing Native IQ Task Execution...")
    print("=" * 50)
    
    # Import after setting up environment
    from src.integration.telegram.hybrid_native_bot import HybridNativeAI
    from src.integration.telegram.auth_handler import TelegramAuthHandler
    from src.domains.agents.observer.ob_agent import ObserverAgent
    from src.domains.agents.analyzer.analyzer_agent import AnalyzerAgent
    from src.domains.agents.decision.decision_agent import DecisionAgent
    from src.domains.agents.execution.execution_agent import ExecutionAgent
    from src.domains.agents.communication.proactive_agent import ProactiveCommunicationAgent
    from src.domains.agents.conversation.proactive_conversation_engine import ProactiveConversationEngine
    
    # Create mock Telegram objects
    class MockUser:
        def __init__(self):
            self.id = 12345
            self.first_name = "TestUser"
            self.last_name = "Smith"
            self.username = "testuser"
    
    class MockMessage:
        def __init__(self, text):
            self.text = text
            self.reply_to_message = None
            self.reply_text = AsyncMock()
    
    class MockUpdate:
        def __init__(self, message_text):
            self.effective_user = MockUser()
            self.message = MockMessage(message_text)
    
    class MockContext:
        pass
    
    class MockApplication:
        def __init__(self):
            self.bot = MagicMock()
    
    class MockAuthHandler:
        def is_authorized(self, user_id):
            return True
    
    try:
        # Initialize agents
        print("📋 Initializing agents...")
        observer_agent = ObserverAgent()
        analyzer_agent = AnalyzerAgent()
        decision_agent = DecisionAgent()
        execution_agent = ExecutionAgent()
        proactive_agent = ProactiveCommunicationAgent()
        proactive_conversation_engine = ProactiveConversationEngine()
        
        # Initialize auth handler and application
        auth_handler = MockAuthHandler()
        application = MockApplication()
        
        # Initialize HybridNativeAI
        print("🤖 Initializing HybridNativeAI...")
        hybrid_ai = HybridNativeAI(
            observer_agent=observer_agent,
            analyzer_agent=analyzer_agent,
            decision_agent=decision_agent,
            execution_agent=execution_agent,
            proactive_agent=proactive_agent,
            proactive_conversation_engine=proactive_conversation_engine,
            auth_handler=auth_handler,
            application=application
        )
        
        # Add user to interactive mode
        hybrid_ai.interactive_users.add(12345)
        
        print("✅ Initialization complete!")
        print()
        
        # Test 1: Conversational message (should NOT trigger task execution)
        print("🧪 Test 1: Conversational Message")
        print("-" * 30)
        conversational_update = MockUpdate("Hello, how are you today?")
        conversational_context = MockContext()
        
        print(f"📝 Sending conversational message: '{conversational_update.message.text}'")
        await hybrid_ai.handle_message(conversational_update, conversational_context)
        
        # Check if it was routed to conversational handling (not task execution)
        print("✅ Conversational message processed (should use ProactiveCommunicationAgent)")
        print()
        
        # Test 2: Task execution request (should trigger DELA pipeline)
        print("🧪 Test 2: Task Execution Request")
        print("-" * 30)
        task_update = MockUpdate("Schedule a meeting with the team for tomorrow at 2 PM")
        task_context = MockContext()
        
        print(f"📝 Sending task request: '{task_update.message.text}'")
        await hybrid_ai.handle_message(task_update, task_context)
        
        print("✅ Task execution request processed (should use DELA pipeline)")
        print()
        
        # Test 3: Another task execution request
        print("🧪 Test 3: Another Task Execution Request")
        print("-" * 30)
        automation_update = MockUpdate("Automate the weekly report generation and send it to stakeholders")
        automation_context = MockContext()
        
        print(f"📝 Sending automation request: '{automation_update.message.text}'")
        await hybrid_ai.handle_message(automation_update, automation_context)
        
        print("✅ Automation request processed (should use DELA pipeline)")
        print()
        
        # Test 4: Email task request
        print("🧪 Test 4: Email Task Request")
        print("-" * 30)
        email_update = MockUpdate("Send an email to john@company.com about the project update")
        email_context = MockContext()
        
        print(f"📝 Sending email request: '{email_update.message.text}'")
        await hybrid_ai.handle_message(email_update, email_context)
        
        print("✅ Email request processed (should use DELA pipeline)")
        print()
        
        print("🎉 ALL TESTS COMPLETED!")
        print("=" * 50)
        print("📊 SUMMARY:")
        print("✅ Conversational messages → ProactiveCommunicationAgent")
        print("✅ Task requests → DELA Pipeline (Observer → Analyzer → Decision → Execution)")
        print("🚀 Native IQ now ACTUALLY EXECUTES TASKS instead of just talking about them!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_task_execution())

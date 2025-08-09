#!/usr/bin/env python
"""
Test OpenAI API connectivity specifically for the Telegram bot
Run this script to verify that messages from the Telegram bot are reaching OpenAI
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import ContextTypes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    logger.error("❌ OPENAI_API_KEY environment variable not found!")
    exit(1)
else:
    logger.info(f"✅ OPENAI_API_KEY found: {api_key[:5]}...{api_key[-4:]}")

async def test_direct_openai():
    """Test direct OpenAI API connectivity"""
    try:
        logger.info("Testing direct OpenAI API connection...")
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello!"}
            ],
            max_tokens=50
        )
        message = response.choices[0].message.content.strip()
        logger.info(f"✅ Direct OpenAI API test successful! Response: {message}")
        return True
    except Exception as e:
        logger.error(f"❌ Direct OpenAI API test failed: {str(e)}")
        return False

async def test_hybrid_native_bot():
    """Test if HybridNativeAI can successfully call OpenAI"""
    try:
        logger.info("Testing HybridNativeAI OpenAI integration...")
        
        # Import the HybridNativeAI class
        from src.integration.telegram.hybrid_native_bot import HybridNativeAI
        from src.domains.agents.observer.ob_agent import ObserverAgent
        from src.domains.agents.analyzer.analyzer_agent import AnalyzerAgent
        from src.domains.agents.decision.decision_agent import DecisionAgent
        from src.domains.agents.execution.execution_agent import ExecutionAgent
        from src.domains.agents.communication.proactive_agent import ProactiveCommunicationAgent
        from src.domains.agents.conversation.proactive_conversation_engine import ProactiveConversationEngine
        
        # Create mock agents
        observer_agent = ObserverAgent(agent_id="test_observer")
        analyzer_agent = AnalyzerAgent(agent_id="test_analyzer")
        decision_agent = DecisionAgent(agent_id="test_decision")
        execution_agent = ExecutionAgent(agent_id="test_execution")
        proactive_agent = ProactiveCommunicationAgent(agent_id="test_proactive")
        proactive_conversation_engine = ProactiveConversationEngine()
        
        # Create mock auth_handler and application
        class MockAuthHandler:
            def __init__(self):
                self.authorized_users = set([123456])  # Add the test user ID
                
            def is_authorized(self, update):
                # The real auth handler expects an update object, not user_id
                user_id = update.effective_user.id
                logger.info(f"🔍 Auth check for user {user_id}: {user_id in self.authorized_users}")
                return user_id in self.authorized_users
        
        class MockApplication:
            def __init__(self):
                pass
                
        # Create the HybridNativeAI instance
        bot = HybridNativeAI(
            observer_agent=observer_agent,
            analyzer_agent=analyzer_agent,
            decision_agent=decision_agent,
            execution_agent=execution_agent,
            proactive_agent=proactive_agent,
            proactive_conversation_engine=proactive_conversation_engine,
            auth_handler=MockAuthHandler(),
            application=MockApplication()
        )
        
        # Create a mock update and context
        class MockMessage:
            def __init__(self, text):
                self.text = text
                self.reply_to_message = None
        
        class MockUser:
            def __init__(self, id, first_name):
                self.id = id
                self.first_name = first_name
                self.last_name = "User"  # Add missing attribute
                self.username = "testuser"  # Add missing attribute
        
        class MockUpdate:
            def __init__(self, message, user):
                self.message = message
                self.effective_user = user
        
        class MockContext:
            def __init__(self):
                self.bot = None
        
        # Create mock objects
        message = MockMessage("Hello Native IQ, can you help me with business operations?")
        user = MockUser(123456, "Test User")
        update = MockUpdate(message, user)
        context = MockContext()
        
        # Add the user to interactive users
        bot.interactive_users.add(user.id)
        
        # Mock the reply_text method to capture the response
        response_captured = None
        
        async def mock_reply_text(text, parse_mode=None):
            nonlocal response_captured
            response_captured = text
            logger.info(f"✅ CAPTURED RESPONSE: {text}")
            return True
        
        # Mock the reply_text method on the message object
        message.reply_text = mock_reply_text
        
        # Also mock the _send_telegram_message method to prevent it from trying to send via Telegram
        original_send_telegram = bot.proactive_agent._send_telegram_message
        async def mock_send_telegram(user_id, message_text):
            logger.info(f"Mocked telegram send to {user_id}: {message_text}")
            return True
        bot.proactive_agent._send_telegram_message = mock_send_telegram
        
        # Handle the message
        logger.info("Sending test message to HybridNativeAI...")
        logger.info(f"User {user.id} is in interactive_users: {user.id in bot.interactive_users}")
        
        # Add some debugging to see what path the message takes
        try:
            await bot.handle_message(update, context)
            logger.info("handle_message completed without exception")
        except Exception as e:
            logger.error(f"Exception in handle_message: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        # Check if we got a response
        if response_captured:
            logger.info(f"✅ HybridNativeAI successfully generated a response: {response_captured}")
            return True
        else:
            logger.error("❌ HybridNativeAI did not generate a response")
            return False
            
    except Exception as e:
        logger.error(f"❌ HybridNativeAI test failed: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Run all tests"""
    logger.info("Starting OpenAI API connectivity tests...")
    
    # Test direct OpenAI API
    direct_success = await test_direct_openai()
    
    # Test HybridNativeAI
    hybrid_native_success = await test_hybrid_native_bot()
    
    # Summary
    logger.info("\n--- TEST RESULTS SUMMARY ---")
    logger.info(f"Direct OpenAI API: {'✅ PASS' if direct_success else '❌ FAIL'}")
    logger.info(f"HybridNativeAI OpenAI: {'✅ PASS' if hybrid_native_success else '❌ FAIL'}")
    
    if direct_success and hybrid_native_success:
        logger.info("🎉 All tests passed! Your Telegram bot can successfully reach OpenAI.")
    else:
        logger.info("⚠️ Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    asyncio.run(main())


"""
Standalone script to run the Native AI Telegram bot
This script uses a non-asyncio approach to avoid event loop conflicts
"""

import os
import sys
import logging
from telegram.ext import ApplicationBuilder
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from src.domains.tools.calandar_tool import get_calendar_tools
from src.domains.tools.email_tool import get_email_tools

# Add the project root to the path so we can import our modules
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def main():
    """Run the bot using non-asyncio approach"""
    # Import here to avoid circular imports
    from src.domains.agents.observer.ob_agent import ObserverAgent
    from src.domains.agents.analyzer.analyzer_agent import AnalyzerAgent
    from src.domains.agents.decision.decision_agent import DecisionAgent
    from src.domains.agents.execution.execution_agent import ExecutionAgent
    from src.domains.agents.communication.proactive_agent import ProactiveCommunicationAgent
    from src.domains.agents.conversation.proactive_conversation_engine import ProactiveConversationEngine
    from src.integration.telegram.auth_handler import TelegramAuthHandler
    
    # Get token from environment
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN found in environment")
        sys.exit(1)
    
    # Create application directly
    application = ApplicationBuilder().token(token).build()
    
    # Initialize agents
    observer_agent = ObserverAgent()
    analyzer_agent = AnalyzerAgent()
    decision_agent = DecisionAgent()
    execution_agent = ExecutionAgent()
    proactive_agent = ProactiveCommunicationAgent()
    proactive_conversation_engine = ProactiveConversationEngine()

    
    # Initialize auth handler
    auth_handler = TelegramAuthHandler()

    # Get tools
    calendar_tools = get_calendar_tools()
    email_tools = get_email_tools()
    
    for tool in calendar_tools:
        execution_agent.register_tool("calendar_tool", tool)

    for tool in email_tools:
        execution_agent.register_tool("email_tool", tool)

    logger.info(f"Registered tools: {execution_agent.get_available_tools()}")

    # Import and setup handlers
    from src.integration.telegram.hybrid_native_bot import setup_handlers
    setup_handlers(application, observer_agent, analyzer_agent, decision_agent, 
                  execution_agent, proactive_agent, proactive_conversation_engine, auth_handler)
    
    # Start the bot using non-asyncio method
    logger.info("Starting Native AI Bot...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

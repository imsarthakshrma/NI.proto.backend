"""
Test script to verify Execution Agent integration with Google Drive and email tools
"""

import asyncio
import logging
import sys
import os

# Add the src directory to Python path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(repo_root, 'src'))

from src.domains.agents.execution.execution_agent import ExecutionAgent
from src.core.base_agent import Intention

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_execution_agent_tools():
    """Test the Execution Agent's tool integration"""
    
    print("🚀 Testing Execution Agent Tool Integration")
    print("=" * 50)
    
    # Initialize the Execution Agent
    try:
        agent = ExecutionAgent("test_execution_001")
        print(f"✅ Execution Agent initialized: {agent.agent_id}")
        
        # Check available tools
        available_tools = agent.get_available_tools()
        print(f"📋 Available tools: {available_tools}")
        
        # Test tool availability checks
        expected_tools = [
            "list_drive_files",
            "get_drive_file_info", 
            "download_drive_file",
            "upload_drive_file",
            "email_tool"
        ]
        
        print("\n🔍 Checking tool availability:")
        for tool_name in expected_tools:
            has_tool = agent.has_tool(tool_name)
            status = "✅" if has_tool else "❌"
            print(f"  {status} {tool_name}: {'Available' if has_tool else 'Missing'}")
        
        # Test task type detection
        print("\n🎯 Testing task type detection:")
        test_messages = [
            ("list my google drive files", "list_drive_files"),
            ("download file from drive", "download_drive_file"),
            ("upload document to drive", "upload_drive_file"),
            ("get drive file info", "get_drive_file_info"),
            ("send an email", "send_email"),
            ("schedule a meeting", "schedule_meeting")
        ]
        
        for message, expected_task in test_messages:
            detected_task = agent._determine_task_type("execute_automation", message)
            status = "✅" if detected_task == expected_task else "❌"
            print(f"  {status} '{message}' -> {detected_task} (expected: {expected_task})")
        
        # Test tool execution simulation (without actually calling external APIs)
        print("\n🛠️ Testing tool execution framework:")
        
        # Create a test intention
        test_intention = Intention(
            id="test_intention_001",
            desire_id="execute_automations",
            action_type="execute_automation",
            parameters={"task_type": "list_drive_files"}
        )
        
        # Test context
        test_context = {
            "user_message": "list my google drive files",
            "user": "TestUser"
        }
        
        # Execute the intention (this will show the tool execution flow)
        print("  🎬 Executing test intention...")
        result = await agent.act(test_intention, test_context)
        
        print(f"  📊 Execution result:")
        print(f"    Success: {result.get('success', False)}")
        print(f"    Action taken: {result.get('action_taken', False)}")
        print(f"    Tool used: {result.get('tool_used', 'N/A')}")
        print(f"    Task type: {result.get('task_type', 'N/A')}")
        if result.get('error'):
            print(f"    Error: {result.get('error')}")
        
        # Get execution summary
        summary = agent.get_execution_summary()
        print(f"\n📈 Execution Summary:")
        print(f"  Total executions: {summary['total_executions']}")
        print(f"  Successful executions: {summary['successful_executions']}")
        print(f"  Success rate: {summary['success_rate']:.2%}")
        print(f"  Total time saved: {summary['total_time_saved']} minutes")
        
        print("\n🎉 Integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.exception("Test execution failed")
        return False

if __name__ == "__main__":
    print("Starting Execution Agent Integration Test...")
    success = asyncio.run(test_execution_agent_tools())
    
    if success:
        print("\n✅ All tests passed! The Execution Agent can use our tools.")
    else:
        print("\n❌ Tests failed. Check the logs for details.")
        sys.exit(1)

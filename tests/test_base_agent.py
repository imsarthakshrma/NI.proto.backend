"""
Main testing file for DELA AI Base Agent
Simple test harness to validate base_agent.py functionality
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any, List
# from dotenv import load_dotenv
# load_dotenv()

# Mock the base_agent imports for now - we'll implement them step by step
try:
    from src.core.base_agent import (
        BaseAgent, 
        Belief, 
        Desire, 
        Intention, 
        BeliefType,
        # AgentStatus
    )
    from langchain_core.messages import BaseMessage, HumanMessage
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    print("This is expected - we'll implement components step by step")
    IMPORTS_AVAILABLE = False


class TestObserverAgent(BaseAgent):
    """Simple test implementation of Observer Agent"""
    
    async def perceive(self, messages: List[BaseMessage], context: Dict[str, Any]) -> List[Belief]:
        """Test perception - just create a simple belief from input"""
        beliefs = []
        for msg in messages:
            belief = Belief(
                type=BeliefType.OBSERVATION,
                content={"message": str(msg.content), "timestamp": datetime.now().isoformat()},
                confidence=0.9,
                source="test_input"
            )
            beliefs.append(belief)
        return beliefs
    
    async def update_desires(self, beliefs: List[Belief], context: Dict[str, Any]) -> List[Desire]:
        """Test desires - simple goal to process observations"""
        return [
            Desire(
                goal="process_observation",
                priority=1,
                conditions={"has_beliefs": len(beliefs) > 0}
            )
        ]
    
    async def deliberate(self, beliefs: List[Belief], desires: List[Desire], current_intentions: List[Intention]) -> List[Intention]:
        """Test deliberation - create intention to log observations"""
        new_intentions = []
        for desire in desires:
            if desire.goal == "process_observation":
                intention = Intention(
                    desire_id=desire.id,
                    plan=[
                        {"action": "log_observation", "status": "pending"},
                        {"action": "update_knowledge", "status": "pending"}
                    ]
                )
                new_intentions.append(intention)
        return new_intentions
    
    async def act(self, intention: Intention, context: Dict[str, Any]) -> Dict[str, Any]:
        """Test action - just log what we're doing"""
        next_action = intention.next_action()
        if next_action:
            print(f"Executing: {next_action['action']}")
            next_action["status"] = "completed"
            return {"success": True, "action": next_action["action"]}
        return {"success": False, "reason": "no_action_available"}
    
    async def learn(self, beliefs: List[Belief], intentions: List[Intention], context: Dict[str, Any]) -> None:
        """Test learning - just print what we learned"""
        completed_intentions = [i for i in intentions if i.status == "completed"]
        print(f"Learning from {len(completed_intentions)} completed intentions")


async def test_basic_functionality():
    """Test basic agent functionality"""
    print("Testing Basic Agent Functionality")
    print("=" * 50)
    
    if not IMPORTS_AVAILABLE:
        print("Cannot run tests - missing imports")
        print("TODO: Implement base_agent.py first")
        return
    
    try:
        # Create test agent
        agent = TestObserverAgent(
            agent_id="test_001",
            agent_type="TestObserver"
        )
        
        print(f"Agent created: {agent.agent_id}")
        print(f"Initial status: {agent.get_status()}")
        
        # Test processing
        test_input = {"message": "Hello, this is a test observation"}
        result = await agent.process(test_input, {"test": True})
        
        print(f"Processing completed")
        print(f"Final status: {agent.get_status()}")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


def test_imports():
    """Test if we can import required packages"""
    print("Testing Package Imports")
    print("=" * 30)
    
    packages_to_test = [
        "langchain_core",
        "langchain_openai", 
        "langgraph",
        "uuid",
        "asyncio",
        "dataclasses"
    ]
    
    for package in packages_to_test:
        try:
            __import__(package)
            print(f"{package}")
        except ImportError:
            print(f"{package} - needs installation")


def test_environment():
    """Test environment setup"""
    print("Testing Environment")
    print("=" * 25)
    
    env_vars = ["OPENAI_API_KEY", "LANGSMITH_API_KEY"]
    
    for var in env_vars:
        if os.environ.get(var):
            print(f"{var} is set")
        else:
            print(f"{var} not set (optional for basic testing)")


async def main():
    """Main test runner"""
    print("DELA AI - Base Agent Testing")
    print("=" * 40)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Run tests in sequence
    test_imports()
    print()
    
    test_environment()
    print()
    
    await test_basic_functionality()
    print()
    
    print("Testing completed!")
    print("=" * 40)


if __name__ == "__main__":
    # Simple way to run async main
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Testing interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
"""
Base Agent Implementation for Native Intelligence
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
# from re import L
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
import uuid
from dataclasses import field
from dotenv import load_dotenv
load_dotenv()


from langgraph.graph import StateGraph, END
# from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

# from llama_index import OpenAI

class AgentStatus (Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    LEARNING = "learning"
    ERROR = "error"

class BeliefType (Enum):
    OBSERVATION = "observation"
    PATTERN = "pattern"
    CONTEXT = "context"
    KNOWLEDGE = "knowledge"


@dataclass
class Belief:
    """
    Represents a belief in the BDI framework
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: BeliefType = BeliefType.OBSERVATION
    content: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"

    def is_valid(self) -> bool:
        """Check if belief is still valid (not expired)"""
        return self.confidence > 0.1

@dataclass
class Desire:
    """Represents a desire/goal in the BDI framework"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    priority: int = 1
    conditions: Dict[str, Any] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    
    def is_achievable(self, beliefs: List[Belief]) -> bool:
        """Check if desire can be achieved given current beliefs
        
        Args:
            beliefs (List[Belief]): List of current beliefs
        
        Returns:
            bool: True if desire can be achieved, False otherwise
        """
        # Default implementation - can be overridden by specific agents
        # Check if we have any valid beliefs to work with
        valid_beliefs = [belief for belief in beliefs if belief.is_valid()]
        return len(valid_beliefs) > 0


@dataclass
class Intention:
    """
    Represents an intention/plan in the BDI framework
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    desire_id: str = ""
    action_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    plan: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending" # pending, active, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    # updated_at: datetime = field(default_factory=datetime.now)

    def next_action(self)-> Optional[Dict[str, Any]]:
        """
        Get the next action to be executed
        """
        pending_actions = [action for action in self.plan if action.get("status") != "completed"]
        return pending_actions[0] if pending_actions else None

    def update_action(self, action_id: str, status: str)-> Optional[Dict[str, Any]]:
        """
        Update the status of an action
        """
        for action in self.plan:
            if action.get("id") == action_id:
                action["status"] = status
                return action
        return None

class AgentState(TypedDict):
    """LangGraph state for agent processing"""
    messages: Annotated[List[BaseMessage], "The messages in the conversation"]
    beliefs: Annotated[List[Belief], "Current agent beliefs"]
    desires: Annotated[List[Desire], "Current agent desires/goals"]
    intentions: Annotated[List[Intention], "Current agent intentions/plans"]
    context: Annotated[Dict[str, Any], "Processing context"]
    agent_status: Annotated[str, "Current agent status"]

class BaseAgent(ABC):
    """
    Base BDI Agent class integrated with LangGraph
    Provides the foundation for all DELA AI agents
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        model_name: str = "gpt-4o",
        temperature: float = 0.1
    ):
        """
        Initialize the agent with basic parameters
        """ 
        # agent parameters
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.status = AgentStatus.IDLE
        
        # langgraph components
        self.model = ChatOpenAI(model=model_name, temperature=temperature)
        self.graph = None
        self._build_graph()
        
        # BDI components
        self.beliefs: List[Belief] = []
        self.desires: List[Desire] = []
        self.intentions: List[Intention] = []
        
        # agent metadata
        self.created_at = datetime.now()
        self.last_activity = datetime.now() 


    def _build_graph(self):
        """Build the LangGraph workflow for this agent"""
        workflow = StateGraph(AgentState)
        
        # define nodes
        workflow.add_node("perceive", self._perceive_node)
        workflow.add_node("deliberate", self._deliberate_node)
        workflow.add_node("act", self._act_node)
        workflow.add_node("learn", self._learn_node)
        
        # define edges
        workflow.set_entry_point("perceive")
        workflow.add_edge("perceive", "deliberate")
        workflow.add_edge("deliberate", "act")
        workflow.add_edge("act", "learn")
        workflow.add_edge("learn", END)
        
        self.graph = workflow.compile()

    async def _perceive_node(self, state: AgentState) -> AgentState:
        """Perception phase - update beliefs based on input"""
        self.status = AgentStatus.PROCESSING
        
        # extract new observations from messages
        new_beliefs = await self.perceive(state["messages"], state["context"])
        
        # update beliefs
        updated_beliefs = self._update_beliefs(state["beliefs"] + new_beliefs)
        
        return {
            **state,
            "beliefs": updated_beliefs,
            "agent_status": self.status.value
        }

    async def _deliberate_node(self, state: AgentState) -> AgentState:
        """Deliberation phase - generate intentions from beliefs and desires"""
        
        # update desires based on current context
        updated_desires = await self.update_desires(state["beliefs"], state["context"])
        
        # generate new intentions
        new_intentions = await self.deliberate(
            state["beliefs"], 
            updated_desires, 
            state["intentions"]
        )
        
        return {
            **state,
            "desires": updated_desires,
            "intentions": state["intentions"] + new_intentions
        }
    
    async def _act_node(self, state: AgentState) -> AgentState:
        """Action phase - execute intentions"""
        
        # select and execute the highest priority intention
        active_intention = self._select_intention(state["intentions"])
        
        if active_intention:
            result = await self.act(active_intention, state["context"])
            
            # update intention status
            for intention in state["intentions"]:
                if intention.id == active_intention.id:
                    intention.status = "completed" if result.get("success") else "failed"
        
        return {
            **state,
            "intentions": state["intentions"]
        }
    
    async def _learn_node(self, state: AgentState) -> AgentState:
        """Learning phase - update knowledge based on outcomes"""
        
        # learn from the execution results
        await self.learn(state["beliefs"], state["intentions"], state["context"])
        
        self.status = AgentStatus.IDLE
        self.last_activity = datetime.now()
        
        return {
            **state,
            "agent_status": self.status.value
        }
    
    def _update_beliefs(self, beliefs: List[Belief]) -> List[Belief]:
        """Update and filter beliefs"""
        # remove expired or invalid beliefs
        valid_beliefs = [b for b in beliefs if b.is_valid()]
        
        # remove duplicates (keep most recent)
        unique_beliefs = {}
        for belief in valid_beliefs:
            key = f"{belief.type.value}_{belief.source}"
            if key not in unique_beliefs or belief.timestamp > unique_beliefs[key].timestamp:
                unique_beliefs[key] = belief
        
        return list(unique_beliefs.values())

    def _select_intention(self, intentions: List[Intention]) -> Optional[Intention]:
        """Select the highest priority intention to execute"""
        pending_intentions = [i for i in intentions if i.status == "pending"]
        if not pending_intentions:
            return None
        
        # simple priority selection - can be overridden
        return pending_intentions[0]
    
    async def process(
        self, 
        input_data: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Main processing method using LangGraph"""
        
        # prepare initial state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=str(input_data))],
            "beliefs": self.beliefs.copy(),
            "desires": self.desires.copy(),
            "intentions": self.intentions.copy(),
            "context": context or {},
            "agent_status": self.status.value
        }
        
        # configure run for LangSmith tracing
        config: RunnableConfig = {
            "run_name": f"{self.agent_type}_{self.agent_id}",
            "tags": [self.agent_type, "dela_ai"],
            "metadata": {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # execute the graph
        result = await self.graph.ainvoke(initial_state, config)
        
        # update internal state
        self.beliefs = result["beliefs"]
        self.desires = result["desires"]
        self.intentions = result["intentions"]
        
        return {
            "agent_id": self.agent_id,
            "status": result["agent_status"],
            "beliefs_count": len(self.beliefs),
            "intentions_count": len([i for i in self.intentions if i.status == "pending"]),
            "result": result
        }

    # abstract methods to be implemented by specific agents
    @abstractmethod
    async def perceive(
        self, 
        messages: List[BaseMessage], 
        context: Dict[str, Any]
    ) -> List[Belief]:
        """Process input and generate beliefs"""
        pass
    
    @abstractmethod
    async def update_desires(
        self, 
        beliefs: List[Belief], 
        context: Dict[str, Any]
    ) -> List[Desire]:
        """Update agent desires based on current beliefs"""
        pass
    
    @abstractmethod
    async def deliberate(
        self, 
        beliefs: List[Belief], 
        desires: List[Desire], 
        current_intentions: List[Intention]
    ) -> List[Intention]:
        """Generate new intentions based on beliefs and desires"""
        pass
    
    @abstractmethod
    async def act(
        self, 
        intention: Intention, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an intention"""
        pass
    
    @abstractmethod
    async def learn(
        self, 
        beliefs: List[Belief], 
        intentions: List[Intention], 
        context: Dict[str, Any]
    ) -> None:
        """Learn from execution results"""
        pass
    
    # utility methods
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "beliefs_count": len(self.beliefs),
            "desires_count": len(self.desires),
            "intentions_count": len(self.intentions),
            "last_activity": self.last_activity.isoformat()
        }
    
    def add_belief(self, belief: Belief) -> None:
        """Add a new belief"""
        self.beliefs.append(belief)
        self.beliefs = self._update_beliefs(self.beliefs)
    
    def add_desire(self, desire: Desire) -> None:
        """Add a new desire"""
        self.desires.append(desire)
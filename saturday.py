# SATURDAY PROJECT GOAL
# Make a fully working and interacatble multi node langgraph agentic system.
# This is mission critical activity to be working on.

# Begin by planning and drawing graph.
# Follow code structure of research agent. Prompts, etc are all in different places?
# Maybe do this as you need, dont prematurely abstract
# Focus on function

# LLM with structured output, pydantic data classes, tool binding, separation of calls
# Avoid conditional edges for command routers

# Load environment variables from .env file
import os
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LANGSMITH_TRACING = os.getenv('LANGSMITH_TRACING')
LANGSMITH_ENDPOINT = os.getenv('LANGSMITH_ENDPOINT')
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')
LANGSMITH_PROJECT = os.getenv('LANGSMITH_PROJECT')

# Imports from LangGraph and related libraries
from typing import Annotated, Any, List, Optional, Sequence, List, Union, Literal
from pydantic import BaseModel, Field, validator
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from operator import add

# Initialize the LLM (OpenAI) and bind the tools.
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5,
    api_key=OPENAI_API_KEY
)

# Main control flow will be done with a router agnet that outputs missions. These missions will be translated into commands, which will be the final output.

# Human, 

# Begin with the state: We will have nested layers of strategy and routing to handle agentic control flow.

# TODO make the plan object a more structured item.
class Plan(BaseModel):
    goal: str = Field(..., description="The high-level goal of the plan.")
    plan_text: str = Field("", description="The actual plan details as a string")
    steps: list[str] = Field(default_factory=list, description="Ordered list of steps")

# Main state
class State(BaseModel):
    messages: Annotated[
        Sequence[BaseMessage],
        add
    ] = Field(
        default_factory=list,
        description="The messages associated with all "
    )
    plan: Plan = Field(
        default_factory=Plan,
        description="The plan associated with the current state."
    )
    next: str = Field(description="The next node to route to")



# Human Node:
def Human(state: State):
    # Keep track of where the state came from, this should be triggered by a command
    # Make dummy for now 
    human_message = "Yo whats up im a human sayyy whatttttttt-- please route me to Human!"
    return {"messages": human_message}


class Router(BaseModel):
    """Member to route to next"""

    next: Literal["Human", "Planner", "Worker"] = Field(
            ...,
            description="The node to route to next. If no workers are needed, route to END"
            )

# Agentic Router Node
# def AgenticRouter(state: State) -> Command[Literal["Human", "Planner", "Worker"]]:
def AgenticRouter(state: State) -> Command[Literal["human" ]]:
    system_prompt = """
        You are a supervisor tasked with managing a conversation between the following members: Human, Planner, Worker. Route to human always.
        
    """

    messages = [{"role": "system", "content": system_prompt}] + state.messages

    response = llm.with_structured_output(Router).invoke(messages)

    return Command(
            goto=response["next"],
            update={
                "next": goto,
                }
            ) 


graph_builder = StateGraph(State)

graph_builder.add_node("agentic_router", AgenticRouter)
graph_builder.add_node("human", Human)

graph_builder.add_edge("human", "agentic_router")
graph_builder.add_edge(START, "human")

memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)


thread = {"configurable": {"thread_id": "1"}}

initial_state = {}  # or an instance of your State model
config = {"configurable": {"thread_id": "1", "checkpoint_ns": ""}}
graph.invoke(initial_state, config=config)














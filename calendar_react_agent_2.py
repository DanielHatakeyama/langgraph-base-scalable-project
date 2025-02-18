# Todays work is to recreate yesterdays project but completely unassisted apart from the documentation.
# Here goes nothing. I will of course use yesterday's code as reference.

# =============================================================================
# Setup
# =============================================================================

# Set up logging (change level to INFO to disable debug prints)
import logging
logging.basicConfig(level=logging.INFO)

# Display Graph Imports
from IPython.display import Image

# Typing Imports
from pydantic import BaseModel
from typing import Annotated
from typing_extensions import TypedDict

# LangChain Imports
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool

#LangGraph Imports
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from langgraph.prebuilt import ToolNode, tools_condition

# Environment Setup
import os
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

# llm setup
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=OPENAI_API_KEY
)

# -----------
# Define All Tools (Do this better on second pass-through)
# ---------

search_tool = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=False
)

from tools import (
    create_calendar_event,
    CreateCalendarEventModel
)

from calendar_react_agent import (
    get_current_datetime
)

# List of tools (acts as toolbox, check to see if there is more official way to do this)
tools = [get_current_datetime, create_calendar_event]

# mock tool, just definition for a tool, so routing happens
class AskHuman(BaseModel):
    """Ask the human a question"""

    question: str

# -------

# Bind the tools to the model, and bind the askhuman path next to it.
model = llm
model_with_tools = llm.bind_tools(tools + [AskHuman])

# --------
# Graph Assembly
# --------

# TODO: CHeck if this can be done with pydantic instead

# Define the function that determines whether to continue or not
def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1]
    # If there is no function call, then we finish
    if not last_message.tool_calls:
        return END
    # If tool call is asking Human, we return that node
    # You could also add logic here to let some system know that there's something that requires Human input
    # For example, send a slack message, etc
    elif last_message.tool_calls[0]["name"] == "AskHuman":
        return "ask_human"
    # Otherwise if there is, we continue
    else:
        return "action"

class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

# Define nodes

# Define the function that calls the model
def call_model(state):
    messages = state["messages"]
    response = model.invoke(messages)
    assert len(response.tool_calls) <= 1
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}

# We define a fake node to ask the human
def ask_human(state):
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    location = interrupt("Say something:")
    tool_message = [{"tool_call_id": tool_call_id, "type": "tool", "content": location}]
    return {"messages": tool_message}


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

# Not sure if this is needed or not idc
LANGSMITH_TRACING = os.getenv('LANGSMITH_TRACING')
LANGSMITH_ENDPOINT = os.getenv('LANGSMITH_ENDPOINT')
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')
LANGSMITH_PROJECT = os.getenv('LANGSMITH_PROJECT')

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

from nodes.tools import (
    create_calendar_event,
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

    return Command(
        update={
            # update the message history
            "messages": [ToolMessage("Successfully looked up user information", tool_call_id=z)]
        }
    )
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    location = interrupt("Say something:")
    tool_message = [{"tool_call_id": tool_call_id, "type": "tool", "content": location}]
    return {"messages": tool_message}



from typing import TypedDict
import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command

class State(TypedDict):
   """The graph state."""
   some_text: str

def human_node(state: State):
   value = interrupt(
      # Any JSON serializable value to surface to the human.
      # For example, a question or a piece of text or a set of keys in the state
      {
         "text_to_revise": state["some_text"]
      }
   )
   return {
      # Update the state with the human's input
      "some_text": value
   }


# Build the graph
graph_builder = StateGraph(State)
# Add the human-node to the graph
graph_builder.add_node("human_node", human_node)
graph_builder.add_edge(START, "human_node")

# A checkpointer is required for `interrupt` to work.
checkpointer = MemorySaver()
graph = graph_builder.compile(
   checkpointer=checkpointer
)

# Pass a thread ID to the graph to run it.
thread_config = {"configurable": {"thread_id": uuid.uuid4()}}



# Using stream() to directly surface the `__interrupt__` information.
for chunk in graph.stream({"some_text": "Original text"}, config=thread_config):
   print(chunk)

# Resume using Command
for chunk in graph.stream(Command(resume="Edited text"), config=thread_config):
   print(chunk)


def human(state: MessagesState) -> Command[Literal["agent", "another_agent"]]:
    """A node for collecting user input."""
    user_input = interrupt(value="Ready for user input.")

    # Determine the active agent.
    active_agent = ...

    ...
    return Command(
        update={
            "messages": [{
                "role": "human",
                "content": user_input,
            }]
        },
        goto=active_agent
    )

def agent(state) -> Command[Literal["agent", "another_agent", "human"]]:
    # The condition for routing/halting can be anything, e.g. LLM tool call / structured output, etc.
    goto = get_next_agent(...)  # 'agent' / 'another_agent'
    if goto:
        return Command(goto=goto, update={"my_state_key": "my_state_value"})
    else:
        return Command(goto="human") # Go to human node
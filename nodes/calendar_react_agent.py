#!/usr/bin/env python3
import pytz
"""
This script creates an interactive calendar reAct agent using LangChain and LangGraph.
The agent assists users with creating calendar events through natural language
conversations. It greets the user initially and then prompts dynamically for input.
"""

import os
import json
from dotenv import load_dotenv
from typing import Annotated, Sequence, TypedDict, Dict, Optional
from IPython.display import Image
import datetime
import logging

# Set up logging (change level to INFO to disable debug prints)
logging.basicConfig(level=logging.INFO)

# Import required modules from LangChain and LangGraph.
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langchain.callbacks import StdOutCallbackHandler

from pydantic import BaseModel, ValidationError

# Optionally import IPython display functionality for graph visualization.
try:
    from IPython.display import Image, display
except ImportError:
    Image = None
    display = None

from tools import (
    create_calendar_event,
    CreateCalendarEventModel
)

# =============================================================================
# Environment Setup
# =============================================================================

# Load environment variables from the .env file (make sure it contains OPENAI_API_KEY).
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# -----------------------------------------------------------------------------
# Initialize ChatOpenAI Instances
# -----------------------------------------------------------------------------

# General LLM instance (not directly used in the agent below).
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    max_tokens=100,
    api_key=OPENAI_API_KEY
)

# Initialize the model for the calendar agent using a different model.
model = ChatOpenAI(model="gpt-4o-mini")

# =============================================================================
# Define Agent State and Dummy Calendar Tool
# =============================================================================

class AgentState(TypedDict):
    """The state of the calendar agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]

# Honstly fuck you im hard coding time zone 
@tool
def get_current_datetime():
    """
    Return the current date and time in ISO 8601 format using Mountain Time (America/Denver).
    """
    tz = pytz.timezone("America/Denver")
    now = datetime.datetime.now(tz).isoformat()

    print("asdfasdf")

    return now


# Bind the dummy tool to the model.
tools = [create_calendar_event, get_current_datetime]
model = model.bind_tools(tools)

# Create a mapping of tool names to tool functions for easy lookup.
tools_by_name = {tool.name: tool for tool in tools}

# =============================================================================
# Define State Graph Nodes and Edges
# =============================================================================

def tool_node(state: AgentState):
    """
    Node that processes tool calls.
    
    It iterates over tool calls in the last message, invokes the corresponding
    dummy tool, and returns the tool responses as messages.
    """
    outputs = []
    for tool_call in state["messages"][-1].tool_calls:
        tool_result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
        outputs.append(
            ToolMessage(
                content=json.dumps(tool_result),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
    return {"messages": outputs}

def call_model(state: AgentState, config: RunnableConfig):
    """
    Node that calls the language model.
    
    The system prompt has been updated to reflect the calendar assistant role.
    """
    system_prompt = SystemMessage(
        """
        You are a helpful calendar assistant whose job is to help users create and manage calendar events. When interacting with the user, follow these guidelines:
        USE MOUNTAINT TIME YOU JEW
        1. **Structured Event Details:**  
        Collect event details in a JSON object with the following keys:
        - "topic" (Mandatory): A brief topic for the event.
        - "start_time" (Mandatory): The event's start time, which must be in ISO 8601 format.
        - "end_time" (Optional): The event's end time in ISO 8601 format.
        - "location" (Optional): The location of the event.
        - "description" (Optional): Any additional information.

        2. **Handling Relative Time Expressions:**  
        You a should always use MST. The time tool will return MST, and the event and user are in MST.
        If the user mentions a relative time expression (e.g., "3 days from now", "tomorrow at 10am"), first call the `get_current_datetime` tool to get the current time. Then, use that reference to calculate the absolute time and update the event details accordingly by calling `update_event_details_tool`.

        3. **State Updates:**  
        Incrementally update the event details as new details are provided. If the event details are incomplete or ambiguous, ask the user for clarification rather than calling the `create_calendar_event` tool.

        3.5 **User Confirmation:** Before calling the `create_calendar_event` tool, confirm the event details with the user.
        The user must confirm the event details before proceeding to use the tool create_calendar_event.

        4. **Event Creation:**
        Only when both mandatory fields ("topic" and "start_time") are filled and user confirmation is complete, call the `create_calendar_event` tool to finalize the event creation.
        When you are ready to create the event, call the tool with a JSON object structured as:
        {"event_details": { ... }} containing all Structured Event Details.

        5. **Tool Invocation:**  
        - Use `get_current_datetime` to retrieve the current time.
        - Use,  `create_calendar_event` ONLY when all required information is available AND you have asked confirmation from the user and the user has confirmed.
        - Apart from these tools, you have no other tools available in this conversation. Do not make faulty tool calls that are not part of the calendar assistant's workflow.

        6. **Conversation Termination:**  
        Monitor the conversation for cues that the user is trying to end the interaction. If the user expresses farewell phrases (e.g., "bye", "exit", "thank you, I'm done", etc.) or clearly indicates that no further assistance is needed, gracefully end the conversation.

        Your responses should guide the conversation by collecting necessary details, making appropriate tool calls, and clearly instructing the user when additional information is needed. Ensure that you also decide when the conversation should conclude based on the user's input.
        """
    )
    if not state["messages"]:
        messages = [system_prompt]
    else:
        messages = state["messages"]
    
    response = model.invoke(messages, config)
    
    return {"messages": [response]}


def should_continue(state: AgentState):
    """
    Determine whether to continue processing the conversation.
    
    If the last message does not include any tool calls, then the conversation cycle ends.
    (In interactive mode, control is passed back to the user prompt.)
    """
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"

# =============================================================================
# Helper Function to Print the Output Stream
# =============================================================================

def print_message(message):
    """
    Helper function to print a single message.
    """
    if isinstance(message, tuple):
        # In case of a tuple, print directly.
        print(message)
    elif hasattr(message, "pretty_print"):
        message.pretty_print()
    else:
        print(message)

# =============================================================================
# Main Execution: Interactive Conversation Loop
# =============================================================================

def main():
    """
    Main function to build and run the interactive calendar agent.
    The agent greets the user first and then dynamically prompts for user input.
    """
    # Build the state graph.
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",
            "end": END,
        },
    )
    workflow.add_edge("tools", "agent")
    
    # Compile the workflow into an executable graph.
    graph = workflow.compile()
    
    # Initialize conversation state with an empty messages list.
    state = {"messages": []}
    
    # Generate initial greeting from the agent.
    print("Agent is thinking...")
    initial_stream = graph.stream(state, stream_mode="values")
    for output in initial_stream:
        for msg in output.get("messages", []):
            print("Agent:", end=" ")
            print_message(msg)
            state["messages"].append(msg)
    
    # Interactive conversation loop.
    while True:
        user_input = input("User: ")
        if user_input.strip().lower() in ["exit", "quit", "bye"]:
            print("Agent: Goodbye!")
            break
        
        # Append the user's message to the state.
        state["messages"].append(("user", user_input))
        
        # Process the updated conversation through the graph.
        agent_stream = graph.stream(state, stream_mode="values")
        for output in agent_stream:
            for msg in output.get("messages", []):
                print("Agent:", end=" ")
                print_message(msg)
                state["messages"].append(msg)

if __name__ == "__main__":
    main()

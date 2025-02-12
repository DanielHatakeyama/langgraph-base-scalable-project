"""
Calendar Agent
Example of an agent that dynamically gathers calendar event details via LLM-driven interaction.
The agent stores a partial event form in state, queries the human for missing details, updates
the form using LLM prompts, and once complete asks for confirmation before calling the calendar event tool.
"""

from typing_extensions import TypedDict, Annotated  # For Pydantic state and reducer functions
from langgraph.graph.message import add_messages       # For streamlining message handling

from langchain_core.messages import AnyMessage, AIMessage, HumanMessage
from langgraph.graph import MessagesState, START, END, StateGraph
from pydantic import BaseModel
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime

# -------------------------------
# Import our tools and models from tools.py
# -------------------------------
from tools import (
    create_calendar_event_tool,
    get_current_time_tool,
    CreateCalendarEventInputModel
)

# Load environment variables and set up the language model
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    max_tokens=150,
    api_key=OPENAI_API_KEY
)

# -------------------------------
# Define additional helper classes
# -------------------------------
class AskHuman(BaseModel):
    """Pydantic model to ask the human a question."""
    question: str

# -------------------------------
# Set up tools and tool binding
# -------------------------------
tools = [create_calendar_event_tool, get_current_time_tool]
tool_node = ToolNode(tools)
# Bind our tools plus AskHuman so that the LLM may produce tool calls.
model = llm.bind_tools(tools + [AskHuman])

# -------------------------------
# Define a helper for human input.
# -------------------------------
def interrupt(prompt: str) -> str:
    """Simulate a human prompt by reading input from the console."""
    return input(prompt)

# -------------------------------
# Dynamic Gathering Nodes Using the Agent
# -------------------------------
def ask_missing_field(state):
    """
    Use the LLM to dynamically generate a clarifying question for the first missing field.
    The agent is provided with the current event_data and asked to produce a natural question.
    The output message includes a tool call with name "AskHuman" and the missing field in its parameters.
    """
    event_data = state.get("event_data", {})
    required_fields = ["topic", "start_time", "end_time"]
    missing_fields = [f for f in required_fields if f not in event_data or not event_data[f]]
    if not missing_fields:
        # Nothing is missing; return the state unmodified.
        return {"messages": state["messages"]}
    field = missing_fields[0]
    system_prompt = (
        f"You are an assistant that gathers calendar event details. The required field is '{field}'.\n"
        f"The current event details are: {event_data}\n"
        f"Ask the user a natural, clarifying question to obtain the value for '{field}'."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Generate the clarifying question."}
    ]
    response = llm.invoke(messages)
    question_text = response.content.strip()
    new_message = AIMessage(content=question_text)
    new_message.tool_calls = [{"id": "ask_missing", "name": "AskHuman", "parameters": {"field": field}}]
    state["messages"].append(new_message)
    return {"messages": state["messages"]}

def update_event_data(state):
    """
    After receiving the human's answer in natural language, use the LLM to parse and update the event_data.
    The system prompt provides the current event_data, the current time, and the human's natural language answer.
    The LLM is instructed to extract structured details for 'topic', 'start_time', and 'end_time'.
    Expected output is a JSON object with the updated fields.
    """
    event_data = state.get("event_data", {})
    human_answer = state["messages"][-1].content.strip()
    current_time_str = datetime.now().isoformat()
    system_prompt = (
        "You are an assistant that extracts structured calendar event details from a natural language description.\n"
        f"Current time: {current_time_str}\n"
        f"Existing event details: {event_data}\n"
        f"User description: \"{human_answer}\"\n"
        "Extract and update the following fields if present: topic, start_time, end_time.\n"
        "For any relative time expressions (like 'tomorrow at 2pm'), convert them to absolute ISO 8601 datetime strings.\n"
        "Return only a JSON object with the updated fields. For example: "
        "{\"topic\": \"Feed the dogs\", \"start_time\": \"2025-02-12T14:00:00\", \"end_time\": \"2025-02-12T15:00:00\"}."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Extract the event details."}
    ]
    response = llm.invoke(messages)
    try:
        update_dict = json.loads(response.content)
    except Exception as e:
        update_dict = {}  # Fallback: do not update if parsing fails.
    event_data.update(update_dict)
    state["event_data"] = event_data
    new_message = AIMessage(content=f"Event details updated: {event_data}")
    new_message.tool_calls = [{"id": "update_event", "name": "FillEventDetails", "parameters": event_data}]
    state["messages"].append(new_message)
    return {"messages": state["messages"]}

def gather_event_details(state):
    """
    If event_data is complete, attempt to validate it.
    On successful validation, transform the event_data into a tool call for final confirmation.
    If validation fails, remove the problematic field and allow further gathering.
    """
    event_data = state.get("event_data", {})
    required_fields = ["topic", "start_time", "end_time"]
    if any(field not in event_data or not event_data[field] for field in required_fields):
        return {"messages": state["messages"]}
    else:
        try:
            # Convert start_time and end_time from strings to datetime if necessary.
            if isinstance(event_data["start_time"], str):
                event_data["start_time"] = datetime.fromisoformat(event_data["start_time"])
            if isinstance(event_data["end_time"], str):
                event_data["end_time"] = datetime.fromisoformat(event_data["end_time"])
            validated = CreateCalendarEventInputModel(**event_data)
        except Exception as e:
            # On validation error, remove the problematic field (here, for simplicity, 'end_time').
            event_data.pop("end_time", None)
            state["event_data"] = event_data
            new_message = AIMessage(content=f"Validation error: {e}. Let's re-collect the value for end_time.")
            new_message.tool_calls = [{"id": "remove_invalid", "name": "FillEventDetails", "parameters": event_data}]
            state["messages"].append(new_message)
            return {"messages": state["messages"]}
        # Validation succeeded. Create a message that transforms the state into a final tool call.
        new_message = AIMessage(content=f"Final event details: {validated.dict()}")
        new_message.tool_calls = [{"id": "confirm_event", "name": "create_calendar_event_tool", "parameters": validated.dict()}]
        state["messages"].append(new_message)
        return {"messages": state["messages"]}

def confirm_calendar_event(state):
    """
    Ask the human to confirm the complete event details.
    If confirmed, call the calendar event tool using the parameters.
    """
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    params = {}
    if tool_calls and len(tool_calls) > 0:
        params = tool_calls[0].get("parameters", {})
    confirmation = interrupt(f"Please confirm the event details {params} (yes/no): ")
    if confirmation.lower() in ["yes", "y"]:
        result = create_calendar_event_tool(params)
        state["messages"].append(AIMessage(content=result))
    else:
        state["messages"].append(HumanMessage(content="Event creation cancelled. Please modify the event details."))
    return {"messages": state["messages"]}

# -------------------------------
# Routing Function (safely checking for tool_calls)
# -------------------------------
def should_continue(state):
    """
    Decide which node to visit next:
      - If event_data is incomplete, then:
          • if the last message has a tool call named "AskHuman", go to 'ask_human';
          • if the last message has a tool call named "FillEventDetails", go to 'update_event_data';
          • otherwise, go to 'ask_missing_field'.
      - If event_data is complete and the last tool call is create_calendar_event_tool,
        go to 'confirm_calendar_event'.
      - Otherwise, finish.
    """
    messages = state["messages"]
    event_data = state.get("event_data", {})
    required_fields = ["topic", "start_time", "end_time"]
    if any(field not in event_data or not event_data[field] for field in required_fields):
        if messages:
            last_msg = messages[-1]
            tool_calls = getattr(last_msg, "tool_calls", None)
            if tool_calls and len(tool_calls) > 0:
                last_tool = tool_calls[0]["name"]
                if last_tool == "AskHuman":
                    return "ask_human"
                elif last_tool == "FillEventDetails":
                    return "update_event_data"
        return "ask_missing_field"
    if messages:
        last_msg = messages[-1]
        tool_calls = getattr(last_msg, "tool_calls", None)
        if tool_calls and len(tool_calls) > 0:
            if tool_calls[0]["name"] == "create_calendar_event_tool":
                return "confirm_calendar_event"
    return END

# -------------------------------
# Build the state graph workflow
# -------------------------------
workflow = StateGraph(MessagesState)
# 'agent' simply passes messages onward; subsequent nodes update state.
workflow.add_node("agent", lambda state: {"messages": state["messages"]})
workflow.add_node("ask_missing_field", ask_missing_field)
workflow.add_node("ask_human", lambda state: {"messages": [HumanMessage(content=interrupt("The agent requests additional input: "))]})
workflow.add_node("update_event_data", update_event_data)
workflow.add_node("gather_event_details", gather_event_details)
workflow.add_node("confirm_calendar_event", confirm_calendar_event)
workflow.add_node("action", tool_node)
workflow.add_node("call_model", lambda state: {"messages": [model.invoke(state["messages"][-2:])]} )

# Set the entrypoint to 'agent'
workflow.add_edge(START, "agent")
# Route based on the current state.
workflow.add_conditional_edges("agent", should_continue)
# Loop back from nodes to agent for the next iteration.
workflow.add_edge("ask_missing_field", "agent")
workflow.add_edge("ask_human", "agent")
workflow.add_edge("update_event_data", "agent")
workflow.add_edge("gather_event_details", "agent")
workflow.add_edge("confirm_calendar_event", "agent")
workflow.add_edge("action", "agent")
workflow.add_edge("call_model", "agent")

# Set up memory checkpointing
memory = MemorySaver()

# Compile the workflow into a LangChain Runnable
app = workflow.compile(checkpointer=memory)

# Configuration for streaming execution (example thread_id "2")
config = {"configurable": {"thread_id": "2"}}

# -------------------------------
# Execute the workflow
# -------------------------------
initial_state = {
    "messages": [
        HumanMessage(content="I want to schedule a meeting. Please help me create a calendar event.")
    ],
    "event_data": {}  # start with an empty event form
}

for event in app.stream(initial_state, config, stream_mode="values"):
    event["messages"][-1].pretty_print()

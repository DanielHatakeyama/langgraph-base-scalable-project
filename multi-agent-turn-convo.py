#!/usr/bin/env python
"""
Human-in-the-Loop Chatbot Example using LangGraph with OpenAI and Pydantic

This script demonstrates a LangGraph chatbot that can request human assistance
when needed. It uses an interrupt to pause execution and then resumes when a human 
provides input. The graph's state is defined using a Pydantic BaseModel for runtime 
validation.

Before running, create a `.env` file in the same directory with your API keys:
    OPENAI_API_KEY=<your_openai_api_key>
    TAVILY_API_KEY=<your_tavily_api_key>

Required packages:
    - python-dotenv
    - langgraph
    - langchain_openai
    - tavily-python
    - langchain_community
    - pydantic>=2
"""
import uuid
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Loop through required environment variables.
required_env_vars = ["OPENAI_API_KEY", "TAVILY_API_KEY"]
for var in required_env_vars:
    value = os.getenv(var)
    if not value:
        raise ValueError(f"Please set {var} in your .env file.")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Not sure if this is needed or not idc
LANGSMITH_TRACING = os.getenv('LANGSMITH_TRACING')
LANGSMITH_ENDPOINT = os.getenv('LANGSMITH_ENDPOINT')
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')
LANGSMITH_PROJECT = os.getenv('LANGSMITH_PROJECT')

# Imports from LangGraph and related libraries
from typing import Annotated, Any, List
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool



# Define the overall state of the graph using a Pydantic model.
# Here, we use Annotated to apply the add_messages reducer.
class OverallState(BaseModel):
    messages: Annotated[List[Any], add_messages] = Field(default_factory=list)

# Build the state graph using the Pydantic model as the state schema.
graph_builder = StateGraph(OverallState)

# Define a human assistance tool that uses interrupt to pause execution.
# @tool
# def human_assistance(query: str) -> str:
#     """Ask a query to a human. You will get a human response back as feedback."""
#     print(f"[Human Assistance Requested] Query: {query}")
#     # This will pause execution until a resume Command is provided.
#     human_response = interrupt({"query": query})
#     return human_response["data"]

class AskHuman(BaseModel):
    """Ask the human a question"""
    question: str

# Instantiate the search tool and add the human assistance tool.
search_tool = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=False
)

tools = [search_tool]
tool_node = ToolNode(tools)

# Initialize the LLM (OpenAI) and bind the tools.
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5,
    api_key=OPENAI_API_KEY
)
llm_with_tools = llm.bind_tools(tools + [AskHuman])

# Define the chatbot node function.

def chatbot(state: OverallState):
    message = llm_with_tools.invoke(state.messages)
    # Disable parallel tool calling to avoid duplicate tool calls on resume.
    # if hasattr(message, "tool_calls"):
    #     assert len(message.tool_calls) <= 1
    return {"messages": [message]}

def human(state: OverallState):
    """Human Node"""
    print("---human_feedback---")
    feedback = interrupt("Please provide feedback:")
    return {"messages": [feedback]}

# We define a fake node to ask the human
def ask_human(state):
    tool_call_id = state.messages[-1].tool_calls[0]["id"]
    tool_call_1 = state.messages[-1].tool_calls[0]
    feedback = interrupt(tool_call_1)
    tool_message = [{"tool_call_id": tool_call_id, "type": "tool", "content": feedback}]
    return {"messages": tool_message}

def should_continue(state):
    messages = state.messages
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
        return "tools"


# Add the chatbot node to the graph.
graph_builder.add_node("agent", chatbot)
graph_builder.add_node("ask_human", ask_human)
# Add a tool node to handle tool calls.
graph_builder.add_node("tools", tool_node)

# Set conditional routing: if a tool call is made, route to the tools node.
graph_builder.add_conditional_edges("agent", should_continue)
graph_builder.add_edge("tools", "agent")
graph_builder.add_edge("ask_human", "agent")
graph_builder.add_edge(START, "agent")

# Compile the graph with an in-memory checkpointer for state persistence.
memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)

# # Utility function to print out messages from graph events.
# def print_events(events):
#     for event in events:
#         messages = event.get("messages", [])
#         for msg in messages:
#             content = getattr(msg, "content", str(msg))
#             print(f"Assistant: {content}")

def get_human_feedback(query):
    print("Human Query:")
    return input(f"{query}\n\nUser:")

def main():

    system_prompt = """
    Have a conversation with the user. Use the AskHuman tool to communicate until they say the phrase "stop".
    """

    initial_state = {"messages": [{"role": "system", "content": system_prompt}]}
    thread = {"configurable": {"thread_id": "1"}}

    
    # Run graph until an interruption or end:
    for event in graph.stream(initial_state, thread, stream_mode="updates"):
        print(f"event: {event}")

        # Check for human interrupt
        if '__interrupt__' in event:
            interrupt = event['__interrupt__'][0]
            if interrupt.value.get('name') == 'AskHuman':
                # Retrieve the question from the interrupt args
                question = interrupt.value.get('args', {}).get('question')
                print("Detected AskHuman interrupt!")
                print("Question:", question)
    
    while (True):

        last_message = graph.get_state(thread).values['messages'][-1]
        print(f"last_message = \n{last_message}")
        human_feedback = get_human_feedback(last_message)

        graph.invoke(Command(resume=human_feedback), thread, stream_mode="updates")
    
    # graph.invoke(initial_state, thread)
    # If reach here, the graph had an interruption, or i guess i could have had an error or ended too...
    



# def main():
#     # Configuration with a thread_id to enable checkpointing (i.e. conversation memory).
#     config = {"configurable": {"thread_id": str(uuid.uuid4())}}

#     system_prompt = """
#         You will converse with the human assistant using the human_assistance tool about whatever topic that they choose.
#         If it would help to do research, which you almost always do before responding to the human, use the search tool
#         and then respond with a more educated and better answer, which is your goal to provide. 
#     """
#     initial_payload = {"messages": [{"role": "system", "content": system_prompt}]}

#     # Start the conversation by streaming events from the graph.
#     events = graph.stream(initial_payload, config, stream_mode="values")
#     print("\nAssistant responses:")
#     print_events(events)
    

#     while(True):
#         snapshot = graph.get_state(config)
#         messages = snapshot.values.get("messages", [])
#         if messages:
#             last_message = messages[-1]
#             # Check if the last message includes any tool calls.
#             if hasattr(last_message, "tool_calls") and last_message.tool_calls:
#                 # Look for a specific tool call by name.
#                 for call in last_message.tool_calls:
#                     if call.get("name") == "human_assistance":
#                         print("\n[Graph is waiting for a human_assistance tool call.]")
#                         human_input = input("Enter your human assistance response: ")
#                         # Create a Command to resume execution with the human's input.
#                         from langgraph.types import Command
#                         human_command = Command(resume={"data": human_input})
#                         events = graph.stream(human_command, config, stream_mode="values")
#                         print_events(events)
#                         break
        

if __name__ == "__main__":
    main()

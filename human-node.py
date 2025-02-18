import uuid
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Only need to use these if you are tracing the output on langsmit (its worth setting up)
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

# Define Pydantic Models
class OverallState(BaseModel):
    messages: Annotated[List[Any], add_messages] = Field(default_factory=list)

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


# Define the agent node function.
def chatbot(state: OverallState):
    message = llm_with_tools.invoke(state.messages)
    # Disable parallel tool calling to avoid duplicate tool calls on resume.
    # if hasattr(message, "tool_calls"):
    #     assert len(message.tool_calls) <= 1
    return {"messages": [message]}

# Ask human node
def ask_human(state):
    tool_call_id = state.messages[-1].tool_calls[0]["id"]
    tool_call_1 = state.messages[-1].tool_calls[0]
    feedback = interrupt(tool_call_1)
    tool_message = [{"tool_call_id": tool_call_id, "type": "tool", "content": feedback}]
    return {"messages": tool_message}

# Conditional edge 
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

graph_builder = StateGraph(OverallState)

# Add nodes to graph
graph_builder.add_node("agent", chatbot)
graph_builder.add_node("ask_human", ask_human)
graph_builder.add_node("tools", tool_node)

# Set graph edges - Note the conditional edge from agent using should continue function.
graph_builder.add_conditional_edges("agent", should_continue)
graph_builder.add_edge("tools", "agent")
graph_builder.add_edge("ask_human", "agent")
graph_builder.add_edge(START, "agent")

# Compile the graph with an in-memory checkpointer for state persistence.
memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)

def get_human_feedback(query):
    print("Human Query:")
    return input(f"{query}\n\nUser:")

def main():

    system_prompt = """
    Have a conversation with the user. Use the AskHuman tool to communicate until they say the phrase "stop". Be sure to be a helpful assistant, and use the search tool if external information from the internet might be helpful as context before responding to the user.
    """

    initial_state = {"messages": [{"role": "system", "content": system_prompt}]}
    thread = {"configurable": {"thread_id": "1"}}

    graph.invoke(initial_state, thread)
     
    while (True):

        last_message = graph.get_state(thread).values['messages'][-1]
        # question = last_message["tool_calls"][0]["args"]["question"]
        question = __import__("json").loads(last_message.additional_kwargs.get("tool_calls", [{}])[0].get("function", {}).get("arguments", "{}")).get("question")

        if (question is None): 
            print("No query to user, likely agent routed to end, possible bug")
            break
        
        human_feedback = get_human_feedback(question)
        graph.invoke(Command(resume=human_feedback), thread, stream_mode="updates")
    
if __name__ == "__main__":
    main()

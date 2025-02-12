
# Probably wont need this once it is well setup.
from typing_extensions import TypedDict # Pydantic state
from typing_extensions import Annotated # For reducer function
from langgraph.graph.message import add_messages # For streamlining the reducer function for messages

# Refactor this later to be nicer and all one line for all langgraph.graph imports.
from langgraph.graph import StateGraph # Langgraph graph object. Explore if other graph objects are better or if there is a general one to go with.
from langgraph.graph import START # For specifying the start node in a graph object

# Local Imports
from nodes.agents import *

print("Running Main.py")

# Assemble Graph 
graph_builder = StateGraph(State)
graph_builder.add_node(ai_message)
graph_builder.add_edge(START, "ai_message") # This is equivalent to add_edge(START, "node"), I believe.

graph_builder.add_edge("ai_message", "human_input")

graph_builder.add_node(human_input)
graph_builder.add_edge("human_input", "ai_message")


graph_builder.add_node(human_input_escape)
graph_builder.add_conditional_edges("human_input", "human_input_escape", "system_message", lambda state: state["messages"][0].content == "exit")


graph = graph_builder.compile()

# Run Graph
message_1 = {"role": "system", "content": "Make sure that all responses are only in spanish."}
message_2 = {"role": "user", "content": "Hi"}

result = graph.invoke({"messages": [message_1, message_2]})

# Print output
print(f"result = {result}\n")
for message in result["messages"]:
    message.pretty_print()


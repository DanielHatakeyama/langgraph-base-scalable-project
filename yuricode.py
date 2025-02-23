from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt
from pydantic import BaseModel
from typing import List, Optional, Literal

# Define the state with required updates
class GoalState(BaseModel):
    user_messages: List[str] = []
    follow_up_questions: List[str] = []
    goal_statement: Optional[str] = None
    satisfied: bool = False

# Set up ChatGPT and Memory
chat_model = ChatOpenAI(model="gpt-4o", temperature=0.7)
conversation_memory = ChatMessageHistory()

# Human node: Collect user input
def human_node(state: GoalState) -> Command[Literal["goal_alignment"]]:
    """Interrupt execution to collect user input and ensure state updates."""

    # Interrupt to collect user input
    user_input = interrupt("Waiting for user input...")

    # Store input properly
    conversation_memory.add_user_message(user_input)
    state.user_messages.append(user_input)

    return Command(
        update={"user_messages": state.user_messages},
        goto="goal_alignment"
    )

# Goal alignment node
def goal_alignment_node(state: GoalState) -> Command[Literal["human", "final_goal"]]:
    """Uses LLM to refine the user's goal and ensures updates."""

    if not state.user_messages:
        return Command(
            update={"follow_up_questions": ["I didn't receive any input."]},
            goto="human"
        )

    # Generate LLM response
    chat_input = "\n".join(state.user_messages)
    response = chat_model.predict(chat_input)

    # Ensure state updates
    return Command(
        update={
            "goal_statement": response,
            "satisfied": True
        },
        goto="final_goal"
    )

# Final goal confirmation node
def final_goal_node(state: GoalState) -> Command[Literal[END]]:
    """Returns the finalized goal statement, or asks for clarification."""

    if state["satisfied"] and state["goal_statement"]:
        print(f"Goal finalized: {state['goal_statement']}")
        return Command(goto=END)

    return Command(
        update={"follow_up_questions": ["Can you clarify your goal?"]},
        goto="human"
    )

# Build the LangGraph system
goal_graph = StateGraph(GoalState)

# Add nodes
goal_graph.add_node("human", human_node)
goal_graph.add_node("goal_alignment", goal_alignment_node)
goal_graph.add_node("final_goal", final_goal_node)

# Define graph flow
goal_graph.add_edge(START, "human")  # Start with user input
goal_graph.add_edge("human", "goal_alignment")  # Process input
goal_graph.add_edge("goal_alignment", "final_goal")  # Finalize goal
goal_graph.add_edge("goal_alignment", "human")  # Ask again if needed
goal_graph.add_edge("final_goal", END)  # End process

# Compile graph
goal_executor = goal_graph.compile()

# Example Run
initial_state = GoalState(user_messages=["I need help with a project"])
final_state = goal_executor.invoke(initial_state)

# Access response correctly
response = final_state.get("goal_statement", "No goal statement generated")
print(response)

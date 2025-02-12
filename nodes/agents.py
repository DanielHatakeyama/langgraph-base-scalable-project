from typing_extensions import TypedDict # Pydantic state
from typing_extensions import Annotated # For reducer function
from langgraph.graph.message import add_messages # For streamlining the reducer function for messages

from langchain_core.messages import AnyMessage # Langchain anymessage, check this out. AIMessage and HumanMessage are subclasses of this.
from langchain_core.messages import AIMessage # For specifying an AI message.
from langchain_core.messages import HumanMessage # For specifying a human message.

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, max_tokens=100, api_key=OPENAI_API_KEY)


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    extra_field: int
    user_feedback: str


def ai_message_hi(state: State):
    new_message = AIMessage("Hello!")
    return {"messages": [new_message]}

def ai_message(state: State):
    new_message = llm.invoke(state["messages"])
    print(state["messages"])
    return {"messages": [new_message]}

def system_message(state: State): 
    system_message = "Only speak in spanish for now on."
    return {"messages": [system_message]}

def human_input(state: State):
    user_text = input("Please enter your message: ")
    new_message = HumanMessage(user_text)

    # Check for exit, quit, break, etc.

    return {"messages": [new_message]}

human_input_gate

# TODO figure out extra field what can use stuff like that for.

# TODO Need solution for state management and automation.

# TODO: State managmenent could be done with substate worlds. Give a certain domain a substate to work with and this is automatically registered and handled in the global state
# TODO: Main problem is that this should be able to work with reducer functions. Not sure how to do this right now, but it should be possible without a huge monolith.
# TODO: 
# TODO MAKE THIS README CLOSER TO ACTUAL PROJECT DESCRIPTION



Okay as of reflecting:


python double package and subclass for agent and tools
each agent requires pydantic input and output
has a robust way to concatenate different pydantic instances into a singular state at runtime.
this lets matching happen much more easily and flexiblly, this way additional input checks that are custom to each agent or tool can be used.
GOal is to ensure that no mistakes and mismatches can happen with agent to agent to tool to tool io. 
tool boxes can be made with this magical concatenation function.

make sure to consider when will a tool be used individually as a node
or when will a tool be compiled into a tool box and how will it be used then
extra interfacing on tool boxes? or a toolbox abstraction helper:
- Toolbox abstraction helper

all nodes are composed of at the minimum (characterize with langgraph)

input set
transformation
output set


Now that i have thought about this further here are some ideas for the final structure:

1. Workflows, tools, agents: all sub classed of node. Node has some common features and imports, but nothing heavy except some function accessability potentially.
2. Workflows, stored as subprocesses are what all complex systems are built on top of. The abstraction process can go on in other ways--a langgraph agentic node saved as a single workflow could recursively happen until you have the entire program in a single runnable node. This composition may be either good or bad, depending on how it is implemented. A rule of keeping workflows as simple, understandable, deterministic, reusable. Documentation would be extensive so that the AI could dynamically compose itself.
3. Some processes that should be supported in this architecture.

a. Normalizer workflow -- Given context, fill in a state s, through repeated tooling.
b. workflow: get_tool(tool_box) -> tool
c. workflow: gate(context, pass-fail-condition) -> (state, pass / fail) / evaluator(context, mission) -> (bool, state) / agent-if-else(context, condition) -> bool !Figure out details of how these work: built off a agent that does the action, but generalized for input. Agent takes state in and state out and transforms. This means that there will be a specific attachment to state for each of these calls that will be quote(returned) as output. There can be additional wrappers to actually make these workflows behave differently than other workflows to be injected directly into a if else block. Because they do have to return something that is not state but also ALL OF THE WORKSPACES SHOULD ONLY NEED A LOCAL CONTEXT, BUT ALSO NOT REALLY IF IT WOULD BE UNNECCESSARILY COMPLICATED TO IMPLEMENT
d. workflow: router(context, options)
e. abstract classes sorta things 
f. composition of many little pieces (lego pyramid)
g. workflow: quote(refinement) can be done like in R-learning by trying same output multiple times and checking aggreement to increase confidence. Specific modifications to this process of refinement can maybe induce actual refinement, since accessing a longer context window of previous solutions can help aid the final composition step well.
h. workflow: fetch_tools(contexxt)->toolbox ?
i. workflow: check_tools(context) -> do all tools with normalized input to json and actually do work unless you cant then false i guess.or just check which tools you are considering useing or have already used and the state of t
j. continued THE LOCAL CONTEXT SCOPE OF A LITTLE SUBGRAPH AGENT THAT WILL GET INPUT AND RECURSIVELY FILL OUT A EMPTY STATE THAT ACTS AS PlACE FOR IT TO FILL INTERMEDIATE ANSWERS.
k. This thing will loop until the whole thing is filled out in order!
l. Force use tools as a boolean


LOGGING DYNAMICALLY AND EASILY


4. This seems like a very component based approach. Building from the ground up, renaming new things, and using them to build more. Nodes could be extremely complex in this architecture, but resuable and very testable.















# LangGraph + Google Calendar Integration

A lightweight but scalable project template that integrates LangGraph (or LangChain-based workflows) with Google Calendar using Python.

## Overview

This repository demonstrates how to set up:

- Google OAuth Authentication for programmatic calendar access.
- LangGraph to orchestrate workflows (Graph API approach).
- Pydantic for robust tool input validation.
- Tools that create Google Calendar events.

It’s structured to make it easy to expand with more tools, subgraphs, and additional functionality.

## Features

- **Google Calendar Integration**: A tool (`create_calendar_event`) that creates an event in your calendar via Google’s API.
- **LangGraph Workflow**: A sample graph that calls the tool and returns a final state.
- **Pydantic Validation**: Ensures correct data formats for start/end times.
- **Modular Architecture**: Separate folders for auth, tools, models, and graph.
- **Scalable**: Easily add more tools or subgraphs as your project grows.

## Installation & Setup

### Prerequisites

- Python 3.8+ recommended.
- A Google Cloud Project with the Calendar API enabled.
- Client Credentials for an OAuth client (downloaded JSON or environment-based credentials).
- A `.env` file for storing client secrets and other environment variables.
- Optional but recommended: a virtual environment to keep dependencies isolated.

### Step 1: Clone the Repository

```
git clone <your-repo-url>
cd <repo-folder>
```

### Step 2: Create and Activate a Virtual Environment

```
python -m venv venv  # or python3, depending on your system
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

### Step 3: Install Dependencies

```
pip install -r requirements.txt
```

Typical dependencies include:

- langgraph
- langchain
- google-auth-oauthlib
- google-api-python-client
- pydantic
- python-dotenv

### Step 4: Environment Configuration

Create a `.env` file in the project root and include secret variables for google and your LLM.

```
OPEN_AI_KEY=Blah blah blah
GOOGLE_CLIENT_ID=<YOUR_CLIENT_ID>
GOOGLE_CLIENT_SECRET=<YOUR_CLIENT_SECRET>
GOOGLE_REDIRECT_URI=http://localhost
```

### Step 5: Initial Google OAuth

When you first run the program, it will prompt you to grant permissions in your browser:

- The script checks for a `token.json` file.
- If not present, it opens a local server and requests OAuth consent.
- On success, it writes out `token.json` (which should be in the `.gitignore`).

## Project Structure

```
project_root/
├── auth/
│   ├── __init__.py
│   └── google_auth.py      # Handles Google OAuth and returns Calendar service
├── models/
│   ├── __init__.py
│   └── calendar_models.py  # Pydantic model(s) for event creation input
├── tools/
│   ├── __init__.py
│   └── calendar_tool.py    # Calendar event creation tool
├── graph/
│   ├── __init__.py
│   └── main_graph.py       # Defines a simple graph-based workflow
├── main.py                 # Entry point for running the workflow
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not checked into Git)
├── .gitignore              # Exclude token.json, .env, etc.
└── token.json              # Stores OAuth tokens (auto-created; do not commit)
```

### Key Folders

- **`auth/`**: Contains `google_auth.py`, which manages the OAuth flow and returns an authenticated Calendar service.
- **`models/`**: Holds Pydantic models that define input/output validation.
- **`tools/`**: Where each tool lives as a separate file or module.
- **`graph/`**: Your LangGraph-based workflows. Each file can define one or more `StateGraph`.

## Usage

### 1. Run the Main Script

```
python main.py
```

On the first run:

- A browser window opens to let you log in with your Google account.
- Permissions are requested to manage your Google Calendar.
- Once granted, a `token.json` is saved locally.

### 2. Observe the Output

- The script prints the final state from the workflow.
- If you used the included tool, check your Google Calendar to verify the newly created event.

## Pydantic & Tools

- Tools accept a single dictionary input and use `@tool` decorator from `langchain.tools`.
- A Pydantic model (e.g., `CreateEventInput`) validates that dictionary.
- The tool calls `get_calendar_service()` from `auth/google_auth.py` for authentication.

## Expanding the Workflow

- Add more tools in the `tools/` folder and import them into your graph.
- In `graph/main_graph.py`, define new nodes that call these tools. Link them with `add_edge`.
- For more advanced parallel or branching flows, simply add more nodes and edges.

## Troubleshooting

### OAuth Errors:

- Ensure your Google credentials are correct and you have enabled the Calendar API in Google Cloud Console.

### `token.json` Issues:

- If the flow fails after partial authentication, delete `token.json` and re-run to force a fresh OAuth.

### Tool Deprecation Warnings:

- Use `.invoke()` or `.run()` instead of calling tools directly like a normal function. This ensures compatibility with LangGraph’s latest updates.

### Pydantic Validation:

- If you get an error about invalid time or format, check your ISO 8601 strings or your Pydantic model constraints.

## Contributing

- **Pull Requests**: Please ensure your code follows a consistent style and that you update the relevant docs.
- **Issues**: If you find a bug or have a suggestion, open an issue to discuss.

## Questions or Feedback?
Feel free to reach out or open an issue! Contributions and suggestions are welcome.


## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


## Sources & Learning Material

1. https://langchain-ai.github.io/langgraph/tutorials/introduction/
2. https://www.youtube.com/watch?v=8BV9TW490nQ
3. Shout out to AI
4. https://youtube.com/watch?v=tx5OapbK-8A&si=-UIOOGailG3VG4Vb



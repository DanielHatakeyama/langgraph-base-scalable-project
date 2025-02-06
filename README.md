# TODO MAKE THIS README CLOSER TO ACTUAL PROJECT DESCRIPTION

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



# Softlight Agent

An AI-driven UI workflow capture agent that takes natural language requests and automatically executes UI actions in a browser, capturing screenshots and metadata of each state change.

## Overview

Softlight Agent ("Agent B") is designed to:
- Take natural-language requests like "Create a project in Linear" or "Create a repository on GitHub"
- Use an LLM to plan generic UI actions dynamically (no hardcoding)
- Execute those actions in a real browser via Playwright
- Detect when the UI changes (even if the URL doesn't) and capture screenshots of each state
- Save screenshots + JSON metadata under `dataset/<task_slug>/`

The system is **completely generalizable** across web apps and doesn't rely on hard-coded workflows.

## Supported Tasks

The system has been tested and works with 4 different tasks across 3 different web applications:

1. **Create a project in Linear** - Demonstrates modal detection, form filling, and context-aware button detection
2. **Create an issue in Linear** - Shows consistency across different sections of the same app
3. **Search on YouTube** - Demonstrates search box handling and automatic Enter key press
4. **Create a repository on GitHub** - Shows sidebar navigation, form filling, and scrolling to find buttons below the fold

## Key Features

- **Context-Aware**: Analyzes page structure dynamically to find buttons, forms, and navigation
- **Generalizable**: Works across any web app without hardcoding
- **Non-URL State Capture**: Captures modals, forms, dropdowns, and other states without URLs
- **Smart Button Detection**: Uses semantic matching to find the right buttons based on task context
- **Login Handling**: Detects login requirements and saves session state
- **Search Box Support**: Automatically presses Enter for search boxes (YouTube, Google, etc.)

## Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers:**
   ```bash
   python -m playwright install
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your Groq API key:
   # GROQ_API_KEY=your_key_here
   ```
   
   **Getting a Groq API Key (Free!):**
   - Go to https://console.groq.com/
   - Sign up for a free account
   - Navigate to API Keys section
   - Create a new API key
   - Copy it to your `.env` file
   
   **Note:** If you don't have an API key, the agent will use heuristic fallback planning for common tasks.

## Running

### Basic Usage

```bash
python main.py "create a project in Linear"
```

### Example Tasks

```bash
# Create a project in Linear
python main.py "create a project in Linear called Test Project"

# Create an issue in Linear
python main.py "create an issue in Linear called Bug Fix"

# Search on YouTube
python main.py "Go to youtube and search for a funny video"

# Create a repository on GitHub
python main.py "Create a new repository on github named test"
```

## Output

All outputs are saved under `dataset/<task_slug>/` where `<task_slug>` is a slugified version of your task description.

For example, running `python main.py "create a project in Linear"` will create:
```
dataset/create-a-project-in-linear/
├── 001_initial.png
├── 001_initial.json
├── 002_goto.png
├── 002_goto.json
├── 003_click-by-text.png
├── 003_click-by-text.json
...
```

Each JSON file contains metadata:
- `index`: Sequential state number
- `url`: Current page URL
- `timestamp`: ISO UTC timestamp
- `dom_hash`: Hash of the DOM for change detection
- `step`: Action that triggered this capture
- `screenshot`: Filename of the screenshot

## Configuration

Edit `config.yaml` to customize behavior:

- `dataset_root`: Root directory for dataset storage (default: "dataset")
- `headless`: Run browser in headless mode (default: false)
- `slow_mo`: Delay between actions in milliseconds (default: 300)
- `persistent_context`: Save login state between runs (default: true)
- `llm`: LLM configuration (provider, model, temperature)
- `common_button_text`: List of common button texts for submit actions

## Architecture

- `main.py`: Entry point and orchestration
- `planner.py`: LLM-based planning with heuristic fallback
- `executor.py`: Playwright execution engine with login handling
- `actions.py`: Generic browser action implementations
- `page_analyzer.py`: Context-aware page structure analysis
- `state_manager.py`: UI state detection and screenshot capture
- `utils.py`: Helper functions (slugify, dom_hash, etc.)

## How It Works

1. **Planning**: The agent uses Groq LLM (or heuristic fallback) to generate a sequence of generic UI actions
2. **Execution**: Playwright executes each action sequentially in a Chromium browser
3. **State Detection**: After each action, the DOM is hashed and compared to detect changes
4. **Capture**: When a change is detected, a full-page screenshot and metadata are saved

## Key Technical Features

- **Context-Aware Page Analysis**: Dynamically analyzes page structure to find buttons, forms, and navigation without hardcoding
- **Modal Detection**: Automatically detects and prioritizes buttons inside modals
- **Header Button Filtering**: Skips header/nav buttons (like search bars) to find form buttons
- **Scrolling Support**: Automatically scrolls to find buttons below the fold
- **Search Box Handling**: Detects search boxes and presses Enter instead of looking for non-existent buttons
- **Login State Management**: Detects login requirements and saves session state between runs

## Requirements

- Python 3.8+
- Playwright >=1.40.0
- Groq API key (free) - see setup instructions above

## Troubleshooting

**Browser doesn't launch:**
- Make sure you ran `python -m playwright install`
- Check that Chromium is installed correctly

**No actions generated:**
- If using LLM: Check your Groq API key in `.env` (GROQ_API_KEY)
- The agent will fall back to heuristics if LLM is unavailable

**Login required:**
- The system will detect login pages and pause for manual login
- Login state is saved in `.browser_context/` for future runs

**Screenshots not captured:**
- Ensure the `dataset/` directory is writable
- Check that actions are actually changing the DOM

## License

MIT

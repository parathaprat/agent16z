"""
Planner module for generating UI action plans using LLM or fallback heuristics.
"""
import json
import os
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_planning_prompt(task: str) -> str:
    """
    Create a general-purpose planning prompt that works for ANY website.
    
    Args:
        task: Natural language task description
        
    Returns:
        Formatted prompt string
    """
    return f"""You are an expert UI automation planner. Break down ANY user task into a sequence of SIMPLE, ROBUST browser actions.

TASK: {task}

CRITICAL: Before generating actions, DEEPLY ANALYZE the task:

1. IDENTIFY SUB-GOALS: Break the task into sequential sub-goals
   Example: "search for KSI on youtube and play his latest video"
   → Sub-goal 1: Navigate to YouTube
   → Sub-goal 2: Search for "KSI"
   → Sub-goal 3: Click on KSI's channel from search results
   → Sub-goal 4: Find and click his latest video
   → Sub-goal 5: Capture the state

2. THINK THROUGH THE FLOW: What page am I on after each action?
   - After search → I'm on search results page (need to click a result)
   - After clicking channel → I'm on channel page (need to find videos)
   - After clicking video → I'm on video player page (goal achieved)

3. IDENTIFY REQUIRED NAVIGATION: Don't skip intermediate steps
   - If task says "play video X", you need to: search → click result → play
   - If task says "go to channel and do Y", you need to: search → click channel → do Y
   - Each page transition requires an explicit action

4. BE REALISTIC ABOUT CLICKABLE TEXT:
   - On search results: Click the name of what you searched for
   - On video sites: Click video titles to play them
   - On dashboards: Click navigation items or content titles
   - Use the ACTUAL text that would appear, not generic words

AVAILABLE ACTION TYPES:

1. goto: Navigate to a URL
   - Extract the website URL from the task description
   - If no URL is mentioned, infer the most likely website for the task
   - Example: {{"type": "goto", "url": "https://example.com"}}

2. click_by_text: Click any element by its visible text
   - Use this for buttons, links, tabs, dropdown options, menu items, selectors
   - Be SPECIFIC - use the exact visible text you expect to see
   - Think about what text would be visible to a user
   - For dropdowns/selectors: First click the current selection to open it, then click the target option
   - Example: {{"type": "click_by_text", "text": "Submit"}}
   - Example: {{"type": "click_by_text", "text": "Java"}} (for language selector)

3. wait_for_modal: Wait for a modal/dialog to appear
   - Use after clicking buttons that typically open modals (Create, New, Add, Edit, etc.)
   - Use when you expect a popup or dialog to appear
   - Helps ensure the UI is ready for the next action

4. fill_inputs: Fill any input field, textarea, or editor
   - Use generic field names that describe the purpose, not the technical name
   - Common patterns:
     * "q" or "search" for search boxes
     * "code", "editor", "solution" for code editors
     * "name", "title", "email", "description" for form fields
     * "query", "input" for generic text inputs
   - The system will find the field by label, placeholder, name, or type
   - Example: {{"type": "fill_inputs", "inputs": {{"q": "search term"}}}}
   - Example: {{"type": "fill_inputs", "inputs": {{"code": "your code here"}}}}

5. click_submit: Click a submit/save/create/confirm button OR press Enter for search
   - For search boxes: After filling search input, use click_submit (it will press Enter automatically)
   - For forms: Tries common button texts: "Submit", "Save", "Create", "Confirm", "Run", "Send"
   - IMPORTANT: Search boxes (YouTube, Google, etc.) don't have visible submit buttons - use click_submit after fill_inputs and it will press Enter

6. capture_state: Capture a screenshot of the current state
   - Always include at the end to capture the final result

CRITICAL PLANNING PRINCIPLES:

1. DECOMPOSE COMPLEX TASKS:
   - "Search for X and do Y" = search → click X from results → do Y
   - "Go to X and do Y" = navigate → click X → do Y
   - "Play video X" = search → click video title
   - "Create item with properties" = click Create → fill form → submit
   - Each arrow (→) is a separate action

2. UNDERSTAND PAGE FLOW AND NAVIGATION:
   - After searching: You're on a results page → must click a result to proceed
   - After clicking a result: You're on that specific page → can interact with its content
   - After filling a form: You're still on same page → must submit to proceed
   - Think: "Where am I now? What do I need to click to get to the next page?"
   - IMPORTANT: If task involves creating something in a category (e.g., "create a project", "create an issue"), you may need to navigate to that section first
   - Look for navigation elements: sidebars, menus, tabs (e.g., "Projects", "Issues", "Tasks")
   - Don't assume "Create" button is immediately visible - it might be in a specific section

3. DON'T SKIP NAVIGATION STEPS:
   - If the task requires going somewhere specific, generate the clicks to get there
   - "Play latest video" requires: search → click channel/video → potentially click play
   - "Edit item X" requires: search/find X → click X → click Edit → fill → save
   - "Create a project" requires: navigate to Projects section → click Create → fill form → submit
   - "Create an issue" requires: navigate to Issues section → click Create → fill form → submit
   - Each transition between pages/sections needs an action
   - If task mentions a category (project, issue, task, page), navigate to that section first

4. BE SPECIFIC WITH CLICKABLE TEXT:
   - Use the ACTUAL text that appears, not generic labels
   - Search results: Click the name of what you searched for (e.g., "KSI", "John Doe")
   - Video titles: Click the actual video title or "Latest video" or first visible video
   - Buttons: Click exact button text ("Submit", "Save", "Create")
   - DON'T use vague text like "Play" without context

5. HANDLE DROPDOWNS/SELECTORS (when needed):
   - ONLY if the task explicitly requires changing a selection
   - First click the CURRENT selection (visible text)
   - Then click the TARGET option
   - Example: Task says "solve in Java" AND default is C++ → click "C++", then "Java"

6. HANDLE FORMS AND INPUTS:
   - Identify what needs to be entered
   - Use generic field names: "code", "editor", "q", "search", "name", "title"
   - For coding sites: Usually just need to fill "code" field
   - Don't assume forms need to be opened - they might be already visible

7. BE SPECIFIC BUT REALISTIC:
   - Use common button texts: "Submit", "Run", "Save", "Create", "Search"
   - Don't invent UI elements like "Add a solution", "Edit code", etc.
   - If you don't know the exact text, use click_submit instead

8. EXTRACT URLS INTELLIGENTLY:
   - Parse the task for website names and specific pages
   - If task mentions a specific problem/page, construct full URL
   - Examples:
     * "search on google" → https://www.google.com
     * "create project in linear" → https://linear.app
     * "problem X on codingsite" → https://codingsite.com/problems/x

GENERAL EXAMPLES (these patterns work on ANY website):

Example 1: Simple search (single page)
Task: "search for python tutorials on google"
Sub-goals: Navigate → Fill search → Press Enter → Capture
Analysis: Search boxes don't have visible buttons - use click_submit after fill_inputs (it presses Enter)
{{
  "actions": [
    {{"type": "goto", "url": "https://www.google.com"}},
    {{"type": "fill_inputs", "inputs": {{"q": "python tutorials"}}}},
    {{"type": "click_submit"}},
    {{"type": "capture_state"}}
  ]
}}
Note: click_submit automatically detects search boxes and presses Enter - no need to look for a search button

Example 2: Search and navigate to result (multi-page)
Task: "search for NASA on google and go to their website"
Sub-goals: Navigate → Search → Click result → Capture
{{
  "actions": [
    {{"type": "goto", "url": "https://www.google.com"}},
    {{"type": "fill_inputs", "inputs": {{"q": "NASA"}}}},
    {{"type": "click_submit"}},
    {{"type": "click_by_text", "text": "NASA"}},
    {{"type": "capture_state"}}
  ]
}}

Example 3: Multi-step navigation on video site
Task: "search for TechChannel on videosite and play their latest video"
Sub-goals: Navigate → Search → Click channel → Click videos section → Capture
Flow: Home page → Search results → Channel page → Videos visible
{{
  "actions": [
    {{"type": "goto", "url": "https://videosite.com"}},
    {{"type": "fill_inputs", "inputs": {{"q": "TechChannel"}}}},
    {{"type": "click_submit"}},
    {{"type": "click_by_text", "text": "TechChannel"}},
    {{"type": "click_by_text", "text": "Videos"}},
    {{"type": "capture_state"}}
  ]
}}
Note: This shows the pattern - don't skip intermediate clicks between pages

Example 4: Creating something with navigation
Task: "create a new project called MyApp"
Sub-goals: Navigate → Go to Projects section → Click Create → Fill form → Submit → Capture
Analysis: "project" suggests we need to navigate to Projects section first
{{
  "actions": [
    {{"type": "goto", "url": "https://website.com"}},
    {{"type": "click_by_text", "text": "Projects"}},
    {{"type": "click_by_text", "text": "Create"}},
    {{"type": "wait_for_modal"}},
    {{"type": "fill_inputs", "inputs": {{"name": "MyApp"}}}},
    {{"type": "click_submit"}},
    {{"type": "capture_state"}}
  ]
}}

Example 4b: Creating something (if Create button is immediately visible)
Task: "create a new task"
Sub-goals: Navigate → Click Create → Fill form → Submit → Capture
Analysis: If "Create" button is visible on homepage, no navigation needed
{{
  "actions": [
    {{"type": "goto", "url": "https://website.com"}},
    {{"type": "click_by_text", "text": "Create"}},
    {{"type": "wait_for_modal"}},
    {{"type": "fill_inputs", "inputs": {{"name": "New task"}}}},
    {{"type": "click_submit"}},
    {{"type": "capture_state"}}
  ]
}}

Example 5: Filling editor directly (single page)
Task: "solve the problem on this page"
Sub-goals: Navigate (already on page) → Fill → Submit → Capture
{{
  "actions": [
    {{"type": "goto", "url": "https://codingsite.com/problem"}},
    {{"type": "fill_inputs", "inputs": {{"code": "solution"}}}},
    {{"type": "click_submit"}},
    {{"type": "capture_state"}}
  ]
}}

KEY INSIGHTS:
- Simple tasks (search only): 3-4 actions
- Navigation tasks (search + click result): 5-6 actions
- Complex tasks (search + navigate + interact): 6-8+ actions
- Each page transition = new action
- Don't skip intermediate clicks

PLANNING PROCESS:

Step 1: DECOMPOSE INTO SUB-GOALS
- Break the task into a sequence of sub-goals
- Each sub-goal represents a page or state transition
- Example: "search X and play video" = [search] → [click result] → [play]

Step 2: MAP OUT THE PAGE FLOW
- Start: What page do I begin on?
- After each action: What page/state am I on now?
- What needs to happen to get to the next page?
- Example flow: Home → Search results → Channel page → Video page
- IMPORTANT: If task mentions a category (project, issue, task), think about navigation:
  * "create a project" → likely need to click "Projects" in sidebar/menu first
  * "create an issue" → likely need to click "Issues" in sidebar/menu first
  * "create a page" → might need to navigate to pages section first
- Don't assume the Create button is on the homepage - it might be in a section

Step 3: GENERATE ACTIONS FOR EACH TRANSITION
- For each sub-goal, create the action(s) needed
- Don't skip steps between pages or sections
- Use specific, realistic text for clicks
- Example:
  * Sub-goal "search" → fill_inputs + click_submit
  * Sub-goal "click result" → click_by_text with the search term
  * Sub-goal "play video" → click_by_text with video title or "Videos"
  * Sub-goal "create project" → click_by_text "Projects" → click_by_text "Create" → fill form → submit
- If task mentions a category, include navigation to that section:
  * "create a project" → navigate to Projects section first
  * "create an issue" → navigate to Issues section first

Step 4: VALIDATE THE FLOW
- Does each action move toward the goal?
- Am I skipping any page transitions?
- Is the clickable text realistic and specific?
- Would a human follow this exact sequence?

Step 5: KEEP IT PRACTICAL
- Don't guess at hidden navigation
- Use obvious, visible text for clicks
- If task is simple (just search), keep it simple
- If task is complex (search + navigate + interact), include all steps

COMMON MISTAKES TO AVOID:
❌ Inventing UI elements that don't exist ("Add a solution", "Edit code")
❌ Using vague clickable text ("Play" instead of video title)
❌ Skipping page transitions (searching but not clicking result)
❌ Over-complicating simple tasks (adding navigation when content is visible)
❌ Under-complicating complex tasks (not generating intermediate navigation steps)

CORRECT PATTERNS:
✅ Simple task: goto → fill → submit → capture (3-4 actions)
✅ Navigation task: goto → fill → submit → click_result → capture (4-5 actions)
✅ Complex task: goto → fill → submit → click_result → click_item → capture (5-7+ actions)
✅ Use specific names from the task for clickable text

IMPORTANT REMINDERS:
- Work for ANY website, not just specific ones
- Don't memorize specific website layouts - use general patterns
- Be conservative - less is more
- Focus on what's LIKELY to be visible after initial navigation
- Always end with capture_state

Now analyze the given task following the PLANNING PROCESS above. Return ONLY valid JSON with an "actions" array, no markdown formatting or explanation."""


def plan_with_groq(task: str, config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Use Groq API to generate a plan of UI actions (free and fast!).
    
    Args:
        task: Natural language task description
        config: Configuration dictionary with LLM settings
        
    Returns:
        List of action dictionaries or None if failed
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    
    try:
        import requests
        
        llm_config = config.get("llm", {})
        model = llm_config.get("model", "llama-3.1-8b-instant")  # Free Groq model
        api_base = llm_config.get("api_base", "https://api.groq.com/openai/v1")
        
        # Create prompt
        prompt = create_planning_prompt(task)
        
        # Prepare request (Groq uses OpenAI-compatible API)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that generates JSON objects with an 'actions' array of UI actions. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": llm_config.get("temperature", 0.2),
            "response_format": {"type": "json_object"}
        }
        
        # Make API call
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        # Extract content
        content = result["choices"][0]["message"]["content"]
        return parse_llm_response(content)
        
    except Exception as e:
        print(f"  ⚠ Groq planning failed: {e}")
        return None


def plan_with_huggingface(task: str, config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Use Hugging Face Inference API to generate a plan of UI actions.
    
    Args:
        task: Natural language task description
        config: Configuration dictionary with LLM settings
        
    Returns:
        List of action dictionaries or None if failed
    """
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        return None
    
    try:
        import requests
        
        llm_config = config.get("llm", {})
        model = llm_config.get("model", "meta-llama/Meta-Llama-3.1-8B-Instruct")
        api_base = llm_config.get("api_base", "https://api-inference.huggingface.co/models")
        
        # Construct API URL
        # Try new router endpoint first, fallback to old endpoint
        if "router.huggingface.co" in api_base:
            # New router endpoint format: https://router.huggingface.co/hf-inference/{model}
            api_url = f"{api_base}/{model}"
        elif "api-inference.huggingface.co" in api_base:
            # Old endpoint format (deprecated but might still work for some models)
            api_url = f"{api_base}/{model}"
        else:
            # Default: assume it's already a full URL or use old format
            api_url = f"{api_base}/{model}" if not api_base.endswith(model) else api_base
        
        # Create prompt
        prompt = create_planning_prompt(task)
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Format prompt for instruction-tuned models (adjust based on model)
        # Try different formats for different models
        if "phi" in model.lower() or "llama" in model.lower():
            formatted_prompt = f"<|user|>\n{prompt}\n<|assistant|>\n"
        elif "mistral" in model.lower():
            formatted_prompt = f"[INST] {prompt} [/INST]"
        else:
            # Default format
            formatted_prompt = prompt
        
        payload = {
            "inputs": formatted_prompt,
            "parameters": {
                "temperature": llm_config.get("temperature", 0.2),
                "max_new_tokens": 1000,
                "return_full_text": False,
                "do_sample": True
            }
        }
        
        # Make API call
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        # Handle loading state (model might be loading)
        if response.status_code == 503:
            print("  ⏳ Model is loading, please wait...")
            # Retry after a delay
            import time
            time.sleep(10)
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        response.raise_for_status()
        result = response.json()
        
        # Extract generated text - handle different response formats
        generated_text = ""
        if isinstance(result, list) and len(result) > 0:
            # Standard format: [{"generated_text": "..."}]
            generated_text = result[0].get("generated_text", "")
        elif isinstance(result, dict):
            # Alternative format: {"generated_text": "..."}
            generated_text = result.get("generated_text", result.get("text", ""))
        else:
            generated_text = str(result)
        
        # Parse JSON from response
        return parse_llm_response(generated_text)
        
    except Exception as e:
        print(f"  ⚠ Hugging Face planning failed: {e}")
        return None




def parse_llm_response(content: str) -> Optional[List[Dict[str, Any]]]:
    """
    Parse LLM response to extract action list.
    
    Args:
        content: Raw LLM response text
        
    Returns:
        List of action dictionaries or None if parsing failed
    """
    if not content:
        return None
    
    # Try to parse as JSON directly
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            # Look for common keys
            for key in ["actions", "plan", "steps"]:
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
        elif isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    json_patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```',
        r'\{[^{}]*"actions"[^{}]*\[.*?\][^{}]*\}',
        r'\[.*?\]'
    ]
    
    for pattern in json_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1) if match.groups() else match.group(0))
                if isinstance(parsed, dict):
                    for key in ["actions", "plan", "steps"]:
                        if key in parsed and isinstance(parsed[key], list):
                            return parsed[key]
                elif isinstance(parsed, list):
                    return parsed
            except:
                continue
    
    return None


def plan_with_llm(task: str, config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Use LLM to generate a plan of UI actions (supports Groq and Hugging Face).
    
    Args:
        task: Natural language task description
        config: Configuration dictionary with LLM settings
        
    Returns:
        List of action dictionaries or None if failed
    """
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "groq").lower()
    
    if provider == "groq":
        return plan_with_groq(task, config)
    elif provider == "huggingface":
        return plan_with_huggingface(task, config)
    elif provider == "none":
        return None
    else:
        # Default to Groq (free and fast)
        return plan_with_groq(task, config)


def plan_with_heuristic(task: str) -> List[Dict[str, Any]]:
    """
    Generate a plan using heuristic rules (fallback when LLM is unavailable).
    
    Args:
        task: Natural language task description
        
    Returns:
        List of action dictionaries
    """
    task_lower = task.lower()
    
    # Linear-specific heuristics
    if "linear" in task_lower:
        if "create" in task_lower and "project" in task_lower:
            return [
                {"type": "goto", "url": "https://linear.app"},
                {"type": "click_by_text", "text": "Create"},
                {"type": "wait_for_modal"},
                {"type": "fill_inputs", "inputs": {"name": "My Project"}},
                {"type": "click_submit"},
                {"type": "capture_state"}
            ]
        elif "create" in task_lower and "issue" in task_lower:
            return [
                {"type": "goto", "url": "https://linear.app"},
                {"type": "click_by_text", "text": "New"},
                {"type": "wait_for_modal"},
                {"type": "fill_inputs", "inputs": {"title": "New Issue"}},
                {"type": "click_submit"},
                {"type": "capture_state"}
            ]
    
    # Notion-specific heuristics
    elif "notion" in task_lower:
        if "filter" in task_lower and "database" in task_lower:
            return [
                {"type": "goto", "url": "https://notion.so"},
                {"type": "click_by_text", "text": "Filter"},
                {"type": "wait_for_modal"},
                {"type": "capture_state"}
            ]
        elif "create" in task_lower and "page" in task_lower:
            return [
                {"type": "goto", "url": "https://notion.so"},
                {"type": "click_by_text", "text": "New"},
                {"type": "wait_for_modal"},
                {"type": "fill_inputs", "inputs": {"title": "New Page"}},
                {"type": "click_submit"},
                {"type": "capture_state"}
            ]
    
    # Google search heuristics (no auth required - good for testing)
    elif "google" in task_lower and "search" in task_lower:
        # Extract search query if provided
        search_query = "Python programming"
        if "for" in task_lower:
            parts = task_lower.split("for")
            if len(parts) > 1:
                search_query = parts[-1].strip()
        elif "search" in task_lower:
            parts = task_lower.split("search")
            if len(parts) > 1:
                potential_query = parts[-1].strip()
                if potential_query and len(potential_query) > 2:
                    search_query = potential_query
        
        return [
            {"type": "goto", "url": "https://www.google.com"},
            {"type": "capture_state"},
            {"type": "fill_inputs", "inputs": {"q": search_query, "search": search_query}},
            {"type": "click_submit"},
            {"type": "capture_state"}
        ]
    
    # Generic fallback
    return [
        {"type": "goto", "url": "https://linear.app"},
        {"type": "capture_state"}
    ]


def plan(task: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate a plan for the given task using LLM or fallback heuristics.
    
    Args:
        task: Natural language task description
        config: Configuration dictionary
        
    Returns:
        List of action dictionaries
    """
    print(f"📋 Planning actions for: {task}")
    
    # Try LLM first
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "groq").lower()
    
    if provider != "none":
        llm_plan = plan_with_llm(task, config)
        if llm_plan and len(llm_plan) > 0:
            provider_name = "Groq" if provider == "groq" else "Hugging Face" if provider == "huggingface" else "LLM"
            print(f"  ✓ Generated {len(llm_plan)} actions using {provider_name} LLM")
            return llm_plan
    
    # Fallback to heuristics
    print(f"  ⚠ Using heuristic planner (no API key or LLM failed)")
    heuristic_plan = plan_with_heuristic(task)
    print(f"  ✓ Generated {len(heuristic_plan)} actions using heuristics")
    return heuristic_plan


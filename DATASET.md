# Dataset

This directory contains captured UI states for 3 different tasks across Linear and YouTube.

## Task 1: Create a Project in Linear

**Task:** `"create a project in Linear called Test Project"`

**Description:**
This task demonstrates creating a new project in Linear. The workflow includes:

- Navigating to Linear
- Logging in (if required)
- Navigating to the Projects section
- Opening the create modal
- Filling in the project name
- Submitting the form

**Captured States:**

- Initial state (before navigation)
- After navigation to Linear
- After clicking "Projects" in sidebar
- After clicking "New project" button
- Modal appears (non-URL state)
- Form filled with project name
- After clicking "Create Project" button
- Final state (project created)

**Key Features Demonstrated:**

- Login detection and handling
- Navigation to specific sections
- Modal detection and interaction
- Form filling
- Context-aware button detection (finds "Create Project" in modal)

---

## Task 2: Create an Issue in Linear

**Task:** `"create an issue in Linear called Bug Fix"`

**Description:**
This task demonstrates creating a new issue in Linear. The workflow includes:

- Navigating to Linear
- Navigating to the Issues section
- Opening the create modal
- Filling in the issue title
- Submitting the form

**Captured States:**

- Initial state
- After navigation to Linear
- After clicking "Issues" in sidebar
- After clicking create button
- Modal appears (non-URL state)
- Form filled with issue title
- After clicking submit button
- Final state (issue created)

**Key Features Demonstrated:**

- Navigation to different sections (Issues vs Projects)
- Same pattern works across sections
- Consistency of the system

---

## Task 3: Search on YouTube

**Task:** `"Go to youtube and search for a funny video"`

**Description:**
This task demonstrates searching on YouTube. The workflow includes:

- Navigating to YouTube
- Logging in (if required)
- Filling the search box
- Pressing Enter (no visible submit button)
- Viewing search results

**Captured States:**

- Initial state
- After login (if required)
- After navigation to YouTube
- Search box filled
- After pressing Enter (search executed)
- Search results displayed
- Final state

**Key Features Demonstrated:**

- Search box detection
- Automatic Enter key press (no submit button needed)
- Handling sites without visible submit buttons
- Generalizability across different app types

---

## Dataset Structure

Each task directory contains:

- `001_initial.png` / `001_initial.json` - Initial state before any actions
- `002_goto.png` / `002_goto.json` - After navigation
- `003_*.png` / `003_*.json` - After each subsequent action
- ...

Each JSON file contains:

```json
{
  "index": 1,
  "url": "https://linear.app",
  "timestamp": "2024-01-01T12:00:00Z",
  "dom_hash": "abc123...",
  "step": "goto",
  "screenshot": "001_initial.png"
}
```

## Non-URL States Captured

All three tasks demonstrate capturing UI states that don't have unique URLs:

- **Modals**: Create project modal, create issue modal
- **Forms**: Project creation form, issue creation form
- **Dropdowns**: Filter dropdowns (if used)
- **Search Results**: YouTube search results page

This demonstrates the system's ability to capture states beyond URL changes, which is a key requirement of the assignment.

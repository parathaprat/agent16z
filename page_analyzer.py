"""
Page analyzer for context-aware UI automation.
Analyzes page structure dynamically without hardcoded patterns.
"""
from typing import Dict, Any, List, Optional
from playwright.sync_api import Page


def analyze_page_context(page: Page) -> Dict[str, Any]:
    """
    Analyze the current page to understand its structure and available actions.
    This is completely general - no hardcoded patterns.
    
    Args:
        page: Playwright page object
        
    Returns:
        Dictionary with page analysis including buttons, forms, navigation, etc.
    """
    try:
        # Get all visible buttons
        buttons = []
        try:
            button_elements = page.locator('button, input[type="button"], input[type="submit"], a[role="button"]')
            count = button_elements.count()
            for i in range(min(count, 50)):  # Limit to first 50 to avoid performance issues
                try:
                    btn = button_elements.nth(i)
                    if btn.is_visible(timeout=500):
                        text = btn.text_content() or ""
                        aria_label = btn.get_attribute("aria-label") or ""
                        button_text = text.strip() or aria_label.strip()
                        if button_text:
                            buttons.append({
                                "text": button_text,
                                "aria_label": aria_label,
                                "type": "button"
                            })
                except:
                    continue
        except:
            pass
        
        # Get navigation elements (links, menu items)
        navigation = []
        try:
            # Look for common navigation patterns
            nav_selectors = [
                'nav a',
                '[role="navigation"] a',
                'aside a',
                '[class*="sidebar" i] a',
                '[class*="menu" i] a',
                '[class*="nav" i] a'
            ]
            for selector in nav_selectors:
                try:
                    nav_elements = page.locator(selector)
                    count = nav_elements.count()
                    for i in range(min(count, 30)):
                        try:
                            elem = nav_elements.nth(i)
                            if elem.is_visible(timeout=500):
                                text = elem.text_content() or ""
                                if text.strip():
                                    navigation.append({
                                        "text": text.strip(),
                                        "type": "navigation"
                                    })
                        except:
                            continue
                except:
                    continue
        except:
            pass
        
        # Get form inputs
        inputs = []
        try:
            input_elements = page.locator('input, textarea, [contenteditable="true"]')
            count = input_elements.count()
            for i in range(min(count, 30)):
                try:
                    inp = input_elements.nth(i)
                    if inp.is_visible(timeout=500):
                        input_type = inp.get_attribute("type") or "text"
                        name = inp.get_attribute("name") or ""
                        placeholder = inp.get_attribute("placeholder") or ""
                        label = ""
                        
                        # Try to find associated label
                        try:
                            input_id = inp.get_attribute("id")
                            if input_id:
                                label_elem = page.locator(f'label[for="{input_id}"]')
                                if label_elem.is_visible(timeout=100):
                                    label = label_elem.text_content() or ""
                        except:
                            pass
                        
                        inputs.append({
                            "type": input_type,
                            "name": name,
                            "placeholder": placeholder,
                            "label": label.strip()
                        })
                except:
                    continue
        except:
            pass
        
        # Detect if there's a modal/dialog open
        has_modal = False
        try:
            modal_selectors = [
                '[role="dialog"]',
                '.modal',
                '[class*="modal" i]',
                '[class*="dialog" i]',
                '[class*="overlay" i]'
            ]
            for selector in modal_selectors:
                try:
                    modal = page.locator(selector).first
                    if modal.is_visible(timeout=500):
                        has_modal = True
                        break
                except:
                    continue
        except:
            pass
        
        return {
            "buttons": buttons,
            "navigation": navigation,
            "inputs": inputs,
            "has_modal": has_modal,
            "url": page.url
        }
    except Exception as e:
        return {
            "buttons": [],
            "navigation": [],
            "inputs": [],
            "has_modal": False,
            "url": page.url,
            "error": str(e)
        }


def find_matching_button(page: Page, task_context: str, action_type: str = "submit") -> Optional[Dict[str, Any]]:
    """
    Find a button that matches the task context semantically.
    Completely general - analyzes page and task to find the best match.
    Prioritizes buttons in modals when modals are present.
    
    Args:
        page: Playwright page object
        task_context: Task description
        action_type: Type of action ("submit", "create", "save", etc.)
        
    Returns:
        Button info if found, None otherwise
    """
    try:
        # First, check if there's a modal - if so, prioritize buttons in modal
        has_modal = False
        modal_buttons = []
        page_buttons = []
        
        try:
            modal_selectors = [
                '[role="dialog"]',
                '.modal',
                '[class*="modal" i]',
                '[class*="dialog" i]',
                '[class*="overlay" i]'
            ]
            
            for selector in modal_selectors:
                try:
                    modal = page.locator(selector).first
                    if modal.is_visible(timeout=500):
                        has_modal = True
                        # Get buttons specifically in this modal
                        try:
                            modal_button_elements = modal.locator('button, input[type="button"], input[type="submit"], a[role="button"]')
                            count = modal_button_elements.count()
                            for i in range(min(count, 20)):
                                try:
                                    btn = modal_button_elements.nth(i)
                                    if btn.is_visible(timeout=500):
                                        text = btn.text_content() or ""
                                        aria_label = btn.get_attribute("aria-label") or ""
                                        button_text = text.strip() or aria_label.strip()
                                        if button_text:
                                            modal_buttons.append({
                                                "text": button_text,
                                                "aria_label": aria_label,
                                                "type": "button",
                                                "in_modal": True
                                            })
                                except:
                                    continue
                        except:
                            pass
                        break
                except:
                    continue
        except:
            pass
        
        # Get all page buttons (but exclude modal buttons if we found modal buttons)
        page_context = analyze_page_context(page)
        all_buttons = page_context.get("buttons", [])
        
        # If we found modal buttons, use those; otherwise use all buttons
        if has_modal and modal_buttons:
            buttons = modal_buttons
        else:
            buttons = all_buttons
        
        if not buttons:
            return None
        
        task_lower = task_context.lower()
        
        # Extract action keywords from task
        action_keywords = []
        action_patterns = {
            "create": ["create", "new", "add"],
            "save": ["save", "update", "edit"],
            "submit": ["submit", "confirm", "send"],
            "delete": ["delete", "remove"],
            "cancel": ["cancel", "close"]
        }
        
        for action, keywords in action_patterns.items():
            if any(kw in task_lower for kw in keywords):
                action_keywords.extend(keywords)
        
        # Extract object keywords (what we're creating/editing)
        object_keywords = []
        common_objects = ["project", "issue", "task", "page", "item", "note", "card", "document"]
        for obj in common_objects:
            if obj in task_lower:
                object_keywords.append(obj)
        
        # Score each button based on relevance
        scored_buttons = []
        for btn in buttons:
            button_text = btn["text"].lower()
            score = 0
            
            # Exact match gets highest score
            if any(keyword in button_text for keyword in action_keywords):
                score += 10
            
            # Object match adds to score
            if any(obj in button_text for obj in object_keywords):
                score += 5
            
            # Combined match (e.g., "Create Project") gets bonus
            if len(action_keywords) > 0 and len(object_keywords) > 0:
                if any(action in button_text for action in action_keywords) and any(obj in button_text for obj in object_keywords):
                    score += 15
            
            # HUGE bonus for buttons in modal (when modal is present)
            if btn.get("in_modal", False):
                score += 25
            
            # Prefer "Create" over "Add" when task says "create"
            if "create" in task_lower and "create" in button_text.lower() and "add" not in button_text.lower():
                score += 10
            
            # Penalize "Add" when task says "create" (unless it's the only match)
            if "create" in task_lower and "add" in button_text.lower() and "create" not in button_text.lower():
                score -= 5
            
            if score > 0:
                scored_buttons.append((score, btn))
        
        # Return highest scoring button
        if scored_buttons:
            scored_buttons.sort(key=lambda x: x[0], reverse=True)
            return scored_buttons[0][1]
        
        return None
    except:
        return None


def find_matching_navigation(page: Page, task_context: str) -> Optional[Dict[str, Any]]:
    """
    Find navigation element that matches the task context.
    
    Args:
        page: Playwright page object
        task_context: Task description
        
    Returns:
        Navigation element info if found, None otherwise
    """
    try:
        page_context = analyze_page_context(page)
        navigation = page_context.get("navigation", [])
        
        if not navigation:
            return None
        
        task_lower = task_context.lower()
        
        # Extract category keywords
        category_keywords = []
        categories = ["project", "issue", "task", "page", "document", "database", "team", "settings"]
        for cat in categories:
            if cat in task_lower:
                category_keywords.append(cat)
        
        # Find navigation that matches category
        for nav in navigation:
            nav_text = nav["text"].lower()
            if any(cat in nav_text for cat in category_keywords):
                return nav
        
        return None
    except:
        return None


def find_matching_input(page: Page, field_name: str) -> Optional[Dict[str, Any]]:
    """
    Find input field that matches the field name semantically.
    
    Args:
        page: Playwright page object
        field_name: Name of field to find (e.g., "name", "title", "code")
        
    Returns:
        Input field info if found, None otherwise
    """
    try:
        page_context = analyze_page_context(page)
        inputs = page_context.get("inputs", [])
        
        if not inputs:
            return None
        
        field_lower = field_name.lower()
        
        # Try to match by name, placeholder, or label
        for inp in inputs:
            if (inp.get("name", "").lower() == field_lower or
                inp.get("placeholder", "").lower() == field_lower or
                inp.get("label", "").lower() == field_lower or
                field_lower in inp.get("name", "").lower() or
                field_lower in inp.get("placeholder", "").lower() or
                field_lower in inp.get("label", "").lower()):
                return inp
        
        # Fallback: return first visible text input
        for inp in inputs:
            if inp.get("type") in ["text", "search", ""] or not inp.get("type"):
                return inp
        
        return None
    except:
        return None


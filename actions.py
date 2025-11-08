"""
Generic browser actions for UI automation.
"""
from typing import Dict, Any, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from page_analyzer import find_matching_button, find_matching_navigation, find_matching_input


def detect_auth_state(page: Page) -> Dict[str, Any]:
    """
    Detect if we're on a login/authentication page OR if login is required.
    
    Args:
        page: Playwright page object
        
    Returns:
        Dictionary with auth state information
    """
    url = page.url.lower()
    page_text = page.content().lower()
    
    # Common login indicators
    login_indicators = [
        "sign in", "log in", "login", "signin",
        "email", "password", "authenticate",
        "continue with", "oauth", "sso"
    ]
    
    # Check URL
    is_login_url = any(indicator in url for indicator in ["login", "signin", "auth", "oauth"])
    
    # Check page content
    login_text_found = any(indicator in page_text for indicator in login_indicators)
    
    # Check for common login form elements
    has_email_field = page.locator('input[type="email"], input[name*="email" i], input[id*="email" i]').count() > 0
    has_password_field = page.locator('input[type="password"]').count() > 0
    
    # Check for login buttons (common on homepages like Linear)
    # Try multiple strategies to find login buttons
    login_button_texts = [
        "sign in", "log in", "login", "signin",
        "sign in with google", "continue with google", 
        "get started", "sign up", "signup"
    ]
    has_login_button = False
    login_button_found = None
    
    # Strategy 1: Find by exact text match (case-insensitive)
    for button_text in login_button_texts:
        try:
            # Try exact match first
            button = page.get_by_role("button", name=button_text, exact=False).first
            if button.is_visible(timeout=1000):
                has_login_button = True
                login_button_found = button_text
                break
        except:
            try:
                # Try link/button with text
                button = page.get_by_text(button_text, exact=False).first
                if button.is_visible(timeout=1000):
                    has_login_button = True
                    login_button_found = button_text
                    break
            except:
                continue
    
    # Strategy 2: Check for buttons with aria-label containing login text
    if not has_login_button:
        try:
            login_aria_selectors = [
                'button[aria-label*="sign in" i]',
                'button[aria-label*="log in" i]',
                'a[aria-label*="sign in" i]',
                'button[aria-label*="login" i]'
            ]
            for selector in login_aria_selectors:
                try:
                    button = page.locator(selector).first
                    if button.is_visible(timeout=1000):
                        has_login_button = True
                        login_button_found = "login button (aria-label)"
                        break
                except:
                    continue
        except:
            pass
    
    # Strategy 3: Check for common login button classes/IDs
    if not has_login_button:
        try:
            login_class_selectors = [
                'button[class*="sign-in" i]',
                'button[class*="login" i]',
                'a[class*="sign-in" i]',
                'button[id*="sign-in" i]',
                'button[id*="login" i]'
            ]
            for selector in login_class_selectors:
                try:
                    button = page.locator(selector).first
                    if button.is_visible(timeout=1000):
                        has_login_button = True
                        login_button_found = "login button (class/id)"
                        break
                except:
                    continue
        except:
            pass
    
    # Check if we're on a dedicated login page
    # Be more conservative: only mark as login page if:
    # 1. URL explicitly indicates login, OR
    # 2. We have BOTH email AND password fields visible (actual login form), OR
    # 3. We have a login form with email/password AND we're on a root/auth URL
    has_login_form = has_email_field and has_password_field
    is_login_page = is_login_url or (has_login_form and (is_login_url or "/login" in url or "/signin" in url))
    
    # requires_login is true if we need login (but might already be logged in)
    requires_login = is_login_page or (has_login_button and not has_login_form)
    
    return {
        "is_login_page": is_login_page,
        "requires_login": requires_login,
        "has_login_button": has_login_button,
        "login_button_text": login_button_found,
        "url": page.url,
        "has_email_field": has_email_field,
        "has_password_field": has_password_field
    }


def goto(page: Page, url: str, timeout: int = 30000) -> Dict[str, Any]:
    """
    Navigate to a URL.
    
    Args:
        page: Playwright page object
        url: URL to navigate to
        timeout: Navigation timeout in milliseconds
        
    Returns:
        Result dictionary with success status
    """
    try:
        page.goto(url, timeout=timeout, wait_until="networkidle")
        return {"success": True, "action": "goto", "url": url}
    except PlaywrightTimeoutError:
        return {"success": False, "action": "goto", "error": "Navigation timeout"}
    except Exception as e:
        return {"success": False, "action": "goto", "error": str(e)}


def click_by_text(page: Page, text: str, timeout: int = 10000, task_context: str = None, skip_auth_check: bool = False) -> Dict[str, Any]:
    """
    Click an element by its visible text.
    Uses page analyzer for context-aware navigation detection.
    
    Args:
        page: Playwright page object
        text: Text to search for
        timeout: Wait timeout in milliseconds
        task_context: Optional task description for context-aware matching
        skip_auth_check: If True, skip login page check (useful after manual login)
        
    Returns:
        Result dictionary with success status
    """
    try:
        # Check if we're on a login page (only if not skipping auth check)
        if not skip_auth_check:
            auth_state = detect_auth_state(page)
            # Only block if we're actually on a dedicated login page (URL-based)
            # Don't block just because login-related text exists (might be after login)
            if auth_state["is_login_page"] and ("/login" in page.url.lower() or "/signin" in page.url.lower() or "/auth" in page.url.lower()):
                return {
                    "success": False,
                    "action": "click_by_text",
                    "error": f"Element with text '{text}' not found - appears to be on login/authentication page",
                    "auth_state": auth_state
                }
        
        # Try context-aware navigation matching first
        if task_context and text.lower() in ["projects", "issues", "tasks", "pages", "documents"]:
            matching_nav = find_matching_navigation(page, task_context)
            if matching_nav and matching_nav["text"].lower() == text.lower():
                try:
                    nav_elem = page.get_by_text(matching_nav["text"], exact=False).first
                    nav_elem.wait_for(state="visible", timeout=timeout)
                    nav_elem.scroll_into_view_if_needed()
                    nav_elem.click()
                    return {"success": True, "action": "click_by_text", "text": matching_nav["text"], "method": "context-aware"}
                except:
                    pass
        
        # Try multiple strategies to find the element
        # Strategy 1: Standard text matching (most common)
        try:
            element = page.get_by_text(text, exact=False).first
            element.wait_for(state="visible", timeout=timeout)
            element.scroll_into_view_if_needed()
            page.wait_for_timeout(300)  # Wait after scroll
            element.click()
            return {"success": True, "action": "click_by_text", "text": text, "method": "text-match"}
        except:
            pass
        
        # Strategy 2: Try by role (button, link)
        try:
            element = page.get_by_role("button", name=text, exact=False).first
            element.wait_for(state="visible", timeout=timeout)
            element.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            element.click()
            return {"success": True, "action": "click_by_text", "text": text, "method": "role-button"}
        except:
            pass
        
        # Strategy 3: Try by link role
        try:
            element = page.get_by_role("link", name=text, exact=False).first
            element.wait_for(state="visible", timeout=timeout)
            element.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            element.click()
            return {"success": True, "action": "click_by_text", "text": text, "method": "role-link"}
        except:
            pass
        
        # Strategy 4: Try finding in sidebar/nav areas (for GitHub, Linear, etc.)
        try:
            # Look for sidebar/nav containers
            sidebar_selectors = [
                'nav',
                'aside',
                '[role="navigation"]',
                '[class*="sidebar" i]',
                '[class*="nav" i]',
                '[class*="menu" i]'
            ]
            
            for sidebar_selector in sidebar_selectors:
                try:
                    sidebar = page.locator(sidebar_selector).first
                    if sidebar.is_visible(timeout=1000):
                        # Look for text in sidebar
                        element = sidebar.get_by_text(text, exact=False).first
                        if element.is_visible(timeout=timeout):
                            element.scroll_into_view_if_needed()
                            page.wait_for_timeout(300)
                            element.click()
                            return {"success": True, "action": "click_by_text", "text": text, "method": "sidebar"}
                except:
                    continue
        except:
            pass
        
        # Strategy 5: Try partial text match (for "New repository" when looking for "New")
        if len(text.split()) == 1:  # Single word
            try:
                # Find all clickable elements and check if text contains our search term
                all_clickables = page.locator('button, a, [role="button"], [role="link"]')
                count = all_clickables.count()
                for i in range(min(count, 50)):
                    try:
                        elem = all_clickables.nth(i)
                        if elem.is_visible(timeout=500):
                            elem_text = elem.text_content() or ""
                            if text.lower() in elem_text.lower() and len(elem_text.strip()) > 0:
                                elem.scroll_into_view_if_needed()
                                page.wait_for_timeout(300)
                                elem.click()
                                return {"success": True, "action": "click_by_text", "text": elem_text.strip(), "method": "partial-match"}
                    except:
                        continue
            except:
                pass
        
        # If all strategies fail, raise the original error
        raise PlaywrightTimeoutError(f"Element with text '{text}' not found")
    except PlaywrightTimeoutError:
        # Check auth state on timeout
        auth_state = detect_auth_state(page)
        error_msg = f"Element with text '{text}' not found"
        if auth_state["is_login_page"]:
            error_msg += " - appears to be on login/authentication page"
        return {
            "success": False,
            "action": "click_by_text",
            "error": error_msg,
            "auth_state": auth_state
        }
    except Exception as e:
        return {"success": False, "action": "click_by_text", "error": str(e)}


def wait_for_modal(page: Page, timeout: int = 10000) -> Dict[str, Any]:
    """
    Wait for a modal dialog to appear.
    
    Args:
        page: Playwright page object
        timeout: Wait timeout in milliseconds
        
    Returns:
        Result dictionary with success status
    """
    try:
        # Common modal selectors
        modal_selectors = [
            '[role="dialog"]',
            '.modal',
            '[class*="modal"]',
            '[class*="dialog"]',
            '[class*="overlay"]'
        ]
        
        for selector in modal_selectors:
            try:
                page.wait_for_selector(selector, timeout=2000, state="visible")
                return {"success": True, "action": "wait_for_modal", "selector": selector}
            except PlaywrightTimeoutError:
                continue
        
        return {"success": False, "action": "wait_for_modal", "error": "No modal found"}
    except Exception as e:
        return {"success": False, "action": "wait_for_modal", "error": str(e)}


def fill_inputs(page: Page, inputs: Dict[str, str], timeout: int = 10000, task_context: str = None, auto_submit_search: bool = True) -> Dict[str, Any]:
    """
    Fill multiple input fields by label, placeholder, name, or common selectors.
    Uses page analyzer for context-aware field detection.
    
    Args:
        page: Playwright page object
        inputs: Dictionary mapping field identifiers to values
        timeout: Wait timeout in milliseconds
        task_context: Optional task description for context-aware field matching
        
    Returns:
        Result dictionary with success status and filled fields
    """
    filled = {}
    errors = {}
    
    # Handle cookie consent first (common on Google, etc.)
    try:
        # Try to find and dismiss cookie consent buttons
        cookie_selectors = [
            'button:has-text("Accept")',
            'button:has-text("I agree")',
            'button:has-text("Accept all")',
            '[aria-label*="Accept" i]',
            '[aria-label*="I agree" i]',
            'button[id*="accept" i]',
            'button[class*="accept" i]'
        ]
        for selector in cookie_selectors:
            try:
                button = page.locator(selector).first
                if button.is_visible(timeout=1000):
                    button.click()
                    page.wait_for_timeout(500)
                    break
            except:
                continue
    except:
        pass
    
    for field_name, value in inputs.items():
        # Try context-aware field matching first
        if task_context:
            matching_input = find_matching_input(page, field_name)
            if matching_input:
                # Use the matched input's selector
                try:
                    # Try by name first
                    if matching_input.get("name"):
                        try:
                            input_elem = page.locator(f'input[name="{matching_input["name"]}"], textarea[name="{matching_input["name"]}"]').first
                            if input_elem.is_visible(timeout=2000):
                                input_elem.click()
                                input_elem.fill(value)
                                filled[field_name] = value
                                continue
                        except:
                            pass
                    
                    # Try by label
                    if matching_input.get("label"):
                        try:
                            label_elem = page.get_by_label(matching_input["label"], exact=False).first
                            if label_elem.is_visible(timeout=2000):
                                label_elem.click()
                                label_elem.fill(value)
                                filled[field_name] = value
                                continue
                        except:
                            pass
                except:
                    pass
        
        try:
            # Special handling for code editors (common case)
            if field_name.lower() in ["code", "editor", "solution"]:
                # Try to find code editor - contenteditable divs or textareas
                code_editor_selectors = [
                    '[contenteditable="true"]',
                    'textarea[class*="editor" i]',
                    'textarea[class*="code" i]',
                    'div[class*="editor" i][contenteditable]',
                    'div[class*="code" i][contenteditable]',
                    'textarea',
                    '[role="textbox"]'
                ]
                for selector in code_editor_selectors:
                    try:
                        editor = page.locator(selector).first
                        if editor.is_visible(timeout=2000):
                            editor.click()
                            # Clear existing content first
                            editor.clear()
                            editor.fill(value)
                            filled[field_name] = value
                            break
                    except PlaywrightTimeoutError:
                        continue
                if field_name in filled:
                    continue
            
            # Special handling for search boxes (Google, YouTube, etc.)
            if field_name.lower() in ["q", "search", "query"]:
                # Try common search box selectors (works for Google, YouTube, etc.)
                search_selectors = [
                    'input[name="q"]',
                    'input[name="search"]',
                    'input[name="search_query"]',  # YouTube
                    'textarea[name="q"]',
                    'textarea[name="search"]',
                    'input[type="search"]',
                    'input[aria-label*="Search" i]',
                    'input[aria-label="Search"]',  # YouTube exact match
                    'input[placeholder*="Search" i]',
                    'input[id*="search" i]',
                    'textarea[aria-label*="Search" i]',
                    'textarea[placeholder*="Search" i]'
                ]
                for selector in search_selectors:
                    try:
                        input_elem = page.locator(selector).first
                        input_elem.wait_for(state="visible", timeout=2000)
                        input_elem.click()  # Focus first
                        input_elem.fill(value)
                        filled[field_name] = value
                        break
                    except PlaywrightTimeoutError:
                        continue
                if field_name in filled:
                    continue
            
            # Try to find by label first
            try:
                label = page.get_by_label(field_name, exact=False).first
                label.wait_for(state="visible", timeout=2000)
                label.click()
                label.fill(value)
                filled[field_name] = value
                continue
            except PlaywrightTimeoutError:
                pass
            
            # Try to find by placeholder
            try:
                placeholder = page.get_by_placeholder(field_name, exact=False).first
                placeholder.wait_for(state="visible", timeout=2000)
                placeholder.click()
                placeholder.fill(value)
                filled[field_name] = value
                continue
            except PlaywrightTimeoutError:
                pass
            
            # Try to find input by name attribute
            try:
                name_input = page.locator(f'input[name*="{field_name}" i], textarea[name*="{field_name}" i]').first
                name_input.wait_for(state="visible", timeout=2000)
                name_input.click()
                name_input.fill(value)
                filled[field_name] = value
                continue
            except PlaywrightTimeoutError:
                pass
            
            # Try to find by id
            try:
                id_input = page.locator(f'input[id*="{field_name}" i], textarea[id*="{field_name}" i]').first
                id_input.wait_for(state="visible", timeout=2000)
                id_input.click()
                id_input.fill(value)
                filled[field_name] = value
                continue
            except PlaywrightTimeoutError:
                pass
            
            # Try to find any visible text input or textarea
            try:
                any_input = page.locator('input[type="text"], input[type="search"], textarea').filter(has_not=page.locator('[type="hidden"]')).first
                if any_input.is_visible(timeout=2000):
                    any_input.click()
                    any_input.fill(value)
                    filled[field_name] = value
                    continue
            except:
                pass
            
            errors[field_name] = "Field not found"
        except Exception as e:
            errors[field_name] = str(e)
    
    # Auto-submit search boxes if we filled a search field and auto_submit is enabled
    if auto_submit_search and len(filled) > 0:
        # Check if we filled a search field
        search_keys = ["q", "search", "query"]
        if any(key.lower() in search_keys for key in filled.keys()):
            # Check if the filled input is still focused or visible
            try:
                # Try to find the search input we just filled
                for field_name in filled.keys():
                    if field_name.lower() in search_keys:
                        # Try common search selectors
                        search_selectors = [
                            f'input[name="{field_name}"]',
                            f'input[name*="{field_name}" i]',
                            'input[type="search"]',
                            'input[aria-label*="Search" i]',
                            'textarea[name*="{field_name}" i]'
                        ]
                        for selector in search_selectors:
                            try:
                                search_input = page.locator(selector).first
                                if search_input.is_visible(timeout=500):
                                    # Don't auto-submit here - let click_submit handle it
                                    # But mark that this is a search context
                                    pass
                            except:
                                continue
            except:
                pass
    
    return {
        "success": len(filled) > 0,
        "action": "fill_inputs",
        "filled": filled,
        "errors": errors,
        "is_search": any(key.lower() in ["q", "search", "query"] for key in filled.keys())
    }


def click_submit(page: Page, button_texts: list = None, task_context: str = None, timeout: int = 10000) -> Dict[str, Any]:
    """
    Click a submit button by common text patterns or form submission.
    Uses smart matching to find buttons that contain keywords or match task context.
    
    Args:
        page: Playwright page object
        button_texts: List of button texts to try (defaults to common patterns)
        task_context: Optional task description to infer button text (e.g., "create project" → "Create Project")
        timeout: Wait timeout in milliseconds
        
    Returns:
        Result dictionary with success status
    """
    if button_texts is None:
        button_texts = ["Create", "New", "Add", "Save", "Submit", "Confirm", "Search", "Google Search"]
    
    # Strategy 0: Special handling for search boxes - press Enter instead of looking for button
    # This handles YouTube, Google, and any site with a search box
    try:
        # Check if we just filled a search input (common pattern)
        # Look for visible search inputs that might have been filled
        search_selectors = [
            'input[name="q"]',
            'input[name="search"]',
            'input[type="search"]',
            'textarea[name="q"]',
            'textarea[name="search"]',
            'input[aria-label*="Search" i]',
            'input[placeholder*="Search" i]',
            'input[id*="search" i]',
            'input[class*="search" i]',
            'textarea[aria-label*="Search" i]',
            'textarea[placeholder*="Search" i]'
        ]
        
        for selector in search_selectors:
            try:
                search_input = page.locator(selector).first
                if search_input.is_visible(timeout=1000):
                    # Check if input has value (was just filled)
                    value = search_input.input_value()
                    if value or search_input.is_focused():
                        # This is likely a search box that was just filled - press Enter
                        search_input.press("Enter")
                        # Pressed Enter on search box
                        return {"success": True, "action": "click_submit", "button": "Enter key (search)", "method": "search-enter"}
            except:
                continue
        
        # Also check if any focused input is a search box
        try:
            focused_input = page.locator('input:focus, textarea:focus').first
            if focused_input.is_visible(timeout=500):
                input_type = focused_input.get_attribute("type") or ""
                input_name = focused_input.get_attribute("name") or ""
                input_id = focused_input.get_attribute("id") or ""
                input_placeholder = focused_input.get_attribute("placeholder") or ""
                input_aria_label = focused_input.get_attribute("aria-label") or ""
                
                # Check if it's a search box by various attributes
                is_search = (
                    input_type == "search" or
                    "search" in input_name.lower() or
                    "q" in input_name.lower() or
                    "search" in input_id.lower() or
                    "search" in input_placeholder.lower() or
                    "search" in input_aria_label.lower()
                )
                
                if is_search:
                    focused_input.press("Enter")
                    # Pressed Enter on focused search box
                    return {"success": True, "action": "click_submit", "button": "Enter key (focused search)", "method": "search-enter"}
        except:
            pass
        
        # Last resort: if we just filled a search field, try to find and press Enter on any visible search input
        # This handles cases where the input might not be focused but is visible
        try:
            all_search_inputs = page.locator('input[type="search"], input[name*="search" i], input[name="q"], input[aria-label*="Search" i]')
            count = all_search_inputs.count()
            for i in range(min(count, 5)):
                try:
                    search_input = all_search_inputs.nth(i)
                    if search_input.is_visible(timeout=500):
                        value = search_input.input_value()
                        if value:  # Has a value, likely just filled
                            search_input.press("Enter")
                            # Pressed Enter on search input with value
                            return {"success": True, "action": "click_submit", "button": "Enter key (search with value)", "method": "search-enter"}
                except:
                    continue
        except:
            pass
    except:
        pass
    
    # Wait a bit for page/modal to settle
    page.wait_for_timeout(1000)
    
    # Strategy 0.5: Special handling for "Create" buttons - look for buttons with "Create" text
    # This is specifically for cases like "Create Repository" where we need to find the button
    # and skip header buttons (like search bars)
    if task_context and ("create" in task_context.lower() or "repository" in task_context.lower()):
        try:
            # Look for all buttons and filter by text containing "Create"
            all_buttons = page.locator('button, [role="button"], input[type="submit"]')
            count = all_buttons.count()
            for i in range(min(count, 50)):
                try:
                    button = all_buttons.nth(i)
                    if button.is_visible(timeout=1000):
                        button_text = button.text_content() or ""
                        
                        # Skip if button is in header/nav/search
                        try:
                            in_header = (
                                button.locator('xpath=ancestor::header | ancestor::nav | ancestor::*[contains(@class, "header") i] | ancestor::*[contains(@class, "nav") i] | ancestor::*[role="banner"]').count() > 0 or
                                button.locator('xpath=ancestor::*[contains(@class, "search") i]').count() > 0
                            )
                            if in_header:
                                continue  # Skip header buttons
                        except:
                            pass
                        
                        # Check if button text contains "Create" and is relevant
                        if "create" in button_text.lower() and len(button_text.strip()) > 0:
                            # Scroll into view (this will scroll to find buttons below the fold)
                            button.scroll_into_view_if_needed()
                            page.wait_for_timeout(500)
                            if button.is_visible(timeout=1000):
                                button.click()
                                return {"success": True, "action": "click_submit", "button": button_text.strip(), "method": "create-specific"}
                except:
                    continue
        except:
            pass
    
    # Strategy 1: Use page analyzer to find matching button (completely context-aware)
    # This now prioritizes buttons in modals
    if task_context:
        matching_button = find_matching_button(page, task_context, action_type="submit")
        if matching_button:
            button_text = matching_button["text"]
            is_in_modal = matching_button.get("in_modal", False)
            # Context-aware match found (debug output removed for cleaner submission)
            
            # Try multiple strategies to click the button, prioritizing modal selectors
            click_strategies = []
            
            # If button is in modal, try modal selectors first
            if is_in_modal:
                click_strategies.extend([
                    # Strategy 1: Find in modal by text (most specific)
                    lambda: page.locator('[role="dialog"] button, .modal button, [class*="modal" i] button, [class*="dialog" i] button').filter(has_text=button_text).first,
                    # Strategy 2: Find in modal by role
                    lambda: page.locator('[role="dialog"]').get_by_role("button", name=button_text, exact=False).first,
                    # Strategy 3: Find in modal by text content
                    lambda: page.locator('[role="dialog"]').get_by_text(button_text, exact=False).first,
                ])
            
            # Then try general selectors
            click_strategies.extend([
                # Strategy 4: By text content (most flexible)
                lambda: page.get_by_text(button_text, exact=False).first,
                # Strategy 5: By role with partial text
                lambda: page.get_by_role("button", name=button_text, exact=False).first,
                # Strategy 6: Find all buttons and match by text
                lambda: page.locator('button, input[type="button"], input[type="submit"]').filter(has_text=button_text).first,
            ])
            
            for i, strategy in enumerate(click_strategies, 1):
                try:
                    button = strategy()
                    if button.is_visible(timeout=2000):
                        # Scroll into view and wait for it to be stable
                        button.scroll_into_view_if_needed()
                        page.wait_for_timeout(500)  # Wait longer after scroll
                        # Check if button is still visible and clickable after scroll
                        if button.is_visible(timeout=1000):
                            button.click()
                            # Clicked button successfully
                            return {"success": True, "action": "click_submit", "button": button_text, "method": "context-aware"}
                except Exception as e:
                    continue
    
    # Strategy 2: Try exact and partial matches from button_texts
    # Prioritize buttons in forms/containers (not in header/nav)
    for text in button_texts:
        try:
            # First, try to find button in form/main content area (not header)
            # This avoids clicking search bars or header buttons
            try:
                # Look for buttons in forms, main content, or modals first
                # Exclude header/nav areas explicitly
                form_button = page.locator('form button, main button, [role="main"] button, [class*="form" i] button, [class*="content" i] button').filter(has_text=text).filter(has_not=page.locator('header, nav, [role="banner"], [class*="header" i], [class*="nav" i]')).first
                if form_button.is_visible(timeout=2000):
                    form_button.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    if form_button.is_visible(timeout=1000):
                        form_button.click()
                        return {"success": True, "action": "click_submit", "button": text, "method": "form-context"}
            except:
                pass
            
            # Try to find all buttons with this text and filter out header ones
            try:
                all_buttons = page.locator(f'button:has-text("{text}"), [role="button"]:has-text("{text}")')
                count = all_buttons.count()
                for i in range(count):
                    try:
                        button = all_buttons.nth(i)
                        if button.is_visible(timeout=1000):
                            # Check if button is in header/nav - if so, skip it
                            try:
                                # More aggressive check for header/nav
                                in_header = (
                                    button.locator('xpath=ancestor::header | ancestor::nav | ancestor::*[contains(@class, "header") i] | ancestor::*[contains(@class, "nav") i] | ancestor::*[role="banner"]').count() > 0 or
                                    button.locator('xpath=ancestor::*[contains(@class, "search") i]').count() > 0
                                )
                                if in_header:
                                    continue  # Skip header buttons (like search)
                            except:
                                pass
                            
                            # This button is not in header - scroll to it and click
                            button.scroll_into_view_if_needed()
                            page.wait_for_timeout(500)
                            if button.is_visible(timeout=1000):
                                button.click()
                                return {"success": True, "action": "click_submit", "button": text, "method": "filtered-match"}
                    except:
                        continue
            except:
                pass
            
            # Try exact match first (but skip if in header)
            button = page.get_by_role("button", name=text, exact=True).first
            try:
                button.wait_for(state="visible", timeout=2000)
                # Check if button is in a form/main area (not header/nav)
                # Skip if it's in header/nav (likely search bar)
                try:
                    # More aggressive check for header/nav
                    in_header = (
                        button.locator('xpath=ancestor::header | ancestor::nav | ancestor::*[contains(@class, "header") i] | ancestor::*[contains(@class, "nav") i] | ancestor::*[role="banner"]').count() > 0 or
                        button.locator('xpath=ancestor::*[contains(@class, "search") i]').count() > 0
                    )
                    if in_header:
                        continue  # Skip header buttons (like search)
                except:
                    pass
                
                button.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                if button.is_visible(timeout=1000):
                    button.click()
                    return {"success": True, "action": "click_submit", "button": text}
            except PlaywrightTimeoutError:
                pass
            
            # Try partial match (case-insensitive) - but skip header
            button = page.get_by_role("button", name=text, exact=False).first
            try:
                button.wait_for(state="visible", timeout=2000)
                # Check if button is in header/nav - if so, skip it
                try:
                    # More aggressive check for header/nav
                    in_header = (
                        button.locator('xpath=ancestor::header | ancestor::nav | ancestor::*[contains(@class, "header") i] | ancestor::*[contains(@class, "nav") i] | ancestor::*[role="banner"]').count() > 0 or
                        button.locator('xpath=ancestor::*[contains(@class, "search") i]').count() > 0
                    )
                    if in_header:
                        continue  # Skip header buttons
                except:
                    pass
                
                button.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                if button.is_visible(timeout=1000):
                    button.click()
                    return {"success": True, "action": "click_submit", "button": text}
            except PlaywrightTimeoutError:
                pass
        except Exception:
            continue
    
    # Strategy 3: Find buttons in modal first (critical for forms)
    # Check if we're in a modal context
    try:
        modal_selectors = [
            '[role="dialog"]',
            '.modal',
            '[class*="modal" i]',
            '[class*="dialog" i]',
            '[class*="overlay" i]'
        ]
        
        has_modal = False
        for selector in modal_selectors:
            try:
                if page.locator(selector).first.is_visible(timeout=500):
                    has_modal = True
                    break
            except:
                continue
        
        if has_modal:
            # Modal detected - searching for buttons in modal
            # Look for buttons in modal with action keywords
            keyword_texts = ["Create", "Save", "Submit", "Confirm", "Add", "New"]
            
            for keyword in keyword_texts:
                try:
                    # Try multiple modal selectors
                    modal_button_selectors = [
                        f'[role="dialog"] button:has-text("{keyword}")',
                        f'.modal button:has-text("{keyword}")',
                        f'[class*="modal" i] button:has-text("{keyword}")',
                        f'[class*="dialog" i] button:has-text("{keyword}")',
                    ]
                    
                    for modal_selector in modal_button_selectors:
                        try:
                            buttons = page.locator(modal_selector)
                            count = buttons.count()
                            for i in range(count):
                                try:
                                    button = buttons.nth(i)
                                    if button.is_visible(timeout=1000):
                                        button_text = button.text_content() or ""
                                        # Skip cancel/close buttons
                                        if any(cancel in button_text.lower() for cancel in ["cancel", "close", "dismiss", "×"]):
                                            continue
                                        if len(button_text.strip()) > 0:
                                            # Scroll into view and ensure it's clickable
                                            button.scroll_into_view_if_needed()
                                            page.wait_for_timeout(500)  # Wait longer after scroll
                                            # Verify button is still visible after scroll
                                            if button.is_visible(timeout=1000):
                                                button.click()
                                                # Clicked button in modal
                                                return {"success": True, "action": "click_submit", "button": button_text.strip(), "method": "modal-keyword"}
                                except:
                                    continue
                        except:
                            continue
                except:
                    continue
            
            # Fallback: Find any non-cancel button in modal
            try:
                all_modal_buttons = page.locator('[role="dialog"] button, .modal button, [class*="modal" i] button')
                count = all_modal_buttons.count()
                # Found buttons in modal, checking...
                for i in range(count):
                    try:
                        button = all_modal_buttons.nth(i)
                        if button.is_visible(timeout=1000):
                            button_text = button.text_content() or ""
                            # Skip cancel/close buttons
                            if any(cancel in button_text.lower() for cancel in ["cancel", "close", "dismiss", "×", "back"]):
                                continue
                            if len(button_text.strip()) > 0:
                                # Scroll into view and ensure it's clickable
                                button.scroll_into_view_if_needed()
                                page.wait_for_timeout(500)  # Wait longer after scroll
                                # Verify button is still visible after scroll
                                if button.is_visible(timeout=1000):
                                    button.click()
                                    # Clicked first non-cancel button in modal
                                    return {"success": True, "action": "click_submit", "button": button_text.strip(), "method": "modal-fallback"}
                    except:
                        continue
            except:
                pass
    except:
        pass
    
    # Strategy 4: Find buttons that contain keywords (flexible matching) - page-wide search
    # But prioritize buttons NOT in header/nav
    keyword_texts = ["Create", "Save", "Submit", "Confirm", "Add", "New"]
    for keyword in keyword_texts:
        try:
            # Find all buttons and filter by text containing keyword
            buttons = page.locator('button, input[type="button"], input[type="submit"], a[role="button"]')
            count = buttons.count()
            
            # First pass: Find buttons NOT in header/nav
            for i in range(min(count, 50)):  # Limit to avoid performance issues
                try:
                    button = buttons.nth(i)
                    if button.is_visible(timeout=500):
                        # Check if button is in header/nav - if so, skip it
                        try:
                            in_header = (
                                button.locator('xpath=ancestor::header | ancestor::nav | ancestor::*[contains(@class, "header") i] | ancestor::*[contains(@class, "nav") i] | ancestor::*[role="banner"]').count() > 0 or
                                button.locator('xpath=ancestor::*[contains(@class, "search") i]').count() > 0
                            )
                            if in_header:
                                continue  # Skip header buttons
                        except:
                            pass
                        
                        button_text = button.text_content() or ""
                        # Skip cancel/close buttons
                        if any(cancel in button_text.lower() for cancel in ["cancel", "close", "dismiss", "×"]):
                            continue
                        if keyword.lower() in button_text.lower() and len(button_text.strip()) > 0:
                            # Scroll into view and ensure it's clickable
                            button.scroll_into_view_if_needed()
                            page.wait_for_timeout(500)  # Wait longer after scroll
                            # Verify button is still visible after scroll
                            if button.is_visible(timeout=1000):
                                button.click()
                                # Clicked button with keyword match (not in header)
                                return {"success": True, "action": "click_submit", "button": button_text.strip(), "method": "keyword-match"}
                except:
                    continue
            
            # Second pass: If no non-header button found, try all buttons (fallback)
            for i in range(min(count, 50)):
                try:
                    button = buttons.nth(i)
                    if button.is_visible(timeout=500):
                        button_text = button.text_content() or ""
                        # Skip cancel/close buttons
                        if any(cancel in button_text.lower() for cancel in ["cancel", "close", "dismiss", "×"]):
                            continue
                        if keyword.lower() in button_text.lower() and len(button_text.strip()) > 0:
                            # Scroll into view and ensure it's clickable
                            button.scroll_into_view_if_needed()
                            page.wait_for_timeout(500)
                            if button.is_visible(timeout=1000):
                                button.click()
                                return {"success": True, "action": "click_submit", "button": button_text.strip(), "method": "keyword-match-fallback"}
                except:
                    continue
        except:
            continue
    
    # Strategy 5: Try to find submit button by type
    try:
        submit_button = page.locator('input[type="submit"], button[type="submit"]').first
        if submit_button.is_visible(timeout=2000):
            submit_button.scroll_into_view_if_needed()
            page.wait_for_timeout(500)  # Wait longer after scroll
            # Verify button is still visible after scroll
            if submit_button.is_visible(timeout=1000):
                submit_button.click()
                # Clicked submit button by type
                return {"success": True, "action": "click_submit", "button": "submit button", "method": "submit-type"}
    except:
        pass
    
    # Debug: Print all visible buttons for troubleshooting (only if verbose mode)
    # Removed verbose debug output for cleaner submission
    
    return {"success": False, "action": "click_submit", "error": "No submit button found"}


def capture_state(page: Page) -> Dict[str, Any]:
    """
    Capture the current page state (for metadata).
    
    Args:
        page: Playwright page object
        
    Returns:
        State dictionary with URL and other metadata
    """
    try:
        url = page.url
        title = page.title()
        return {
            "success": True,
            "action": "capture_state",
            "url": url,
            "title": title
        }
    except Exception as e:
        return {
            "success": False,
            "action": "capture_state",
            "error": str(e)
        }


def execute_action(page: Page, action: Dict[str, Any], config: Dict[str, Any] = None, task_context: str = None, skip_auth_check: bool = False) -> Dict[str, Any]:
    """
    Execute a generic action based on action type.
    
    Args:
        page: Playwright page object
        action: Action dictionary with 'type' and parameters
        config: Configuration dictionary (for button texts, etc.)
        task_context: Optional task description for context-aware actions
        skip_auth_check: If True, skip login page check (useful after manual login)
        
    Returns:
        Result dictionary from the action
    """
    action_type = action.get("type", "").lower()
    config = config or {}
    button_texts = config.get("common_button_text", ["Create", "New", "Add", "Save", "Submit"])
    
    if action_type == "goto":
        return goto(page, action.get("url", ""))
    elif action_type == "click_by_text":
        return click_by_text(page, action.get("text", ""), task_context=task_context, skip_auth_check=skip_auth_check)
    elif action_type == "wait_for_modal":
        return wait_for_modal(page)
    elif action_type == "fill_inputs":
        return fill_inputs(page, action.get("inputs", {}), task_context=task_context)
    elif action_type == "click_submit":
        return click_submit(page, button_texts, task_context=task_context)
    elif action_type == "capture_state":
        return capture_state(page)
    else:
        return {
            "success": False,
            "action": action_type,
            "error": f"Unknown action type: {action_type}"
        }


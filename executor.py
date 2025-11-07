"""
Executor module for running UI actions via Playwright.
"""
import os
from pathlib import Path
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

from actions import execute_action, detect_auth_state
from state_manager import StateManager


class Executor:
    """
    Executes UI actions using Playwright.
    """
    
    def __init__(self, config: Dict[str, Any], state_manager: StateManager):
        """
        Initialize the Executor.
        
        Args:
            config: Configuration dictionary
            state_manager: StateManager instance for capturing states
        """
        self.config = config
        self.state_manager = state_manager
        self.headless = config.get("headless", False)
        self.slow_mo = config.get("slow_mo", 300)
        self.persistent_context = config.get("persistent_context", True)
        self.persistent_context_dir = config.get("persistent_context_dir", ".browser_context")
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.playwright = None
    
    def __enter__(self):
        """Context manager entry."""
        self.playwright = sync_playwright().start()
        
        # Use persistent context if enabled (saves login state)
        if self.persistent_context:
            context_path = Path(self.persistent_context_dir)
            context_path.mkdir(exist_ok=True)
            
            try:
                # Try to use persistent context (saves cookies/sessions)
                self.context = self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(context_path),
                    headless=self.headless,
                    slow_mo=self.slow_mo
                )
                # Get the first page or create a new one
                if len(self.context.pages) > 0:
                    self.page = self.context.pages[0]
                else:
                    self.page = self.context.new_page()
            except Exception as e:
                print(f"  ⚠️  Warning: Could not create persistent context: {e}")
                print("  Falling back to regular browser context...")
                # Fallback to regular context
                self.browser = self.playwright.chromium.launch(
                    headless=self.headless,
                    slow_mo=self.slow_mo
                )
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
        else:
            # Regular browser context (no persistence)
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo
            )
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Persistent context closes automatically
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def execute_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute a list of actions sequentially.
        
        Args:
            actions: List of action dictionaries
            
        Returns:
            List of action results
        """
        results = []
        
        print(f"\n🚀 Executing {len(actions)} actions...")
        
        # Capture initial state
        print("\n[0/{}] Initial state".format(len(actions)))
        self.state_manager.capture_initial_state(self.page)
        
        # Get task description for context-aware button detection
        task_description = getattr(self, 'task_description', None)
        
        for i, action in enumerate(actions, 1):
            action_type = action.get("type", "unknown")
            print(f"\n[{i}/{len(actions)}] {action_type}")
            
            # Execute the action (pass task context for smart button detection)
            result = execute_action(self.page, action, self.config, task_context=task_description)
            results.append(result)
            
            # Check for login requirement AFTER goto action
            if action_type == "goto":
                # Wait a bit for page to load (even if navigation "failed")
                self.page.wait_for_timeout(5000)  # Increased wait time
                
                # Try to wait for page to be ready
                try:
                    self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                except:
                    pass
                
                # Wait a bit more for dynamic content to load
                self.page.wait_for_timeout(2000)
                
                auth_state = detect_auth_state(self.page)
                
                # Check if login is required (completely general - no hardcoded domains)
                # Use general patterns: if we're on a homepage and see login button, prompt
                url = auth_state.get("url", "").lower()
                
                # General pattern: if URL is a root domain (no path or just /) and has login button
                is_root_page = url.count('/') <= 3  # e.g., https://example.com or https://example.com/
                
                # More aggressive check: if we're on a root page and see login button, prompt
                # This is general - works for any app
                should_prompt_login = (
                    auth_state.get("requires_login", False) or 
                    auth_state.get("has_login_button", False) or
                    (is_root_page and auth_state.get("has_login_button", False))
                )
                
                if should_prompt_login:
                    print("\n" + "=" * 60)
                    print("🔐 LOGIN REQUIRED")
                    print("=" * 60)
                    print(f"  Detected at: {auth_state['url']}")
                    
                    if auth_state.get("has_login_button"):
                        print(f"  Found login button: '{auth_state.get('login_button_text', 'login')}'")
                        print("\n  Please click the login button and complete authentication.")
                    elif auth_state.get("is_login_page"):
                        print("  Detected login page.")
                        print("\n  Please log in manually in the browser window.")
                    elif is_homepage:
                        print("  On homepage - login may be required to access features.")
                        print("  Please look for 'Sign in' or 'Log in' button in the browser.")
                        print("  Click it and complete authentication.")
                    else:
                        print("  Login may be required to continue.")
                        print("\n  Please log in manually in the browser window.")
                    
                    print("\n  The browser will wait for you to complete login.")
                    print("  After logging in, press ENTER here to continue...")
                    print("=" * 60)
                    
                    # Wait for user to log in
                    input("\n  👆 Log in now, then press ENTER to continue: ")
                    
                    # Wait a bit for page to settle after login
                    self.page.wait_for_timeout(3000)
                    
                    # Re-check auth state
                    auth_state = detect_auth_state(self.page)
                    if auth_state.get("requires_login", False):
                        print("  ⚠️  Still appears to require login. Continuing anyway...")
                    else:
                        print("  ✓ Login detected! Continuing with task...")
                    
                    # Re-capture state after login
                    self.state_manager.capture_if_changed(self.page, "after-login", force=True)
            
            # Print action result
            if result.get("success"):
                print(f"  ✓ Action succeeded")
            else:
                error = result.get("error", "Unknown error")
                print(f"  ✗ Action failed: {error}")
            
            # Wait for network/idle after actions that might trigger changes
            if action_type in ["goto", "click_by_text", "click_submit", "fill_inputs"]:
                try:
                    self.page.wait_for_load_state("networkidle", timeout=3000)
                except:
                    pass  # Continue if timeout
            
            # Special handling: if we just filled inputs and next action is click_submit,
            # check if it's a search context (for better search handling)
            if action_type == "fill_inputs" and i < len(actions):
                next_action = actions[i] if i < len(actions) else None
                if next_action and next_action.get("type") == "click_submit":
                    # Check if we filled a search field
                    filled_inputs = result.get("filled", {})
                    if any(key.lower() in ["q", "search", "query"] for key in filled_inputs.keys()):
                        # This is likely a search - the click_submit will handle it with Enter key
                        pass
            
            # Wait a bit for DOM to update
            self.page.wait_for_timeout(1000)
            
            # Capture state after each action (force capture if action succeeded)
            action_name = action_type.replace("_", "-")
            force_capture = result.get("success", False)
            self.state_manager.capture_if_changed(self.page, action_name, force=force_capture)
        
        return results


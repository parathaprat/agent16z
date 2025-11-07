"""
State manager for detecting UI changes and capturing screenshots.
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.sync_api import Page

from utils import dom_hash, timestamp, ensure_dir


class StateManager:
    """
    Manages UI state detection and screenshot capture.
    """
    
    def __init__(self, dataset_root: str, task_slug: str):
        """
        Initialize the StateManager.
        
        Args:
            dataset_root: Root directory for dataset storage
            task_slug: Slugified task name for folder organization
        """
        self.dataset_root = Path(dataset_root)
        self.task_slug = task_slug
        self.task_dir = ensure_dir(self.dataset_root / task_slug)
        self.state_index = 0
        self.last_dom_hash: Optional[str] = None
        self.captured_states = []
    
    def capture_if_changed(self, page: Page, action_name: str, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Capture a screenshot if the DOM has changed.
        
        Args:
            page: Playwright page object
            action_name: Name of the action that triggered this capture
            force: If True, capture even if DOM hasn't changed
            
        Returns:
            Metadata dictionary if state was captured, None otherwise
        """
        try:
            # Wait a bit for DOM to settle
            page.wait_for_timeout(500)
            
            # Get current DOM
            html = page.content()
            current_hash = dom_hash(html)
            
            # Check if DOM has changed (or if forced)
            if not force and current_hash == self.last_dom_hash:
                print(f"  ⊘ No change detected for: {action_name}")
                return None
            
            # DOM has changed or forced, capture state
            self.last_dom_hash = current_hash
            self.state_index += 1
            
            # Get page metadata
            url = page.url
            ts = timestamp()
            
            # Take screenshot
            screenshot_filename = f"{self.state_index:03d}_{action_name}.png"
            screenshot_path = self.task_dir / screenshot_filename
            page.screenshot(path=str(screenshot_path), full_page=True)
            
            # Create metadata
            metadata = {
                "index": self.state_index,
                "url": url,
                "timestamp": ts,
                "dom_hash": current_hash,
                "step": action_name,
                "screenshot": screenshot_filename
            }
            
            # Save metadata JSON
            metadata_filename = f"{self.state_index:03d}_{action_name}.json"
            metadata_path = self.task_dir / metadata_filename
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.captured_states.append(metadata)
            
            print(f"  ✓ Captured state {self.state_index}: {action_name} (hash: {current_hash[:16]}...)")
            
            return metadata
            
        except Exception as e:
            print(f"  ✗ Error capturing state: {e}")
            return None
    
    def capture_initial_state(self, page: Page) -> Optional[Dict[str, Any]]:
        """
        Capture the initial state before any actions.
        
        Args:
            page: Playwright page object
            
        Returns:
            Metadata dictionary if state was captured, None otherwise
        """
        return self.capture_if_changed(page, "initial", force=True)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of captured states.
        
        Returns:
            Summary dictionary with statistics
        """
        return {
            "task_slug": self.task_slug,
            "total_states": self.state_index,
            "task_dir": str(self.task_dir),
            "states": self.captured_states
        }


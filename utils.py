"""
Utility functions for the softlight-agent project.
"""
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Union


def slugify(text: str) -> str:
    """
    Convert a task description into a folder-safe slug.
    
    Args:
        text: The task description text
        
    Returns:
        A slugified string safe for use in file paths
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


def dom_hash(html: str) -> str:
    """
    Generate a hash of the normalized DOM for change detection.
    
    Args:
        html: The HTML content to hash
        
    Returns:
        A hexadecimal hash string
    """
    # Remove script and style tags (they change but don't affect visual state)
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Normalize whitespace (but preserve structure)
    normalized = re.sub(r'\s+', ' ', html.strip())
    
    # Generate SHA256 hash
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def timestamp() -> str:
    """
    Get current UTC timestamp in ISO format.
    
    Returns:
        ISO format timestamp string
    """
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Create a directory if it doesn't exist.
    
    Args:
        path: The directory path to ensure exists
        
    Returns:
        Path object of the directory
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


"""
Main entry point for softlight-agent.
"""
import sys
import yaml
from pathlib import Path

from planner import plan
from executor import Executor
from state_manager import StateManager
from utils import slugify, ensure_dir


def load_config(config_path: str = "config.yaml") -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """
    Main function to run the softlight-agent.
    """
    if len(sys.argv) < 2:
        print("Usage: python main.py '<task description>'")
        print("Example: python main.py 'create a project in Linear'")
        sys.exit(1)
    
    task = " ".join(sys.argv[1:])
    
    print("=" * 60)
    print("🤖 Softlight Agent - UI Workflow Capture")
    print("=" * 60)
    print(f"\n📝 Task: {task}\n")
    
    # Load configuration
    try:
        config = load_config()
    except FileNotFoundError:
        print("❌ Error: config.yaml not found")
        sys.exit(1)
    
    # Create task slug and ensure dataset directory exists
    task_slug = slugify(task)
    dataset_root = config.get("dataset_root", "dataset")
    ensure_dir(dataset_root)
    
    # Initialize state manager
    state_manager = StateManager(dataset_root, task_slug)
    
    # Generate plan
    actions = plan(task, config)
    
    if not actions:
        print("❌ Error: No actions generated")
        sys.exit(1)
    
    # Print the full plan before execution
    print("\n" + "=" * 60)
    print("📋 Generated Action Plan")
    print("=" * 60)
    for i, action in enumerate(actions, 1):
        action_type = action.get("type", "unknown")
        action_desc = f"[{i}] {action_type}"
        
        # Add details based on action type
        if action_type == "goto":
            action_desc += f" → {action.get('url', '')}"
        elif action_type == "click_by_text":
            action_desc += f" → '{action.get('text', '')}'"
        elif action_type == "fill_inputs":
            inputs = action.get("inputs", {})
            if inputs:
                # Show first input key and value preview
                first_key = list(inputs.keys())[0]
                first_val = str(inputs[first_key])
                if len(first_val) > 50:
                    first_val = first_val[:50] + "..."
                action_desc += f" → {first_key}: {first_val}"
        elif action_type == "wait_for_modal":
            action_desc += " → waiting for modal/dialog"
        elif action_type == "click_submit":
            action_desc += " → clicking submit button"
        elif action_type == "capture_state":
            action_desc += " → capturing screenshot"
        
        print(f"  {action_desc}")
    print("=" * 60)
    
    # Execute actions
    try:
        with Executor(config, state_manager) as executor:
            # Pass task description for context-aware actions
            executor.task_description = task
            results = executor.execute_actions(actions)
            
            # Print summary
            summary = state_manager.get_summary()
            print("\n" + "=" * 60)
            print("✅ Execution Complete")
            print("=" * 60)
            print(f"\n📊 Summary:")
            print(f"  • Task: {task}")
            print(f"  • Actions executed: {len(actions)}")
            print(f"  • States captured: {summary['total_states']}")
            print(f"  • Output directory: {summary['task_dir']}")
            print(f"\n📁 Screenshots and metadata saved to:")
            print(f"   {summary['task_dir']}\n")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


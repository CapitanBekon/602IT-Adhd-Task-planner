"""Core task management system with JSON persistence and enhanced features."""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class TaskManager:
    """Enhanced task manager with subtasks, priority, effort tracking and hardware integration."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.tasks_file = self.data_dir / "tasks.json"
        self.tasks: List[Dict[str, Any]] = []
        self.load_tasks()
        
    def load_tasks(self) -> None:
        """Load tasks from JSON file."""
        try:
            if self.tasks_file.exists():
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = [self._normalize_task(task) for task in data]
                logger.info(f"Loaded {len(self.tasks)} tasks from {self.tasks_file}")
            else:
                self.tasks = []
                logger.info("No tasks file found, starting with empty list")
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")
            self.tasks = []
            
    def save_tasks(self) -> None:
        """Save tasks to JSON file."""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.tasks)} tasks to {self.tasks_file}")
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")
            
    def _normalize_task(self, task: Any) -> Dict[str, Any]:
        """Normalize task data to standard format with all required fields."""
        if isinstance(task, str):
            return {
                "id": None,
                "title": task,
                "status": 0,  # 0=not started, 1=in progress, 2=completed
                "priority": 0,  # 0=low, higher numbers = higher priority
                "effort": 0,    # effort level estimate
                "due_date": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "has_subtasks": False,
                "subtasks": []
            }
        elif isinstance(task, dict):
            # Handle legacy formats
            normalized = {
                "id": task.get("id"),
                "title": task.get("title", task.get("task", "")),
                "status": int(task.get("status", 0)),
                "priority": int(task.get("priority", task.get("want", 0))),  # 'want' for legacy compatibility
                "effort": int(task.get("effort", 0)),
                "due_date": task.get("due_date"),
                "created_at": task.get("created_at", datetime.now().isoformat()),
                "updated_at": task.get("updated_at", datetime.now().isoformat()),
                "has_subtasks": bool(task.get("has_subtasks", False)),
                "subtasks": [self._normalize_task(st) for st in task.get("subtasks", [])]
            }
            # Auto-detect subtasks
            if normalized["subtasks"] and not normalized["has_subtasks"]:
                normalized["has_subtasks"] = True
            return normalized
        else:
            return self._normalize_task(str(task))
            
    def add_task(self, title: str, priority: int = 0, effort: int = 0, 
                 due_date: Union[str, date, None] = None, interactive: bool = False) -> int:
        """Add a new task and return its index (1-based)."""
        
        # Interactive mode for detailed task creation
        if interactive:
            print(f"Creating task: {title}")
            
            # Get due date
            if due_date is None:
                due_input = input("Enter due date (YYYY-MM-DD) or leave blank: ").strip()
                if due_input:
                    try:
                        due_dt = datetime.fromisoformat(due_input)
                        due_date = due_dt.date().isoformat()
                    except Exception:
                        print("Invalid date format, saving without due date.")
                        due_date = None
                        
            # Get effort
            if effort == 0:
                effort_input = input("Enter effort (1-10) or leave blank: ").strip()
                try:
                    effort = int(effort_input) if effort_input else 0
                    effort = max(0, min(10, effort))  # Clamp to 0-10
                except ValueError:
                    print("Invalid effort value, defaulting to 0.")
                    effort = 0
                    
            # Get priority
            if priority == 0:
                priority_input = input("Enter priority (1-10) or leave blank: ").strip()
                try:
                    priority = int(priority_input) if priority_input else 0
                    priority = max(0, min(10, priority))  # Clamp to 0-10
                except ValueError:
                    print("Invalid priority value, defaulting to 0.")
                    priority = 0
        
        # Convert due_date to string if it's a date object
        if isinstance(due_date, date):
            due_date = due_date.isoformat()
        
        task = {
            "id": len(self.tasks) + 1,
            "title": title,
            "status": 0,
            "priority": priority,
            "effort": effort,
            "due_date": due_date,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "has_subtasks": False,
            "subtasks": []
        }
        
        # Check if effort is high and offer subtasks with Yes/No/Cancel
        if interactive and effort >= 5:
            while True:
                choice = input("Effort >= 5 detected. Create subtasks? (y = yes, n = no, c = cancel): ").strip().lower()
                if not choice:
                    continue
                if choice.startswith('c'):
                    print("Task creation cancelled.")
                    return 0
                if choice.startswith('n'):
                    # Create as a normal task
                    break
                if choice.startswith('y'):
                    task["has_subtasks"] = True
                    # Prompt for subtasks; user can finish by entering blank or 'c' to cancel all
                    cancelled = self._prompt_add_subtasks(task)
                    if cancelled:
                        print("Task creation cancelled.")
                        return 0
                    break
                print("Please enter 'y', 'n', or 'c'.")
        
        self.tasks.append(task)
        self.save_tasks()
        logger.info(f"Added task: {title}")
        return len(self.tasks)
        
    def _prompt_add_subtasks(self, parent_task: Dict[str, Any]) -> None:
        """Interactive subtask creation."""
        while True:
            ans = input(f"Add a subtask to '{parent_task.get('title')}'? (y/n/cancel): ").strip().lower()
            if not ans:
                continue
            if ans.startswith('c'):
                # Cancel entire task creation flow
                return True
            if not ans.startswith('y'):
                return False
            child_title = input("Enter subtask title (or 'c' to cancel): ").strip()
            if not child_title:
                # blank title means done adding subtasks
                return False
            if child_title.lower().startswith('c'):
                return True
            child = self._create_task_interactive(child_title)
            parent_task["subtasks"].append(child)
            parent_task["has_subtasks"] = True
        # default return (should not reach)
        return False
                
    def _create_task_interactive(self, title: str) -> Dict[str, Any]:
        """Create a task interactively (for subtasks)."""
        due_input = input("Enter due date (YYYY-MM-DD) or leave blank: ").strip()
        due_date = None
        if due_input:
            try:
                due_dt = datetime.fromisoformat(due_input)
                due_date = due_dt.date().isoformat()
            except Exception:
                print("Invalid date format, saving without due date.")
                due_date = None
                
        effort_input = input("Enter effort (1-10) or leave blank: ").strip()
        try:
            effort_val = int(effort_input) if effort_input else 0
            effort_val = max(0, min(10, effort_val))
        except ValueError:
            print("Invalid effort value, defaulting to 0.")
            effort_val = 0
            
        priority_input = input("Enter priority (1-10) or leave blank: ").strip()
        try:
            priority_val = int(priority_input) if priority_input else 0
            priority_val = max(0, min(10, priority_val))
        except ValueError:
            print("Invalid priority value, defaulting to 0.")
            priority_val = 0
            
        task = {
            "id": None,  # Subtasks don't need IDs
            "title": title,
            "status": 0,
            "priority": priority_val,
            "effort": effort_val,
            "due_date": due_date,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "has_subtasks": False,
            "subtasks": []
        }
        
        if effort_val > 5:
            choice = input("Effort > 5 detected for this subtask. Split further? (y/n): ").strip().lower()
            if choice.startswith('y'):
                task["has_subtasks"] = True
                self._prompt_add_subtasks(task)
                
        return task
        
    def remove_task(self, task_index: int) -> bool:
        """Remove a task by index (1-based). Returns True if successful."""
        if 1 <= task_index <= len(self.tasks):
            removed = self.tasks.pop(task_index - 1)
            # Update IDs for remaining tasks
            for i, task in enumerate(self.tasks):
                task["id"] = i + 1
            self.save_tasks()
            logger.info(f"Removed task: {removed.get('title', 'Unknown')}")
            return True
        return False
        
    def get_task(self, task_index: int) -> Optional[Dict[str, Any]]:
        """Get a task by index (1-based)."""
        if 1 <= task_index <= len(self.tasks):
            return self.tasks[task_index - 1]
        return None
        
    def update_task_status(self, task_index: int, status: int = None) -> Optional[int]:
        """Update task status. If status is None, cycle through 0->1->2->0."""
        task = self.get_task(task_index)
        if task:
            if status is None:
                # Cycle through statuses
                task["status"] = (task["status"] + 1) % 3
            else:
                task["status"] = max(0, min(2, int(status)))
            task["updated_at"] = datetime.now().isoformat()
            self.save_tasks()
            logger.info(f"Updated task {task_index} status to {task['status']}")
            return task["status"]
        return None
        
    def increment_completion(self, task_index: int) -> Optional[int]:
        """Increment task completion status (0->1->2->0). Alias for update_task_status."""
        return self.update_task_status(task_index)
        
    def find_task_by_title(self, title: str) -> Optional[int]:
        """Find task index by title (case-insensitive). Returns 1-based index."""
        title_lower = title.lower().strip()
        for i, task in enumerate(self.tasks):
            if task.get("title", "").lower().strip() == title_lower:
                return i + 1
        return None
        
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks."""
        return self.tasks.copy()
        
    def get_task_count(self) -> int:
        """Get total number of tasks."""
        return len(self.tasks)
        
    def get_status_name(self, status: int) -> str:
        """Convert status number to human readable name."""
        status_names = {0: "Not Started", 1: "In Progress", 2: "Completed"}
        return status_names.get(status, "Unknown")
        
    def sort_tasks(self, sort_by: str = "priority") -> None:
        """Sort tasks by various criteria."""
        if sort_by == "priority":
            self.tasks.sort(key=lambda x: x.get("priority", 0), reverse=True)
        elif sort_by == "due_date":
            def due_key(task):
                d = task.get('due_date')
                if not d:
                    return datetime.max
                try:
                    return datetime.fromisoformat(d)
                except Exception:
                    return datetime.max
            self.tasks.sort(key=due_key)
        elif sort_by == "effort":
            self.tasks.sort(key=lambda x: x.get("effort", 0))
        elif sort_by == "status":
            self.tasks.sort(key=lambda x: x.get("status", 0))
        elif sort_by == "title":
            self.tasks.sort(key=lambda x: x.get("title", "").lower())
        else:
            raise ValueError(f"Unknown sort criteria: {sort_by}")
            
        # Update IDs after sorting
        for i, task in enumerate(self.tasks):
            task["id"] = i + 1
            
        self.save_tasks()
        logger.info(f"Tasks sorted by {sort_by}")
        
    def view_tasks(self, show_subtasks: bool = True, current_parent: int = None) -> None:
        """Display tasks in a formatted way."""
        if current_parent is not None:
            self.view_subtasks(current_parent)
            return
            
        if not self.tasks:
            print("No tasks available.")
            return
            
        print("\n=== TASKS ===")
        for i, task in enumerate(self.tasks, 1):
            self._print_task(task, prefix=str(i), show_subtasks=show_subtasks)
        print()
        
    def view_subtasks(self, parent_id: int) -> None:
        """Print only the subtasks for a given top-level task (1-based parent_id)."""
        if not isinstance(parent_id, int) or parent_id < 1 or parent_id > len(self.tasks):
            print("Invalid parent task ID.")
            return
            
        parent = self.tasks[parent_id - 1]
        if not isinstance(parent, dict):
            print("Parent task malformed; cannot show subtasks.")
            return
            
        subs = parent.get('subtasks', []) or []
        if not subs:
            print(f"Task {parent_id} ('{parent.get('title', '')}') has no subtasks.")
            return
            
        print(f"\nSubtasks for Task {parent_id}: {parent.get('title', '')}")
        for idx, sub in enumerate(subs, 1):
            if isinstance(sub, dict):
                self._print_task(sub, prefix=f"{idx}", indent=1)
            else:
                print(f"  {idx}. {str(sub)}")
        print()
        
    def _print_task(self, task: Dict[str, Any], prefix: str = "", indent: int = 0, show_subtasks: bool = True) -> None:
        """Print a single task with formatting."""
        title = task.get("title", str(task))
        
        # Build metadata
        meta = []
        meta.append(f"priority:{task.get('priority', 0)}")
        meta.append(f"effort:{task.get('effort', 0)}")
        
        status_map = {0: 'not started', 1: 'in progress', 2: 'completed'}
        meta.append(f"status:{status_map.get(task.get('status', 0), 'unknown')}")
        
        if task.get('due_date'):
            meta.append(f"due:{task.get('due_date')}")
            
        # Format output
        pad = "  " * indent
        label = f"{prefix} {title}".strip()
        print(f"{pad}{label} [{', '.join(meta)}]")
        
        # Print subtasks if requested
        if show_subtasks:
            for idx, child in enumerate(task.get('subtasks', []), 1):
                self._print_task(child, prefix=f"{prefix}.{idx}" if prefix else f"{idx}", indent=indent+1)
                
    def get_task_stats(self) -> Dict[str, int]:
        """Get statistics about tasks."""
        stats = {
            "total": len(self.tasks),
            "not_started": 0,
            "in_progress": 0,
            "completed": 0,
            "has_subtasks": 0,
            "overdue": 0
        }
        
        today = date.today()
        
        for task in self.tasks:
            status = task.get("status", 0)
            if status == 0:
                stats["not_started"] += 1
            elif status == 1:
                stats["in_progress"] += 1
            elif status == 2:
                stats["completed"] += 1
                
            if task.get("has_subtasks", False):
                stats["has_subtasks"] += 1
                
            due_date = task.get("due_date")
            if due_date and status != 2:  # Not completed
                try:
                    due = datetime.fromisoformat(due_date).date()
                    if due < today:
                        stats["overdue"] += 1
                except Exception:
                    pass
                    
        return stats
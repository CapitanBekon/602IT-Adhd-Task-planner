"""NFC integration system for task management with enhanced logging and mapping."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)

class NFCManager:
    """Enhanced NFC manager with better mapping and event logging."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.mappings_file = self.data_dir / "nfc_mappings.json"
        self.pings_file = self.data_dir / "nfc_pings.json"
        
        # mappings: nfc_tag_id -> task_dict (same shape as tasks.json entries)
        self.mappings: Dict[str, Dict] = {}
        self.load_mappings()
        
    def load_mappings(self) -> None:
        """Load NFC mappings from JSON file."""
        try:
            if self.mappings_file.exists():
                with open(self.mappings_file, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                # Normalize mappings: allow older string-based mappings and convert
                norm = {}
                for tag_id, val in (raw or {}).items():
                    if isinstance(val, str):
                        # older format: task title only -> create minimal task dict
                        norm[tag_id] = {
                            "id": None,
                            "title": val,
                            "status": 0,
                            "priority": 0,
                            "effort": 0,
                            "due_date": None,
                            "created_at": datetime.now().isoformat(),
                            "updated_at": datetime.now().isoformat(),
                            "has_subtasks": False,
                            "subtasks": []
                        }
                    elif isinstance(val, dict):
                        # accept as-is but ensure title exists
                        task = val.copy()
                        if 'title' not in task:
                            task['title'] = task.get('task', 'Untitled')
                        norm[tag_id] = task
                    else:
                        # unknown format - skip
                        continue
                self.mappings = norm
                logger.info(f"Loaded {len(self.mappings)} NFC mappings (as task objects)")
            else:
                self.mappings = {}
                logger.info("No NFC mappings file found, starting empty")
        except Exception as e:
            logger.error(f"Failed to load NFC mappings: {e}")
            self.mappings = {}
            
    def save_mappings(self) -> None:
        """Save NFC mappings to JSON file."""
        try:
            with open(self.mappings_file, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.mappings)} NFC mappings (task objects)")
        except Exception as e:
            logger.error(f"Failed to save NFC mappings: {e}")
            
    def log_ping(self, tag_id: str, action: str, task_title: str = None,
                 task_index: int = None, new_status: int = None,
                 reader: str = "unknown", additional_data: Dict[str, Any] = None) -> None:
        """Log an NFC ping event with enhanced data."""
        try:
            ping_data = {
                "tag_id": tag_id,
                "action": action,
                "task_title": task_title,
                "task_index": task_index,
                "new_status": new_status,
                "reader": reader,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add any additional data
            if additional_data:
                ping_data.update(additional_data)
            
            # Load existing pings
            pings = []
            if self.pings_file.exists():
                try:
                    with open(self.pings_file, 'r', encoding='utf-8') as f:
                        pings = json.load(f)
                except Exception:
                    pings = []
                    
            # Add new ping
            pings.append(ping_data)
            
            # Keep only last 1000 pings to prevent file from growing too large
            if len(pings) > 1000:
                pings = pings[-1000:]
                
            # Save pings
            with open(self.pings_file, 'w', encoding='utf-8') as f:
                json.dump(pings, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Logged NFC ping: {tag_id} -> {action}")
            
        except Exception as e:
            logger.error(f"Failed to log NFC ping: {e}")
            
    def get_recent_pings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent NFC ping events."""
        try:
            if self.pings_file.exists():
                with open(self.pings_file, 'r', encoding='utf-8') as f:
                    pings = json.load(f)
                return pings[-limit:] if pings else []
        except Exception as e:
            logger.error(f"Failed to load ping history: {e}")
        return []
            
    def map_tag_to_task(self, tag_id: str, task_title: str) -> None:
        """Map an NFC tag to a task title."""
        old_mapping = self.mappings.get(tag_id)
        # Accept either a task title (str) or a full task dict
        if isinstance(task_title, str):
            task_obj = {
                "id": None,
                "title": task_title,
                "status": 0,
                "priority": 0,
                "effort": 0,
                "due_date": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "has_subtasks": False,
                "subtasks": []
            }
        elif isinstance(task_title, dict):
            task_obj = task_title.copy()
        else:
            logger.error(f"Unsupported task mapping type for tag {tag_id}: {type(task_title)}")
            return

        self.mappings[tag_id] = task_obj
        self.save_mappings()
        if old_mapping:
            logger.info(f"Remapped NFC tag {tag_id} from '{old_mapping.get('title') if isinstance(old_mapping, dict) else old_mapping}' to '{task_obj.get('title')}'")
        else:
            logger.info(f"Mapped NFC tag {tag_id} to task '{task_obj.get('title')}'")
        
    def get_task_for_tag(self, tag_id: str) -> Optional[Dict]:
        """Get the task object mapped to an NFC tag."""
        return self.mappings.get(tag_id)
        
    def remove_mapping(self, tag_id: str) -> bool:
        """Remove an NFC tag mapping."""
        if tag_id in self.mappings:
            task_obj = self.mappings.pop(tag_id)
            self.save_mappings()
            logger.info(f"Removed mapping for NFC tag {tag_id} (was: '{task_obj.get('title') if isinstance(task_obj, dict) else task_obj}')")
            return True
        return False
        
    def get_all_mappings(self) -> Dict[str, str]:
        """Get all NFC tag mappings."""
        # Return a shallow copy; values are task objects
        return {k: v.copy() if isinstance(v, dict) else v for k, v in self.mappings.items()}
        
    def get_tags_for_task(self, task_title: str) -> List[str]:
        """Get all NFC tags mapped to a specific task."""
        return [tag_id for tag_id, task in self.mappings.items()
                if isinstance(task, dict) and task.get('title', '').lower() == task_title.lower()]
                
    def bulk_import_mappings(self, mappings: Dict[str, str]) -> int:
        """Import multiple mappings at once. Returns count of imported mappings."""
        count = 0
        for tag_id, task_title in mappings.items():
            if tag_id and task_title:
                # accept either title string or full dict
                if isinstance(task_title, str):
                    task_obj = {
                        "id": None,
                        "title": task_title,
                        "status": 0,
                        "priority": 0,
                        "effort": 0,
                        "due_date": None,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "has_subtasks": False,
                        "subtasks": []
                    }
                elif isinstance(task_title, dict):
                    task_obj = task_title.copy()
                else:
                    continue
                self.mappings[tag_id] = task_obj
                count += 1
                
        if count > 0:
            self.save_mappings()
            logger.info(f"Bulk imported {count} NFC mappings")
            
        return count
        
    def export_mappings(self) -> Dict[str, str]:
        """Export all mappings for backup/transfer."""
        return self.get_all_mappings()
        
    def clear_all_mappings(self) -> int:
        """Clear all NFC mappings. Returns count of cleared mappings."""
        count = len(self.mappings)
        self.mappings.clear()
        self.save_mappings()
        logger.info(f"Cleared {count} NFC mappings")
        return count
        
    def get_mapping_stats(self) -> Dict[str, Any]:
        """Get statistics about NFC mappings and usage."""
        stats = {
            "total_mappings": len(self.mappings),
            "unique_tasks": len(set([v.get('title') if isinstance(v, dict) else v for v in self.mappings.values()])),
            "recent_pings": len(self.get_recent_pings(100))
        }
        
        # Analyze recent pings for popular tags
        recent_pings = self.get_recent_pings(100)
        tag_usage = {}
        for ping in recent_pings:
            tag_id = ping.get("tag_id")
            if tag_id:
                tag_usage[tag_id] = tag_usage.get(tag_id, 0) + 1
                
        if tag_usage:
            most_used_tag = max(tag_usage, key=tag_usage.get)
            stats["most_used_tag"] = {
                "tag_id": most_used_tag,
                "usage_count": tag_usage[most_used_tag],
                "mapped_task": (self.mappings.get(most_used_tag, {}).get('title') if isinstance(self.mappings.get(most_used_tag), dict) else self.mappings.get(most_used_tag, 'Unmapped'))
            }
        
        return stats
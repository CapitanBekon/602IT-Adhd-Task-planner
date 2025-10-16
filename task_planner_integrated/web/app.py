"""Flask web server for task management with NFC integration and hardware control."""

import logging
import os
from flask import Flask, request, jsonify, render_template, abort
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.task_manager import TaskManager
from core.nfc_manager import NFCManager

logger = logging.getLogger(__name__)

class TaskPlannerServer:
    """Flask server for comprehensive task management."""
    
    def __init__(self, data_dir: str = "data", hardware_manager=None):
        self.app = Flask(__name__, template_folder='../templates')
        self.task_manager = TaskManager(data_dir)
        self.nfc_manager = NFCManager(data_dir)
        self.hardware_manager = hardware_manager
        
        # Configuration
        self.auth_token = os.getenv("TASK_AUTH_TOKEN", "taskplanner2025")
        # Allow NFC endpoints to be public (no auth) if env var set to 1
        self.nfc_public = os.getenv("TASK_NFC_PUBLIC", "1") in ("1", "true", "True")
        
        # Setup routes
        self._setup_routes()
        
        logger.info("Task Planner Server initialized")
        
    def _check_auth(self) -> bool:
        """Check if request has valid authentication."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            return token == self.auth_token
        return False

        
    def _check_nfc_auth(self) -> bool:
        """Check auth for NFC endpoints; allow public access when configured."""
        if self.nfc_public:
            return True
        return self._check_auth()
        
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route("/")
        def index():
            """Serve the web interface."""
            return render_template('index.html')
            
        @self.app.route("/api/health", methods=["GET"])
        def health():
            """Health check endpoint."""
            stats = self.task_manager.get_task_stats()
            nfc_stats = self.nfc_manager.get_mapping_stats()
            
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "task_stats": stats,
                "nfc_stats": nfc_stats,
                "hardware_enabled": self.hardware_manager is not None
            })
            
        @self.app.route("/api/tasks", methods=["GET"])
        def get_tasks():
            """Get all tasks with optional filtering."""
            if not self._check_auth():
                abort(401)
                
            # Optional query parameters
            status = request.args.get('status', type=int)
            include_subtasks = request.args.get('include_subtasks', 'true').lower() == 'true'
            
            tasks = self.task_manager.get_all_tasks()
            
            # Filter by status if specified
            if status is not None:
                tasks = [t for t in tasks if t.get('status') == status]
                
            # Remove subtasks if not requested
            if not include_subtasks:
                for task in tasks:
                    task.pop('subtasks', None)
                    
            return jsonify({
                "tasks": tasks,
                "total_count": self.task_manager.get_task_count(),
                "filtered_count": len(tasks)
            })
            
        @self.app.route("/api/tasks", methods=["POST"])
        def create_task():
            """Create a new task."""
            if not self._check_auth():
                abort(401)
                
            data = request.get_json()
            if not data or not data.get("title"):
                return jsonify({"error": "Missing task title"}), 400
                
            task_index = self.task_manager.add_task(
                title=data["title"],
                priority=data.get("priority", 0),
                effort=data.get("effort", 0),
                due_date=data.get("due_date")
            )
            
            # Update hardware if available
            if self.hardware_manager:
                self.hardware_manager.update_task_led(task_index)
            
            return jsonify({
                "status": "created",
                "task_index": task_index,
                "title": data["title"]
            }), 201
            
        @self.app.route("/api/tasks/<int:task_id>", methods=["GET"])
        def get_task(task_id):
            """Get a specific task."""
            if not self._check_auth():
                abort(401)
                
            task = self.task_manager.get_task(task_id)
            if task:
                return jsonify({"task": task})
            else:
                return jsonify({"error": "Task not found"}), 404
                
        @self.app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
        def delete_task(task_id):
            """Delete a task."""
            if not self._check_auth():
                abort(401)
                
            if self.task_manager.remove_task(task_id):
                # Clean up hardware if available
                if self.hardware_manager:
                    self.hardware_manager.remove_group(task_id)
                return jsonify({"status": "deleted", "task_id": task_id})
            else:
                return jsonify({"error": "Task not found"}), 404
                
        @self.app.route("/api/tasks/<int:task_id>/status", methods=["PUT"])
        def update_task_status(task_id):
            """Update task status.

            Accepts either an empty body (cycle status) or JSON {"status": <0|1|2>}.
            Returns 404 if task missing.
            """
            if not self._check_auth():
                abort(401)

            # Allow empty body without causing a 400 from get_json
            data = request.get_json(silent=True) or {}
            # Only treat explicit status if key present; else cycle
            status = data.get("status") if "status" in data else None

            new_status = self.task_manager.update_task_status(task_id, status)
            if new_status is None:
                return jsonify({"error": "Task not found"}), 404

            # Update hardware if available
            if self.hardware_manager:
                try:
                    self.hardware_manager.update_task_led(task_id, new_status)
                except Exception as e:
                    logger.warning(f"Hardware LED update failed for task {task_id}: {e}")

            return jsonify({
                "status": "updated",
                "task_id": task_id,
                "new_status": new_status,
                "status_name": self.task_manager.get_status_name(new_status)
            })
                
        @self.app.route("/api/tasks/sort", methods=["POST"])
        def sort_tasks():
            """Sort tasks by specified criteria."""
            if not self._check_auth():
                abort(401)
                
            data = request.get_json()
            sort_by = data.get("sort_by", "priority") if data else "priority"
            
            try:
                self.task_manager.sort_tasks(sort_by)
                # Update all hardware after sorting
                if self.hardware_manager:
                    self.hardware_manager.update_all_leds()
                return jsonify({"status": "sorted", "sort_by": sort_by})
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
                
        @self.app.route("/api/tasks/stats", methods=["GET"])
        def get_task_stats():
            """Get task statistics."""
            if not self._check_auth():
                abort(401)
                
            stats = self.task_manager.get_task_stats()
            return jsonify({"stats": stats})
            
        # NFC endpoints
        @self.app.route("/api/nfc/mappings", methods=["GET"])
        def get_nfc_mappings():
            """Get all NFC mappings."""
            if not self._check_nfc_auth():
                abort(401)
                
            mappings = self.nfc_manager.get_all_mappings()
            return jsonify({"mappings": mappings})
            
        @self.app.route("/api/nfc/scan", methods=["POST"])
        def nfc_scan():
            """Handle NFC tag scan."""
            if not self._check_nfc_auth():
                abort(401)
                
            data = request.get_json()
            if not data or not data.get("tag_id"):
                return jsonify({"error": "Missing tag_id"}), 400
                
            tag_id = data["tag_id"]
            task_title = data.get("task_title")
            reader = data.get("reader", "api")
            
            # Check if tag is already mapped
            existing_task_obj = self.nfc_manager.get_task_for_tag(tag_id)
            existing_task = existing_task_obj.get('title') if isinstance(existing_task_obj, dict) else existing_task_obj
            
            if existing_task:
                # Tag is mapped, find and increment the task
                task_index = self.task_manager.find_task_by_title(existing_task)
                
                if task_index:
                    # Task exists, increment it
                    new_status = self.task_manager.update_task_status(task_index)
                    
                    # Update hardware
                    if self.hardware_manager:
                        self.hardware_manager.update_task_led(task_index, new_status)
                    
                    # Log the ping
                    self.nfc_manager.log_ping(
                        tag_id=tag_id,
                        action="task_incremented",
                        task_title=existing_task,
                        task_index=task_index,
                        new_status=new_status,
                        reader=reader
                    )
                    
                    return jsonify({
                        "status": "task_incremented",
                        "tag_id": tag_id,
                        "task_title": existing_task,
                        "task_index": task_index,
                        "new_status": new_status,
                        "status_name": self.task_manager.get_status_name(new_status)
                    })
                else:
                    # Mapped task no longer exists
                    if task_title:
                        # Create new task with provided title
                        task_index = self.task_manager.add_task(task_title)
                        self.nfc_manager.map_tag_to_task(tag_id, task_title)
                        
                        # Update hardware
                        if self.hardware_manager:
                            self.hardware_manager.update_task_led(task_index)
                        
                        self.nfc_manager.log_ping(
                            tag_id=tag_id,
                            action="task_created_remapped",
                            task_title=task_title,
                            task_index=task_index,
                            reader=reader
                        )
                        
                        return jsonify({
                            "status": "task_created_remapped",
                            "tag_id": tag_id,
                            "task_title": task_title,
                            "task_index": task_index,
                            "message": "Mapped task no longer exists, created new task"
                        }), 201
                    else:
                        return jsonify({
                            "error": "mapped_task_missing",
                            "message": "Tag was mapped to a task that no longer exists. Provide task_title to create new task."
                        }), 400
            else:
                # Tag not mapped yet
                if task_title:
                    # Check if task already exists
                    task_index = self.task_manager.find_task_by_title(task_title)
                    
                    if task_index:
                        # Task exists, map tag to it and increment
                        self.nfc_manager.map_tag_to_task(tag_id, task_title)
                        new_status = self.task_manager.update_task_status(task_index)
                        
                        # Update hardware
                        if self.hardware_manager:
                            self.hardware_manager.update_task_led(task_index, new_status)
                        
                        self.nfc_manager.log_ping(
                            tag_id=tag_id,
                            action="task_mapped_and_incremented",
                            task_title=task_title,
                            task_index=task_index,
                            new_status=new_status,
                            reader=reader
                        )
                        
                        return jsonify({
                            "status": "task_mapped_and_incremented",
                            "tag_id": tag_id,
                            "task_title": task_title,
                            "task_index": task_index,
                            "new_status": new_status,
                            "status_name": self.task_manager.get_status_name(new_status)
                        })
                    else:
                        # Task doesn't exist, create it and map tag
                        task_index = self.task_manager.add_task(task_title)
                        self.nfc_manager.map_tag_to_task(tag_id, task_title)
                        
                        # Update hardware
                        if self.hardware_manager:
                            self.hardware_manager.update_task_led(task_index)
                        
                        self.nfc_manager.log_ping(
                            tag_id=tag_id,
                            action="task_created_and_mapped",
                            task_title=task_title,
                            task_index=task_index,
                            reader=reader
                        )
                        
                        return jsonify({
                            "status": "task_created_and_mapped",
                            "tag_id": tag_id,
                            "task_title": task_title,
                            "task_index": task_index
                        }), 201
                else:
                    # Create an empty mapping so the tag is recorded for later mapping
                    self.nfc_manager.map_tag_to_task(tag_id, "")
                    self.nfc_manager.log_ping(
                        tag_id=tag_id,
                        action="mapping_created_empty",
                        task_title="",
                        reader=reader
                    )
                    return jsonify({
                        "status": "mapping_created_empty",
                        "tag_id": tag_id,
                        "message": "Tag recorded with empty mapping. Use mappings API to assign a task later."
                    }), 201

        @self.app.route("/api/nfc/scan/<path:identifier>", methods=["GET"])
        def nfc_scan_get(identifier):
            """Handle NFC tag scan via URL path (GET).

            Supports either a tag UID or a numeric task ID in the URL.
            Example: /api/nfc/scan/04:AA:BB:CC or /api/nfc/scan/3
            Optional query params: task_title, reader
            """
            if not self._check_nfc_auth():
                abort(401)

            # Pull optional params from querystring
            task_title = request.args.get('task_title')
            reader = request.args.get('reader', 'api')

            # If identifier is numeric, treat it as a direct task id
            if identifier.isdigit():
                task_id = int(identifier)
                # Try to update the task status
                new_status = self.task_manager.update_task_status(task_id)
                if new_status is None:
                    # If task not found and task_title provided, create it
                    if task_title:
                        task_index = self.task_manager.add_task(task_title)
                        # Map the numeric identifier (as string) to the created task
                        self.nfc_manager.map_tag_to_task(identifier, task_title)
                        if self.hardware_manager:
                            self.hardware_manager.update_task_led(task_index)
                        self.nfc_manager.log_ping(
                            tag_id=identifier,
                            action="task_created_and_mapped",
                            task_title=task_title,
                            task_index=task_index,
                            reader=reader
                        )
                        return jsonify({
                            "status": "task_created_and_mapped",
                            "tag_id": identifier,
                            "task_title": task_title,
                            "task_index": task_index
                        }), 201
                    return jsonify({"error": "Task not found"}), 404

                # Update hardware
                if self.hardware_manager:
                    try:
                        self.hardware_manager.update_task_led(task_id, new_status)
                    except Exception as e:
                        logger.warning(f"Hardware LED update failed for task {task_id}: {e}")

                # Log ping (use identifier as tag_id)
                self.nfc_manager.log_ping(
                    tag_id=identifier,
                    action="task_incremented",
                    task_index=task_id,
                    new_status=new_status,
                    reader=reader
                )

                return jsonify({
                    "status": "task_incremented",
                    "task_index": task_id,
                    "new_status": new_status,
                    "status_name": self.task_manager.get_status_name(new_status)
                })

            # Otherwise treat identifier as a tag UID
            tag_id = identifier
            existing_task_obj = self.nfc_manager.get_task_for_tag(tag_id)
            existing_task = existing_task_obj.get('title') if isinstance(existing_task_obj, dict) else existing_task_obj

            if existing_task:
                task_index = self.task_manager.find_task_by_title(existing_task)
                if task_index:
                    new_status = self.task_manager.update_task_status(task_index)
                    if self.hardware_manager:
                        self.hardware_manager.update_task_led(task_index, new_status)
                    self.nfc_manager.log_ping(
                        tag_id=tag_id,
                        action="task_incremented",
                        task_title=existing_task,
                        task_index=task_index,
                        new_status=new_status,
                        reader=reader
                    )
                    return jsonify({
                        "status": "task_incremented",
                        "tag_id": tag_id,
                        "task_title": existing_task,
                        "task_index": task_index,
                        "new_status": new_status,
                        "status_name": self.task_manager.get_status_name(new_status)
                    })
                else:
                    # Mapped task missing - try to create if title provided
                    if task_title:
                        task_index = self.task_manager.add_task(task_title)
                        self.nfc_manager.map_tag_to_task(tag_id, task_title)
                        if self.hardware_manager:
                            self.hardware_manager.update_task_led(task_index)
                        self.nfc_manager.log_ping(
                            tag_id=tag_id,
                            action="task_created_remapped",
                            task_title=task_title,
                            task_index=task_index,
                            reader=reader
                        )
                        return jsonify({
                            "status": "task_created_remapped",
                            "tag_id": tag_id,
                            "task_title": task_title,
                            "task_index": task_index
                        }), 201
                    return jsonify({
                        "error": "mapped_task_missing",
                        "message": "Tag is mapped but the task no longer exists. Provide task_title to recreate."
                    }), 400
            else:
                # Tag not mapped
                if task_title:
                    # Check if task exists by title
                    task_index = self.task_manager.find_task_by_title(task_title)
                    if task_index:
                        # Map and increment
                        self.nfc_manager.map_tag_to_task(tag_id, task_title)
                        new_status = self.task_manager.update_task_status(task_index)
                        if self.hardware_manager:
                            self.hardware_manager.update_task_led(task_index, new_status)
                        self.nfc_manager.log_ping(
                            tag_id=tag_id,
                            action="task_mapped_and_incremented",
                            task_title=task_title,
                            task_index=task_index,
                            new_status=new_status,
                            reader=reader
                        )
                        return jsonify({
                            "status": "task_mapped_and_incremented",
                            "tag_id": tag_id,
                            "task_title": task_title,
                            "task_index": task_index,
                            "new_status": new_status,
                            "status_name": self.task_manager.get_status_name(new_status)
                        })
                    else:
                        # Create and map
                        task_index = self.task_manager.add_task(task_title)
                        self.nfc_manager.map_tag_to_task(tag_id, task_title)
                        if self.hardware_manager:
                            self.hardware_manager.update_task_led(task_index)
                        self.nfc_manager.log_ping(
                            tag_id=tag_id,
                            action="task_created_and_mapped",
                            task_title=task_title,
                            task_index=task_index,
                            reader=reader
                        )
                        return jsonify({
                            "status": "task_created_and_mapped",
                            "tag_id": tag_id,
                            "task_title": task_title,
                            "task_index": task_index
                        }), 201
                else:
                    # Create an empty mapping for later assignment
                    self.nfc_manager.map_tag_to_task(tag_id, "")
                    self.nfc_manager.log_ping(
                        tag_id=tag_id,
                        action="mapping_created_empty",
                        task_title="",
                        reader=reader
                    )
                    return jsonify({
                        "status": "mapping_created_empty",
                        "tag_id": tag_id,
                        "message": "Tag recorded with empty mapping. Use mappings API to assign a task later."
                    }), 201

        @self.app.route("/api/nfc/scan/debug/<path:identifier>", methods=["GET"])
        def nfc_scan_debug(identifier):
            """Lightweight debug endpoint to verify path parsing and auth without side effects."""
            if not self._check_nfc_auth():
                abort(401)
            return jsonify({"identifier": identifier, "ok": True})
                    
        @self.app.route("/api/nfc/mappings", methods=["POST"])
        def create_nfc_mapping():
            """Create a new NFC mapping without incrementing."""
            if not self._check_nfc_auth():
                abort(401)
                
            data = request.get_json()
            if not data or not data.get("tag_id") or not data.get("task_title"):
                return jsonify({"error": "Missing tag_id or task_title"}), 400
                
            tag_id = data["tag_id"]
            task_title = data["task_title"]
            
            # Check if task exists, create if not
            task_index = self.task_manager.find_task_by_title(task_title)
            if not task_index:
                task_index = self.task_manager.add_task(task_title)
                
            # Create mapping
            self.nfc_manager.map_tag_to_task(tag_id, task_title)
            
            return jsonify({
                "status": "mapping_created",
                "tag_id": tag_id,
                "task_title": task_title,
                "task_index": task_index
            }), 201
            
        @self.app.route("/api/nfc/mappings/<tag_id>", methods=["DELETE"])
        def delete_nfc_mapping(tag_id):
            """Delete an NFC mapping."""
            if not self._check_nfc_auth():
                abort(401)
                
            if self.nfc_manager.remove_mapping(tag_id):
                return jsonify({"status": "mapping_deleted", "tag_id": tag_id})
            else:
                return jsonify({"error": "Mapping not found"}), 404
                
        @self.app.route("/api/nfc/pings", methods=["GET"])
        def get_nfc_pings():
            """Get recent NFC ping history."""
            if not self._check_nfc_auth():
                abort(401)
                
            limit = request.args.get('limit', 50, type=int)
            pings = self.nfc_manager.get_recent_pings(limit)
            return jsonify({"pings": pings, "count": len(pings)})
            
        @self.app.route("/api/nfc/stats", methods=["GET"])
        def get_nfc_stats():
            """Get NFC usage statistics."""
            if not self._check_nfc_auth():
                abort(401)
                
            stats = self.nfc_manager.get_mapping_stats()
            return jsonify({"stats": stats})
            
        # Hardware endpoints (if hardware manager is available)
        if self.hardware_manager:
            @self.app.route("/api/hardware/status", methods=["GET"])
            def get_hardware_status():
                """Get hardware status."""
                if not self._check_auth():
                    abort(401)
                    
                groups = self.hardware_manager.get_all_groups()
                return jsonify({"groups": groups})
                
            @self.app.route("/api/hardware/sync", methods=["POST"])
            def sync_hardware():
                """Sync all hardware with current task states."""
                if not self._check_auth():
                    abort(401)
                    
                self.hardware_manager.update_all_leds()
                return jsonify({"status": "synced"})
                
    def run(self, host="0.0.0.0", port=5002, debug=False):
        """Run the Flask server."""
        logger.info(f"Starting Task Planner Server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run server
    server = TaskPlannerServer()
    server.run(debug=True)
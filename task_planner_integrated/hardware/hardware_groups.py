"""Hardware groups for task-button-LED integration."""

import logging
from typing import Dict, Any, List, Optional, Callable
from .led_controller import LEDController, STATUS_TO_COLOR
from .button_controller import ButtonController

logger = logging.getLogger(__name__)

class HardwareGroup:
    """Represents a group of task, button, and LED working together."""
    
    def __init__(self, task_id: int, task_title: str = ""):
        self.task_id = task_id
        self.task_title = task_title
        self.status = 0
        self.leds = []  # List of LED configs
        self.buttons = []  # List of button configs
        
    def add_led(self, led_id: str, pins: Dict[str, int]):
        """Add an LED to this group."""
        self.leds.append({
            'led_id': led_id,
            'pins': pins
        })
        
    def add_button(self, button_id: str, pin: int):
        """Add a button to this group."""
        self.buttons.append({
            'button_id': button_id,
            'pin': pin
        })
        
    def get_info(self) -> Dict[str, Any]:
        """Get information about this group."""
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'status': self.status,
            'leds': self.leds,
            'buttons': self.buttons,
            'led_count': len(self.leds),
            'button_count': len(self.buttons)
        }

class HardwareManager:
    """Manages the integration between tasks, LEDs, and buttons."""
    
    def __init__(self, task_manager=None):
        self.task_manager = task_manager
        self.led_controller = LEDController()
        self.button_controller = ButtonController()
        self.groups = {}  # task_id -> HardwareGroup
        
    def register_task_group(self, task_id: int, button_pin: int, 
                           r_pin: int, g_pin: int, b_pin: int,
                           task_callback: Callable[[int], None] = None) -> bool:
        """Register a complete task group with button and LED."""
        try:
            # Get task info
            task = self.task_manager.get_task(task_id) if self.task_manager else None
            task_title = task.get('title', f'Task {task_id}') if task else f'Task {task_id}'
            
            # Create group
            group = HardwareGroup(task_id, task_title)
            
            # Setup LED
            led_id = f"task_{task_id}_led"
            pins = self.led_controller.setup_rgb_led(led_id, r_pin, g_pin, b_pin)
            if pins:
                group.add_led(led_id, pins)
                
            # Setup button with callback
            button_id = f"task_{task_id}_button"
            button_callback = lambda btn_id, pin: self._handle_task_button_press(task_id, btn_id, pin, task_callback)
            
            if self.button_controller.setup_button(button_id, button_pin, callback=button_callback):
                group.add_button(button_id, button_pin)
                
            # Store group
            self.groups[task_id] = group
            
            # Update LED to current task status
            self.update_task_led(task_id)
            
            logger.info(f"Registered task group for task {task_id}: button GPIO{button_pin}, LED R{r_pin}G{g_pin}B{b_pin}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register task group for task {task_id}: {e}")
            return False
            
    def register_additional_led(self, task_id: int, r_pin: int, g_pin: int, b_pin: int) -> bool:
        """Register an additional LED for an existing task (mirror LED)."""
        try:
            if task_id not in self.groups:
                # Create a minimal group for this task
                task = self.task_manager.get_task(task_id) if self.task_manager else None
                task_title = task.get('title', f'Task {task_id}') if task else f'Task {task_id}'
                self.groups[task_id] = HardwareGroup(task_id, task_title)
                
            group = self.groups[task_id]
            
            # Setup additional LED
            led_count = len(group.leds)
            led_id = f"task_{task_id}_led_{led_count + 1}"
            pins = self.led_controller.setup_rgb_led(led_id, r_pin, g_pin, b_pin)
            
            if pins:
                group.add_led(led_id, pins)
                self.update_task_led(task_id)  # Update all LEDs for this task
                logger.info(f"Added additional LED for task {task_id}: R{r_pin}G{g_pin}B{b_pin}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add additional LED for task {task_id}: {e}")
            
        return False
        
    def _handle_task_button_press(self, task_id: int, button_id: str, pin: int, 
                                 custom_callback: Callable[[int], None] = None) -> None:
        """Handle button press for a task."""
        try:
            logger.info(f"Task {task_id} button pressed (GPIO{pin})")
            
            # Update task status if task manager is available
            if self.task_manager:
                new_status = self.task_manager.increment_completion(task_id)
                if new_status is not None:
                    self.update_task_led(task_id, new_status)
                    logger.info(f"Task {task_id} status updated to {new_status}")
                    
            # Call custom callback if provided
            if custom_callback:
                custom_callback(task_id)
                
        except Exception as e:
            logger.error(f"Error handling button press for task {task_id}: {e}")
            
    def update_task_led(self, task_id: int, status: int = None) -> None:
        """Update LED(s) for a task based on its status."""
        try:
            if task_id not in self.groups:
                return
                
            group = self.groups[task_id]
            
            # Get status from task manager if not provided
            if status is None and self.task_manager:
                task = self.task_manager.get_task(task_id)
                status = task.get('status', 0) if task else 0
            elif status is None:
                status = 0
                
            # Update group status
            group.status = status
            
            # Get color for status
            color = STATUS_TO_COLOR.get(status, 'red')
            
            # Update all LEDs in the group
            for led_config in group.leds:
                led_id = led_config['led_id']
                self.led_controller.set_led_color(led_id, color)
                
            logger.debug(f"Updated LEDs for task {task_id} to {color} (status {status})")
            
        except Exception as e:
            logger.error(f"Error updating LED for task {task_id}: {e}")
            
    def update_all_leds(self) -> None:
        """Update all LEDs to match current task statuses."""
        for task_id in self.groups:
            self.update_task_led(task_id)
            
    def get_group_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific task group."""
        if task_id in self.groups:
            return self.groups[task_id].get_info()
        return None
        
    def get_all_groups(self) -> Dict[int, Dict[str, Any]]:
        """Get information about all task groups."""
        return {task_id: group.get_info() for task_id, group in self.groups.items()}
        
    def remove_group(self, task_id: int) -> bool:
        """Remove a task group and clean up its hardware."""
        if task_id not in self.groups:
            return False
            
        try:
            group = self.groups[task_id]
            
            # Turn off LEDs
            for led_config in group.leds:
                led_id = led_config['led_id']
                self.led_controller.led_off(led_id=led_id)
                
            # Remove buttons
            for button_config in group.buttons:
                button_id = button_config['button_id']
                self.button_controller.remove_button(button_id)
                
            # Remove from groups
            del self.groups[task_id]
            
            logger.info(f"Removed hardware group for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing group for task {task_id}: {e}")
            return False
            
    def cleanup(self) -> None:
        """Clean up all hardware resources."""
        try:
            # Turn off all LEDs
            for task_id in list(self.groups.keys()):
                self.remove_group(task_id)
                
            # Cleanup controllers
            self.led_controller.cleanup()
            self.button_controller.cleanup()
            
            logger.info("Hardware manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during hardware cleanup: {e}")
            
    def print_status(self) -> None:
        """Print status of all hardware groups."""
        if not self.groups:
            print("No hardware groups configured.")
            return
            
        print("\n=== HARDWARE STATUS ===")
        for task_id, group in self.groups.items():
            info = group.get_info()
            status_name = ["Not Started", "In Progress", "Completed"][info['status']]
            color = STATUS_TO_COLOR.get(info['status'], 'unknown')
            
            print(f"Task {task_id}: {info['task_title']}")
            print(f"  Status: {status_name} ({color})")
            print(f"  LEDs: {info['led_count']}, Buttons: {info['button_count']}")
            
            for led in info['leds']:
                pins = led['pins']
                print(f"    LED {led['led_id']}: R{pins['r']} G{pins['g']} B{pins['b']}")
                
            for button in info['buttons']:
                print(f"    Button {button['button_id']}: GPIO{button['pin']}")
                
        print()
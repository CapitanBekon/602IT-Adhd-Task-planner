"""Main task planner application with integrated hardware and NFC support."""

import logging
import sys
from pathlib import Path
from time import sleep
from typing import Optional, Dict, List, Tuple

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from core.task_manager import TaskManager
from core.nfc_manager import NFCManager
from hardware.hardware_groups import HardwareManager
from hardware.gpio_compat import GPIO, REAL_GPIO
from hardware.led_controller import STATUS_TO_COLOR

logger = logging.getLogger(__name__)

class TaskPlannerApp:
    """Main application class for the integrated task planner."""
    
    def __init__(self, data_dir: str = "data"):
        # Resolve relative data_dir to project-local 'data' folder so we always
        # read/write from the integrated project's data directory when a
        # relative path is provided.
        base = Path(__file__).resolve().parent
        if not Path(data_dir).is_absolute():
            self.data_dir = str((base / data_dir).resolve())
        else:
            self.data_dir = data_dir
        self.task_manager = TaskManager(self.data_dir)
        self.nfc_manager = NFCManager(self.data_dir)
        self.hardware_manager = HardwareManager(self.task_manager)
        
        # Configuration - Update these with your actual pin assignments
        self.LED_PIN_TRIPLETS: List[Tuple[int, int, int]] = [
            (17, 27, 22),  # LED 1 -> Task 1 (R, G, B)
            (23, 24, 25),  # LED 2 -> Task 2 (R, G, B)
        ]
        
        self.BUTTON_PINS: List[int] = [
            5,  # Button 1 -> Task 1
            6,  # Button 2 -> Task 2
        ]
        
        # Navigation state
        self.current_parent: Optional[int] = None
        
        logger.info(f"Task Planner App initialized (REAL_GPIO={REAL_GPIO})")
        
    def setup_hardware(self) -> None:
        """Setup hardware components (LEDs and buttons)."""
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
        except Exception as e:
            logger.warning(f"GPIO setup warning: {e}")
            
        # Register task groups (button + LED combinations)
        for idx in range(min(len(self.LED_PIN_TRIPLETS), len(self.BUTTON_PINS))):
            task_id = idx + 1
            button_pin = self.BUTTON_PINS[idx]
            r_pin, g_pin, b_pin = self.LED_PIN_TRIPLETS[idx]
            
            success = self.hardware_manager.register_task_group(
                task_id=task_id,
                button_pin=button_pin,
                r_pin=r_pin,
                g_pin=g_pin,
                b_pin=b_pin,
                task_callback=self._handle_task_interaction
            )
            
            if success:
                logger.info(f"Setup hardware for Task {task_id}: Button GPIO{button_pin}, LED R{r_pin}G{g_pin}B{b_pin}")
            else:
                logger.error(f"Failed to setup hardware for Task {task_id}")
                
        # Register additional mirror LEDs if we have more LED triplets than buttons
        for idx in range(len(self.BUTTON_PINS), len(self.LED_PIN_TRIPLETS)):
            task_id = idx + 1
            r_pin, g_pin, b_pin = self.LED_PIN_TRIPLETS[idx]
            
            success = self.hardware_manager.register_additional_led(
                task_id=task_id,
                r_pin=r_pin,
                g_pin=g_pin,
                b_pin=b_pin
            )
            
            if success:
                logger.info(f"Setup additional LED for Task {task_id}: R{r_pin}G{g_pin}B{b_pin}")
                
    def _handle_task_interaction(self, task_id: int) -> None:
        """Handle task interaction from button press or other sources."""
        try:
            if self.current_parent is None:
                # Root view: check if task has subtasks
                task = self.task_manager.get_task(task_id)
                if task and task.get('has_subtasks', False) and task.get('subtasks', []):
                    # Enter subtask view
                    self.current_parent = task_id
                    logger.info(f"Entered subtask view for Task {task_id}: {task.get('title', '')}")
                    self.sync_leds_for_view()
                else:
                    # Normal task increment - already handled by hardware manager
                    logger.info(f"Task {task_id} incremented")
            else:
                # Subtask view
                if task_id == 1:
                    # Back to root view
                    logger.info("Returning to root task view")
                    self.current_parent = None
                    self.sync_leds_for_view()
                else:
                    # Increment subtask
                    sub_idx = task_id - 1
                    parent_task = self.task_manager.get_task(self.current_parent)
                    if parent_task:
                        subtasks = parent_task.get('subtasks', [])
                        if 0 < sub_idx <= len(subtasks):
                            subtask = subtasks[sub_idx - 1]
                            current_status = subtask.get('status', 0)
                            new_status = (current_status + 1) % 3
                            subtask['status'] = new_status
                            self.task_manager.save_tasks()
                            logger.info(f"Subtask {sub_idx} of Task {self.current_parent} status -> {new_status}")
                            self.sync_leds_for_view()
                            
        except Exception as e:
            logger.error(f"Error handling task interaction for task {task_id}: {e}")
            
    def sync_leds_for_view(self) -> None:
        """Sync LEDs to match current view (root tasks or subtasks)."""
        try:
            if self.current_parent is None:
                # Root view: each LED shows its corresponding task status
                self.hardware_manager.update_all_leds()
            else:
                # Subtask view: LED 1 = back (yellow), others show subtask status
                parent_task = self.task_manager.get_task(self.current_parent)
                if parent_task:
                    subtasks = parent_task.get('subtasks', [])
                    
                    # LED 1: back indicator (yellow)
                    if 1 in self.hardware_manager.groups:
                        group = self.hardware_manager.groups[1]
                        for led_config in group.leds:
                            led_id = led_config['led_id']
                            self.hardware_manager.led_controller.set_led_color(led_id, 'yellow')
                            
                    # Subsequent LEDs: subtask statuses
                    for idx in range(2, len(self.LED_PIN_TRIPLETS) + 1):
                        sub_idx = idx - 1  # 1-based for subtasks
                        if idx in self.hardware_manager.groups:
                            group = self.hardware_manager.groups[idx]
                            
                            if 0 < sub_idx <= len(subtasks):
                                subtask = subtasks[sub_idx - 1]
                                status = subtask.get('status', 0)
                                color = STATUS_TO_COLOR.get(status, 'red')
                                
                                for led_config in group.leds:
                                    led_id = led_config['led_id']
                                    self.hardware_manager.led_controller.set_led_color(led_id, color)
                            else:
                                # No subtask: turn off
                                for led_config in group.leds:
                                    led_id = led_config['led_id']
                                    self.hardware_manager.led_controller.led_off(led_id=led_id)
                                    
        except Exception as e:
            logger.error(f"Error syncing LEDs for view: {e}")
            
    def run_console_interface(self) -> None:
        """Run the console-based interface."""
        print(f"\n🎯 Task Planner - Integrated Management System")
        print(f"Real GPIO: {REAL_GPIO}")
        print(f"Hardware Groups: {len(self.hardware_manager.groups)}")
        print(f"Tasks: {self.task_manager.get_task_count()}")
        print(f"NFC Mappings: {len(self.nfc_manager.get_all_mappings())}")
        
        try:
            while True:
                # Display current view
                if self.current_parent is None:
                    self.task_manager.view_tasks()
                    # Show hardware status
                    self.hardware_manager.print_status()
                else:
                    self.task_manager.view_subtasks(self.current_parent)
                    
                # Sync LEDs
                self.sync_leds_for_view()
                
                print("\n📋 Options:")
                print("1. Add Task")
                print("2. Remove Task")
                print("3. Sort Tasks")
                print("4. NFC Management")
                print("5. Hardware Status")
                print("6. Start Web Server")
                print("7. Exit")
                
                if self.current_parent is not None:
                    print("0. Back to main tasks")
                    
                choice = input("\nChoose an option: ").strip()
                
                if choice == "0" and self.current_parent is not None:
                    self.current_parent = None
                    print("Returned to main task view")
                    
                elif choice == "1":
                    self._add_task_interactive()
                    
                elif choice == "2":
                    self._remove_task_interactive()
                    
                elif choice == "3":
                    self._sort_tasks_interactive()
                    
                elif choice == "4":
                    self._nfc_management_menu()
                    
                elif choice == "5":
                    self._hardware_status_menu()
                    
                elif choice == "6":
                    self._start_web_server()
                    
                elif choice == "7":
                    print("Exiting Task Planner...")
                    break
                    
                else:
                    print("Invalid option. Please try again.")
                    
                sleep(0.2)
                
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
        finally:
            self.cleanup()
            
    def _add_task_interactive(self) -> None:
        """Interactive task addition."""
        title = input("Enter task title: ").strip()
        if not title:
            print("Task title cannot be empty.")
            return
            
        try:
            task_index = self.task_manager.add_task(title, interactive=True)
            if task_index == 0:
                # Task creation was cancelled by the user during subtask prompts
                print("Task creation cancelled.")
                return
            print(f"Task '{title}' added as Task {task_index}")

            # Update hardware
            try:
                self.hardware_manager.update_task_led(task_index)
            except Exception:
                # Non-fatal: continue even if hardware update fails
                logger.debug(f"Failed to update hardware for new task {task_index}")
            
        except Exception as e:
            print(f"Error adding task: {e}")
            
    def _remove_task_interactive(self) -> None:
        """Interactive task removal."""
        try:
            task_id = int(input("Enter task ID to remove: "))
            if self.task_manager.remove_task(task_id):
                self.hardware_manager.remove_group(task_id)
                print(f"Task {task_id} removed.")
            else:
                print("Invalid task ID.")
        except ValueError:
            print("Please enter a valid number.")
            
    def _sort_tasks_interactive(self) -> None:
        """Interactive task sorting."""
        print("\nSort options:")
        print("1. Priority")
        print("2. Due Date") 
        print("3. Status")
        print("4. Title")
        print("5. Effort")
        
        choice = input("Choose sorting option: ").strip()
        sort_map = {
            "1": "priority",
            "2": "due_date", 
            "3": "status",
            "4": "title",
            "5": "effort"
        }
        
        if choice in sort_map:
            try:
                self.task_manager.sort_tasks(sort_map[choice])
                self.hardware_manager.update_all_leds()
                print(f"Tasks sorted by {sort_map[choice]}")
            except Exception as e:
                print(f"Error sorting tasks: {e}")
        else:
            print("Invalid sorting option.")
            
    def _nfc_management_menu(self) -> None:
        """NFC management submenu."""
        while True:
            print("\n📱 NFC Management:")
            print("1. Show mappings")
            print("2. Add mapping")
            print("3. Remove mapping")
            print("4. Show recent pings")
            print("5. Clear all mappings")
            print("6. Back to main menu")
            
            choice = input("Choose option: ").strip()
            
            if choice == "1":
                mappings = self.nfc_manager.get_all_mappings()
                if mappings:
                    print("\nNFC Mappings:")
                    for tag_id, task_title in mappings.items():
                        print(f"  {tag_id} → {task_title}")
                else:
                    print("No NFC mappings found.")
                    
            elif choice == "2":
                tag_id = input("Enter NFC tag ID: ").strip()
                task_title = input("Enter task title: ").strip()
                if tag_id and task_title:
                    # Check if task exists, create if not
                    task_index = self.task_manager.find_task_by_title(task_title)
                    if not task_index:
                        task_index = self.task_manager.add_task(task_title)
                        print(f"Created new task: {task_title}")
                    self.nfc_manager.map_tag_to_task(tag_id, task_title)
                    print(f"Mapped {tag_id} to {task_title}")
                    
            elif choice == "3":
                tag_id = input("Enter NFC tag ID to remove: ").strip()
                if self.nfc_manager.remove_mapping(tag_id):
                    print(f"Mapping for {tag_id} removed.")
                else:
                    print("Mapping not found.")
                    
            elif choice == "4":
                pings = self.nfc_manager.get_recent_pings(10)
                if pings:
                    print("\nRecent NFC pings:")
                    for ping in pings[-10:]:
                        print(f"  {ping['timestamp']}: {ping['tag_id']} → {ping['action']}")
                else:
                    print("No recent pings found.")
                    
            elif choice == "5":
                confirm = input("Clear ALL NFC mappings? (yes/no): ").strip().lower()
                if confirm == "yes":
                    count = self.nfc_manager.clear_all_mappings()
                    print(f"Cleared {count} mappings.")
                    
            elif choice == "6":
                break
                
            else:
                print("Invalid option.")
                
    def _hardware_status_menu(self) -> None:
        """Hardware status and control menu."""
        while True:
            print("\n⚙️ Hardware Management:")
            print("1. Show hardware status")
            print("2. Test LED colors")
            print("3. Sync all LEDs")
            print("4. Test button (simulation)")
            print("5. Run hardware button test script")
            print("6. Back to main menu")
            
            choice = input("Choose option: ").strip()
            
            if choice == "1":
                self.hardware_manager.print_status()
                
            elif choice == "2":
                self._test_led_colors()
                
            elif choice == "3":
                self.hardware_manager.update_all_leds()
                print("All LEDs synced with task statuses.")
                
            elif choice == "4":
                self._test_button_simulation()
                
            elif choice == "5":
                # Run the hardware/button_test.py script with the current Python interpreter
                try:
                    import subprocess, sys
                    script_path = Path(__file__).resolve().parent / 'hardware' / 'button_test.py'
                    print(f"Running hardware test: {script_path}")
                    subprocess.run([sys.executable, str(script_path)], check=False)
                except Exception as e:
                    print(f"Failed to run hardware test: {e}")
                
            elif choice == "6":
                break
                
            else:
                print("Invalid option.")
                
    def _test_led_colors(self) -> None:
        """Test LED colors for all configured LEDs."""
        groups = self.hardware_manager.get_all_groups()
        if not groups:
            print("No hardware groups configured.")
            return
            
        colors = ['red', 'yellow', 'green', 'blue', 'purple', 'off']
        
        try:
            task_id = int(input("Enter task ID to test LEDs: "))
            if task_id not in groups:
                print(f"No hardware group found for task {task_id}")
                return
                
            print("Testing LED colors... (2 seconds each)")
            for color in colors:
                print(f"  {color}")
                self.hardware_manager.led_controller.set_led_color(f"task_{task_id}_led", color)
                sleep(2)
                
            # Restore original status
            self.hardware_manager.update_task_led(task_id)
            print("Test complete. LED restored to task status.")
            
        except ValueError:
            print("Please enter a valid task ID.")
        except Exception as e:
            print(f"Error testing LEDs: {e}")
            
    def _test_button_simulation(self) -> None:
        """Simulate button press for testing."""
        try:
            task_id = int(input("Enter task ID to simulate button press: "))
            if task_id in self.hardware_manager.groups:
                self._handle_task_interaction(task_id)
                print(f"Simulated button press for task {task_id}")
            else:
                print(f"No hardware group found for task {task_id}")
        except ValueError:
            print("Please enter a valid task ID.")
            
    def _start_web_server(self) -> None:
        """Start the web server."""
        try:
            from web.app import TaskPlannerServer
            print("\n🌐 Starting web server...")
            print("Access the web interface at: http://localhost:5002")
            print("Press Ctrl+C to stop the server and return to console")
            
            server = TaskPlannerServer(self.data_dir, self.hardware_manager)
            server.run(debug=False)
            
        except KeyboardInterrupt:
            print("\nWeb server stopped.")
        except ImportError:
            print("Flask not available. Install with: pip install flask")
        except Exception as e:
            print(f"Error starting web server: {e}")
            
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.hardware_manager.cleanup()
            print("Hardware cleanup completed.")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def led_hardware_test():
    """Test all LED pins directly (bypass app logic)."""
    import time
    from hardware.gpio_compat import GPIO, REAL_GPIO
    
    print(f"\n🔧 LED Hardware Test")
    print(f"Running on: {'REAL Raspberry Pi GPIO' if REAL_GPIO else 'MOCK GPIO (dev mode)'}")
    
    if not REAL_GPIO:
        print("⚠️  Not on a Raspberry Pi - hardware test skipped")
        return
    
    # Use the same pin lists as the app
    led_pins = [17, 27, 22, 23, 24, 25]
    
    print("\nInitializing GPIO...")
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        print("✓ GPIO mode set to BCM")
    except Exception as e:
        print(f"✗ GPIO setup error: {e}")
        return
    
    print("\nTesting each LED pin (1 second each):")
    for pin in led_pins:
        print(f"  GPIO{pin}: ", end='', flush=True)
        try:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
            print("setup OK, ", end='', flush=True)
            GPIO.output(pin, GPIO.LOW)
            print("ON", end='', flush=True)
            time.sleep(1)
            GPIO.output(pin, GPIO.HIGH)
            print(" → OFF")
            time.sleep(0.2)
        except Exception as e:
            print(f"ERROR: {e}")
    
    print("\n✓ Test complete")
    print("\nIf no LEDs lit up, check:")
    print("  1. LED wiring (common anode to 3.3V, R/G/B to GPIO pins)")
    print("  2. Current-limiting resistors (220Ω-330Ω per color)")
    print("  3. Pin numbers match your physical wiring")
    print("  4. GPIO permissions (try: sudo python main.py --ledtest)")
    
    GPIO.cleanup()

def main():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("🎯 Initializing Task Planner...")

    # Quick hardware test option
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--ledtest":
        led_hardware_test()
        return

    # Create and configure app
    app = TaskPlannerApp()

    # Setup hardware
    print("⚙️ Setting up hardware...")
    app.setup_hardware()

    # Run console interface
    app.run_console_interface()

if __name__ == "__main__":
    main()
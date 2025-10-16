"""Demo script to showcase the task planner functionality."""

import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.task_manager import TaskManager
from core.nfc_manager import NFCManager

def demo_task_management():
    """Demonstrate task management features."""
    print("🎯 Task Management Demo")
    print("=" * 50)
    
    # Create task manager
    task_manager = TaskManager("demo_data")
    
    # Add some demo tasks
    tasks_to_add = [
        ("Water the plants", 8, 2, "2025-10-15"),
        ("Complete project report", 10, 7, "2025-10-20"),
        ("Exercise for 30 minutes", 6, 3, None),
        ("Read chapter 5", 4, 4, "2025-10-18"),
        ("Grocery shopping", 7, 2, None)
    ]
    
    print("\n📝 Adding demo tasks...")
    for title, priority, effort, due_date in tasks_to_add:
        task_manager.add_task(title, priority, effort, due_date)
        print(f"   ✅ Added: {title}")
    
    # Display tasks
    print("\n📋 Current tasks:")
    task_manager.view_tasks()
    
    # Demonstrate status updates
    print("\n🔄 Updating task statuses...")
    task_manager.update_task_status(1)  # Water plants -> In Progress
    task_manager.update_task_status(3)  # Exercise -> In Progress
    task_manager.update_task_status(3)  # Exercise -> Completed
    
    print("   ✅ Updated task statuses")
    task_manager.view_tasks()
    
    # Show statistics
    print("\n📊 Task Statistics:")
    stats = task_manager.get_task_stats()
    for key, value in stats.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    # Demonstrate sorting
    print("\n🔀 Sorting by priority...")
    task_manager.sort_tasks("priority")
    task_manager.view_tasks()
    
    return task_manager

def demo_nfc_integration(task_manager):
    """Demonstrate NFC integration."""
    print("\n📱 NFC Integration Demo")
    print("=" * 50)
    
    nfc_manager = NFCManager("demo_data")
    
    # Create NFC mappings
    mappings = [
        ("nfc_plants", "Water the plants"),
        ("nfc_exercise", "Exercise for 30 minutes"),
        ("nfc_reading", "Read chapter 5")
    ]
    
    print("\n🏷️ Creating NFC mappings...")
    for tag_id, task_title in mappings:
        nfc_manager.map_tag_to_task(tag_id, task_title)
        print(f"   ✅ Mapped {tag_id} → {task_title}")
    
    # Simulate NFC interactions
    print("\n📲 Simulating NFC tag scans...")
    
    # Scan plant watering tag
    tag_id = "nfc_plants"
    mapped_task = nfc_manager.get_task_for_tag(tag_id)
    if mapped_task:
        task_index = task_manager.find_task_by_title(mapped_task)
        if task_index:
            old_status = task_manager.get_task(task_index)['status']
            new_status = task_manager.update_task_status(task_index)
            
            nfc_manager.log_ping(
                tag_id=tag_id,
                action="task_incremented",
                task_title=mapped_task,
                task_index=task_index,
                new_status=new_status,
                reader="demo"
            )
            
            print(f"   📱 Scanned {tag_id}: {mapped_task} ({old_status} → {new_status})")
    
    # Show NFC activity
    print("\n📜 Recent NFC activity:")
    pings = nfc_manager.get_recent_pings(5)
    for ping in pings:
        timestamp = ping['timestamp'][:19]  # Remove microseconds
        print(f"   {timestamp}: {ping['tag_id']} → {ping['action']}")
    
    # Show mappings
    print("\n🗺️ All NFC mappings:")
    mappings = nfc_manager.get_all_mappings()
    for tag_id, task_title in mappings.items():
        print(f"   {tag_id} → {task_title}")
    
    return nfc_manager

def demo_hardware_simulation():
    """Demonstrate hardware integration (simulated)."""
    print("\n⚙️ Hardware Integration Demo")
    print("=" * 50)
    
    print("\n🔗 Hardware would be configured as follows:")
    print("   Task 1: Button GPIO5, LED RGB(17,27,22)")
    print("   Task 2: Button GPIO6, LED RGB(23,24,25)")
    
    print("\n💡 LED Status Indicators:")
    print("   🔴 Red:    Not Started")
    print("   🟡 Yellow: In Progress")
    print("   🟢 Green:  Completed")
    
    print("\n🔘 Button Actions:")
    print("   • Single press: Increment task status")
    print("   • If task has subtasks: Enter subtask view")
    print("   • In subtask view: Button 1 = Back, others = subtask control")
    
    print("\n🖥️ Hardware integration is fully functional on Raspberry Pi")
    print("   with GPIO pins connected as specified in the configuration.")

def demo_web_interface():
    """Show information about the web interface."""
    print("\n🌐 Web Interface Demo")
    print("=" * 50)
    
    print("\n🚀 To start the web server:")
    print("   python web/app.py")
    print("   or run it from the main console interface (option 6)")
    
    print("\n🌍 Web interface features:")
    print("   • Modern responsive design")
    print("   • Real-time task management")
    print("   • NFC tag scanning")
    print("   • Task statistics dashboard")
    print("   • Hardware status monitoring")
    print("   • Mobile-friendly interface")
    
    print("\n🔗 Access at: http://localhost:5002")
    print("   API docs available at endpoints under /api/")

def main():
    """Run the complete demo."""
    print("🎯 Task Planner - Complete Functionality Demo")
    print("=" * 60)
    print("This demo showcases all features of the integrated task management system")
    print()
    
    try:
        # Demo core task management
        task_manager = demo_task_management()
        
        # Wait for user
        input("\nPress Enter to continue to NFC demo...")
        
        # Demo NFC integration
        nfc_manager = demo_nfc_integration(task_manager)
        
        # Wait for user
        input("\nPress Enter to continue to hardware demo...")
        
        # Demo hardware concepts
        demo_hardware_simulation()
        
        # Wait for user
        input("\nPress Enter to see web interface info...")
        
        # Show web interface info
        demo_web_interface()
        
        print("\n✨ Demo completed!")
        print("\nNext steps:")
        print("1. Run 'python main.py' for the full console interface")
        print("2. Run 'python web/app.py' for the web interface")
        print("3. Connect hardware on Raspberry Pi for full functionality")
        print("4. Configure NFC readers for automatic tag detection")
        
        # Cleanup option
        cleanup = input("\n🧹 Remove demo data? (y/n): ").strip().lower()
        if cleanup.startswith('y'):
            import shutil
            import os
            demo_dir = Path("demo_data")
            if demo_dir.exists():
                shutil.rmtree(demo_dir)
                print("✅ Demo data cleaned up")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")

if __name__ == "__main__":
    main()
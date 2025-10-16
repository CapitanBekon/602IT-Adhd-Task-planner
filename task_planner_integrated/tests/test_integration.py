"""Test the integrated task planner functionality."""

import sys
from pathlib import Path
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.task_manager import TaskManager
from core.nfc_manager import NFCManager
from hardware.hardware_groups import HardwareManager

class TestTaskManager(unittest.TestCase):
    """Test the core task management functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.task_manager = TaskManager(self.temp_dir)
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    def test_add_task(self):
        """Test adding a basic task."""
        task_index = self.task_manager.add_task("Test Task", priority=5, effort=3)
        self.assertEqual(task_index, 1)
        self.assertEqual(self.task_manager.get_task_count(), 1)
        
        task = self.task_manager.get_task(1)
        self.assertIsNotNone(task)
        self.assertEqual(task['title'], "Test Task")
        self.assertEqual(task['priority'], 5)
        self.assertEqual(task['effort'], 3)
        self.assertEqual(task['status'], 0)
        
    def test_update_task_status(self):
        """Test updating task status."""
        task_index = self.task_manager.add_task("Test Task")
        
        # Test cycling through statuses
        new_status = self.task_manager.update_task_status(task_index)
        self.assertEqual(new_status, 1)  # Not started -> In progress
        
        new_status = self.task_manager.update_task_status(task_index)
        self.assertEqual(new_status, 2)  # In progress -> Completed
        
        new_status = self.task_manager.update_task_status(task_index)
        self.assertEqual(new_status, 0)  # Completed -> Not started
        
    def test_find_task_by_title(self):
        """Test finding tasks by title."""
        self.task_manager.add_task("First Task")
        self.task_manager.add_task("Second Task")
        
        index = self.task_manager.find_task_by_title("First Task")
        self.assertEqual(index, 1)
        
        index = self.task_manager.find_task_by_title("second task")  # Case insensitive
        self.assertEqual(index, 2)
        
        index = self.task_manager.find_task_by_title("Nonexistent Task")
        self.assertIsNone(index)
        
    def test_remove_task(self):
        """Test removing tasks."""
        self.task_manager.add_task("Task 1")
        self.task_manager.add_task("Task 2")
        self.task_manager.add_task("Task 3")
        
        self.assertEqual(self.task_manager.get_task_count(), 3)
        
        # Remove middle task
        success = self.task_manager.remove_task(2)
        self.assertTrue(success)
        self.assertEqual(self.task_manager.get_task_count(), 2)
        
        # Check that IDs are updated
        task1 = self.task_manager.get_task(1)
        task2 = self.task_manager.get_task(2)
        self.assertEqual(task1['title'], "Task 1")
        self.assertEqual(task2['title'], "Task 3")  # Task 3 moved to position 2
        
    def test_sort_tasks(self):
        """Test task sorting."""
        self.task_manager.add_task("Low Priority", priority=1)
        self.task_manager.add_task("High Priority", priority=10)
        self.task_manager.add_task("Medium Priority", priority=5)
        
        self.task_manager.sort_tasks("priority")
        
        # Check order (high to low priority)
        tasks = self.task_manager.get_all_tasks()
        self.assertEqual(tasks[0]['title'], "High Priority")
        self.assertEqual(tasks[1]['title'], "Medium Priority")
        self.assertEqual(tasks[2]['title'], "Low Priority")

class TestNFCManager(unittest.TestCase):
    """Test the NFC management functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.nfc_manager = NFCManager(self.temp_dir)
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    def test_map_tag_to_task(self):
        """Test mapping NFC tags to tasks."""
        self.nfc_manager.map_tag_to_task("tag1", "Test Task")
        
        mapped_task = self.nfc_manager.get_task_for_tag("tag1")
        self.assertEqual(mapped_task, "Test Task")
        
        # Test unmapped tag
        unmapped = self.nfc_manager.get_task_for_tag("nonexistent")
        self.assertIsNone(unmapped)
        
    def test_remove_mapping(self):
        """Test removing NFC mappings."""
        self.nfc_manager.map_tag_to_task("tag1", "Test Task")
        
        success = self.nfc_manager.remove_mapping("tag1")
        self.assertTrue(success)
        
        mapped_task = self.nfc_manager.get_task_for_tag("tag1")
        self.assertIsNone(mapped_task)
        
        # Test removing nonexistent mapping
        success = self.nfc_manager.remove_mapping("nonexistent")
        self.assertFalse(success)
        
    def test_get_tags_for_task(self):
        """Test finding all tags mapped to a specific task."""
        self.nfc_manager.map_tag_to_task("tag1", "Test Task")
        self.nfc_manager.map_tag_to_task("tag2", "Test Task")
        self.nfc_manager.map_tag_to_task("tag3", "Other Task")
        
        tags = self.nfc_manager.get_tags_for_task("Test Task")
        self.assertEqual(set(tags), {"tag1", "tag2"})
        
        tags = self.nfc_manager.get_tags_for_task("Other Task")
        self.assertEqual(tags, ["tag3"])
        
    def test_log_ping(self):
        """Test NFC ping logging."""
        self.nfc_manager.log_ping(
            tag_id="tag1",
            action="task_incremented",
            task_title="Test Task",
            task_index=1,
            new_status=1,
            reader="test_reader"
        )
        
        pings = self.nfc_manager.get_recent_pings(10)
        self.assertEqual(len(pings), 1)
        
        ping = pings[0]
        self.assertEqual(ping['tag_id'], "tag1")
        self.assertEqual(ping['action'], "task_incremented")
        self.assertEqual(ping['task_title'], "Test Task")

class TestHardwareManager(unittest.TestCase):
    """Test the hardware management functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.task_manager = TaskManager(self.temp_dir)
        self.hardware_manager = HardwareManager(self.task_manager)
        
        # Add some test tasks
        self.task_manager.add_task("Task 1")
        self.task_manager.add_task("Task 2")
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        self.hardware_manager.cleanup()
        
    @patch('hardware.hardware_groups.GPIO')
    def test_register_task_group(self, mock_gpio):
        """Test registering a task group with LED and button."""
        success = self.hardware_manager.register_task_group(
            task_id=1,
            button_pin=5,
            r_pin=17,
            g_pin=27,
            b_pin=22
        )
        
        self.assertTrue(success)
        self.assertIn(1, self.hardware_manager.groups)
        
        group_info = self.hardware_manager.get_group_info(1)
        self.assertIsNotNone(group_info)
        self.assertEqual(group_info['task_id'], 1)
        self.assertEqual(group_info['led_count'], 1)
        self.assertEqual(group_info['button_count'], 1)
        
    @patch('hardware.hardware_groups.GPIO')
    def test_register_additional_led(self, mock_gpio):
        """Test registering additional LEDs for a task."""
        # First register a basic group
        self.hardware_manager.register_task_group(
            task_id=1,
            button_pin=5,
            r_pin=17,
            g_pin=27,
            b_pin=22
        )
        
        # Add additional LED
        success = self.hardware_manager.register_additional_led(
            task_id=1,
            r_pin=23,
            g_pin=24,
            b_pin=25
        )
        
        self.assertTrue(success)
        
        group_info = self.hardware_manager.get_group_info(1)
        self.assertEqual(group_info['led_count'], 2)  # Original + additional
        
    def test_get_all_groups(self):
        """Test getting information about all groups."""
        with patch('hardware.hardware_groups.GPIO'):
            self.hardware_manager.register_task_group(
                task_id=1, button_pin=5, r_pin=17, g_pin=27, b_pin=22
            )
            self.hardware_manager.register_task_group(
                task_id=2, button_pin=6, r_pin=23, g_pin=24, b_pin=25
            )
        
        groups = self.hardware_manager.get_all_groups()
        self.assertEqual(len(groups), 2)
        self.assertIn(1, groups)
        self.assertIn(2, groups)

class TestIntegration(unittest.TestCase):
    """Test integration between components."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.task_manager = TaskManager(self.temp_dir)
        self.nfc_manager = NFCManager(self.temp_dir)
        self.hardware_manager = HardwareManager(self.task_manager)
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        self.hardware_manager.cleanup()
        
    def test_nfc_task_workflow(self):
        """Test complete NFC workflow with task management."""
        # Create a task
        task_index = self.task_manager.add_task("Water Plants")
        
        # Map NFC tag to task
        self.nfc_manager.map_tag_to_task("nfc_001", "Water Plants")
        
        # Simulate NFC scan (would increment task)
        mapped_task = self.nfc_manager.get_task_for_tag("nfc_001")
        self.assertEqual(mapped_task, "Water Plants")
        
        found_index = self.task_manager.find_task_by_title(mapped_task)
        self.assertEqual(found_index, task_index)
        
        # Increment task status
        new_status = self.task_manager.update_task_status(found_index)
        self.assertEqual(new_status, 1)  # Should be "In Progress"
        
        # Log the interaction
        self.nfc_manager.log_ping(
            tag_id="nfc_001",
            action="task_incremented",
            task_title=mapped_task,
            task_index=found_index,
            new_status=new_status
        )
        
        # Verify logging
        pings = self.nfc_manager.get_recent_pings(1)
        self.assertEqual(len(pings), 1)
        self.assertEqual(pings[0]['action'], "task_incremented")

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
"""Simple script to test NFC API functionality."""

import requests
import json
import sys
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:5002/api"
AUTH_TOKEN = "taskplanner2025"
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def test_server_health():
    """Test if server is responding."""
    try:
        response = requests.get(f"{BASE_URL}/health", headers=HEADERS, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Server is healthy!")
            print(f"   Task count: {data['task_stats']['total']}")
            print(f"   NFC mappings: {data['nfc_stats']['total_mappings']}")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running:")
        print("   python web/app.py")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

def test_task_operations():
    """Test basic task operations."""
    print("\n📋 Testing task operations...")
    
    # Create a test task
    task_data = {
        "title": "Test Task from API",
        "priority": 7,
        "effort": 3,
        "due_date": "2025-12-31"
    }
    
    response = requests.post(f"{BASE_URL}/tasks", headers=HEADERS, json=task_data)
    if response.status_code == 201:
        result = response.json()
        task_id = result['task_index']
        print(f"✅ Created task {task_id}: {result['title']}")
        
        # Update task status
        response = requests.put(f"{BASE_URL}/tasks/{task_id}/status", headers=HEADERS)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Updated task status to: {result['status_name']}")
        else:
            print(f"❌ Failed to update task status: {response.status_code}")
            
        return task_id
    else:
        print(f"❌ Failed to create task: {response.status_code}")
        return None

def test_nfc_operations():
    """Test NFC operations."""
    print("\n📱 Testing NFC operations...")
    
    # Test NFC tag with new task
    nfc_data = {
        "tag_id": "test_tag_001",
        "task_title": "NFC Test Task",
        "reader": "api_test"
    }
    
    response = requests.post(f"{BASE_URL}/nfc/scan", headers=HEADERS, json=nfc_data)
    if response.status_code == 201:
        result = response.json()
        print(f"✅ NFC scan created task: {result['status']}")
        
        # Scan same tag again to increment
        nfc_data2 = {
            "tag_id": "test_tag_001",
            "reader": "api_test"
        }
        
        response = requests.post(f"{BASE_URL}/nfc/scan", headers=HEADERS, json=nfc_data2)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ NFC increment: {result['status_name']}")
        else:
            print(f"❌ Failed to increment via NFC: {response.status_code}")
            
    else:
        print(f"❌ Failed NFC scan: {response.status_code}")

def test_nfc_mappings():
    """Test NFC mapping management."""
    print("\n🏷️ Testing NFC mappings...")
    
    # Get all mappings
    response = requests.get(f"{BASE_URL}/nfc/mappings", headers=HEADERS)
    if response.status_code == 200:
        mappings = response.json()['mappings']
        print(f"✅ Retrieved {len(mappings)} NFC mappings")
        
        for tag_id, task_title in mappings.items():
            print(f"   {tag_id} → {task_title}")
    else:
        print(f"❌ Failed to get NFC mappings: {response.status_code}")

def cleanup_test_data():
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")
    
    # Get all tasks and remove test ones
    response = requests.get(f"{BASE_URL}/tasks", headers=HEADERS)
    if response.status_code == 200:
        tasks = response.json()['tasks']
        for task in tasks:
            if 'Test' in task['title'] or 'API' in task['title']:
                response = requests.delete(f"{BASE_URL}/tasks/{task['id']}", headers=HEADERS)
                if response.status_code == 200:
                    print(f"✅ Deleted test task: {task['title']}")
                    
    # Remove test NFC mappings
    response = requests.get(f"{BASE_URL}/nfc/mappings", headers=HEADERS)
    if response.status_code == 200:
        mappings = response.json()['mappings']
        for tag_id, task_title in mappings.items():
            if 'test' in tag_id.lower() or 'Test' in task_title:
                response = requests.delete(f"{BASE_URL}/nfc/mappings/{tag_id}", headers=HEADERS)
                if response.status_code == 200:
                    print(f"✅ Deleted test mapping: {tag_id}")

def main():
    """Run all tests."""
    print("🧪 Task Planner API Test Suite\n")
    
    # Test server connectivity
    if not test_server_health():
        sys.exit(1)
    
    # Run tests
    test_task_operations()
    test_nfc_operations()
    test_nfc_mappings()
    
    # Ask if user wants to cleanup
    response = input("\n🧹 Clean up test data? (y/n): ").strip().lower()
    if response.startswith('y'):
        cleanup_test_data()
    
    print("\n✅ All tests completed!")
    print("\nYou can also test the web interface at: http://localhost:5002")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
NFC Tag Scan Simulator

Simulates NFC tag scans by sending HTTP requests to the Task Planner server.
Useful for testing NFC integration without physical NFC tags.
"""

import requests
import json
import sys
import time
from datetime import datetime

# Configuration
SERVER_URL = "http://localhost:5002"
AUTH_TOKEN = "taskplanner2025"

class NFCSimulator:
    def __init__(self, server_url=SERVER_URL, auth_token=AUTH_TOKEN):
        self.server_url = server_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
    def scan_tag(self, tag_id, task_title=None, reader="simulator"):
        """Simulate an NFC tag scan."""
        endpoint = f"{self.server_url}/api/nfc/scan"
        
        payload = {
            "tag_id": tag_id,
            "reader": reader
        }
        
        if task_title:
            payload["task_title"] = task_title
            
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            return response.status_code, response.json()
        except requests.exceptions.ConnectionError:
            return None, {"error": "Cannot connect to server. Is it running?"}
        except Exception as e:
            return None, {"error": str(e)}
            
    def get_mappings(self):
        """Get all NFC mappings."""
        endpoint = f"{self.server_url}/api/nfc/mappings"
        try:
            response = requests.get(endpoint, headers=self.headers)
            return response.status_code, response.json()
        except Exception as e:
            return None, {"error": str(e)}
            
    def get_pings(self, limit=10):
        """Get recent NFC pings."""
        endpoint = f"{self.server_url}/api/nfc/pings?limit={limit}"
        try:
            response = requests.get(endpoint, headers=self.headers)
            return response.status_code, response.json()
        except Exception as e:
            return None, {"error": str(e)}
            
    def create_mapping(self, tag_id, task_title):
        """Create an NFC mapping without scanning."""
        endpoint = f"{self.server_url}/api/nfc/mappings"
        payload = {
            "tag_id": tag_id,
            "task_title": task_title
        }
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            return response.status_code, response.json()
        except Exception as e:
            return None, {"error": str(e)}
            
    def get_tasks(self):
        """Get all tasks."""
        endpoint = f"{self.server_url}/api/tasks"
        try:
            response = requests.get(endpoint, headers=self.headers)
            return response.status_code, response.json()
        except Exception as e:
            return None, {"error": str(e)}

def print_response(status_code, data):
    """Pretty print API response."""
    if status_code is None:
        print(f"❌ Error: {data.get('error', 'Unknown error')}")
        return
        
    status_icon = "✅" if 200 <= status_code < 300 else "❌"
    print(f"\n{status_icon} Status: {status_code}")
    print(json.dumps(data, indent=2))

def main():
    """Main interactive demo."""
    simulator = NFCSimulator()
    
    print("=" * 70)
    print("NFC TAG SCAN SIMULATOR")
    print("=" * 70)
    print(f"\nServer: {SERVER_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if server is running
    try:
        response = requests.get(f"{SERVER_URL}/api/health", timeout=2)
        health = response.json()
        print(f"\n✅ Server is running")
        print(f"   Tasks: {health.get('task_stats', {}).get('total_tasks', 0)}")
        print(f"   NFC Mappings: {health.get('nfc_stats', {}).get('total_mappings', 0)}")
    except:
        print("\n❌ Server is not running!")
        print("   Start it with: python main.py (then choose option 6)")
        sys.exit(1)
    
    while True:
        print("\n" + "=" * 70)
        print("OPTIONS:")
        print("=" * 70)
        print("1. Simulate NFC Tag Scan (with task title)")
        print("2. Simulate NFC Tag Scan (without task title)")
        print("3. Create NFC Mapping (without scanning)")
        print("4. View All NFC Mappings")
        print("5. View Recent NFC Pings")
        print("6. View All Tasks")
        print("7. Quick Demo (scan 3 tags)")
        print("8. Exit")
        
        choice = input("\nEnter choice (1-8): ").strip()
        
        if choice == "1":
            tag_id = input("Enter NFC tag ID (e.g., 04:52:A3:B2:5E:6F:80): ").strip()
            task_title = input("Enter task title: ").strip()
            
            if tag_id and task_title:
                print(f"\n📱 Scanning tag: {tag_id}")
                print(f"   Task: {task_title}")
                status, data = simulator.scan_tag(tag_id, task_title)
                print_response(status, data)
            else:
                print("❌ Tag ID and task title are required")
                
        elif choice == "2":
            tag_id = input("Enter NFC tag ID: ").strip()
            
            if tag_id:
                print(f"\n📱 Scanning tag: {tag_id}")
                status, data = simulator.scan_tag(tag_id)
                print_response(status, data)
            else:
                print("❌ Tag ID is required")
                
        elif choice == "3":
            tag_id = input("Enter NFC tag ID: ").strip()
            task_title = input("Enter task title: ").strip()
            
            if tag_id and task_title:
                print(f"\n🔗 Creating mapping...")
                status, data = simulator.create_mapping(tag_id, task_title)
                print_response(status, data)
            else:
                print("❌ Both tag ID and task title are required")
                
        elif choice == "4":
            print("\n📋 Fetching NFC mappings...")
            status, data = simulator.get_mappings()
            print_response(status, data)
            
        elif choice == "5":
            limit = input("How many recent pings? (default: 10): ").strip()
            limit = int(limit) if limit.isdigit() else 10
            
            print(f"\n📜 Fetching last {limit} pings...")
            status, data = simulator.get_pings(limit)
            print_response(status, data)
            
        elif choice == "6":
            print("\n📝 Fetching all tasks...")
            status, data = simulator.get_tasks()
            print_response(status, data)
            
        elif choice == "7":
            print("\n🎬 Running Quick Demo...")
            print("\nThis will simulate scanning 3 different NFC tags")
            
            demo_tags = [
                ("04:AA:BB:CC:DD:EE:01", "Water Plants"),
                ("04:AA:BB:CC:DD:EE:02", "Check Mail"),
                ("04:AA:BB:CC:DD:EE:03", "Take Medication")
            ]
            
            for tag_id, task_title in demo_tags:
                print(f"\n{'─' * 70}")
                print(f"📱 Scanning: {task_title} ({tag_id})")
                status, data = simulator.scan_tag(tag_id, task_title)
                print_response(status, data)
                time.sleep(1)
            
            print(f"\n{'─' * 70}")
            print("✅ Demo complete!")
            print("\nNow let's scan the first tag again to increment it...")
            time.sleep(2)
            
            tag_id, task_title = demo_tags[0]
            print(f"\n📱 Scanning again: {task_title}")
            status, data = simulator.scan_tag(tag_id, task_title)
            print_response(status, data)
            
            print("\n💡 Notice how the status changed from 0 → 1")
            
        elif choice == "8":
            print("\n👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please enter 1-8.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

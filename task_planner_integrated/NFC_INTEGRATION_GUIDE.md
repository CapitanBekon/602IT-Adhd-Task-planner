# NFC Integration Guide

## Overview

This guide explains how to integrate NFC tags with the Task Planner system using NFC Tools or similar apps.

## System Architecture

```
NFC Tag → NFC Tools App → HTTP POST → Task Planner Server → Update Task → Update LED
```

## How It Works

1. **Tag Mapping**: Each NFC tag is mapped to a task (stored in `data/nfc_mappings.json`)
2. **Tag Scan**: When an NFC tag is scanned, it triggers an HTTP POST to the server
3. **Task Action**: The server finds the mapped task and increments its status
4. **Auto-Creation**: If the task doesn't exist, it's automatically created as "Not Started"
5. **LED Update**: The corresponding LED updates to reflect the new status

## API Endpoint

### `/api/nfc/scan` - Handle NFC Tag Scan

**Method**: `POST`  
**Content-Type**: `application/json`  
**Authorization**: `Bearer taskplanner2025`

#### Request Body

```json
{
  "tag_id": "04:52:A3:B2:5E:6F:80",
  "task_title": "Water Plants"
}
```

**Fields:**
- `tag_id` (required): The unique identifier of the NFC tag
- `task_title` (optional but recommended): The title of the task to associate with this tag
- `reader` (optional): Name of the reader device (default: "api")

#### Behavior

| Scenario | Action | Response |
|----------|--------|----------|
| **Tag mapped + Task exists** | Increment task status | `task_incremented` |
| **Tag mapped + Task missing** | Create task with provided title | `task_created_remapped` |
| **Tag unmapped + Title provided** | Create/find task, map tag, increment | `task_created_and_mapped` |
| **Tag unmapped + No title** | Return error | `unmapped_tag` |

#### Response Examples

**Success - Task Incremented:**
```json
{
  "status": "task_incremented",
  "tag_id": "04:52:A3:B2:5E:6F:80",
  "task_title": "Water Plants",
  "task_index": 1,
  "new_status": 1,
  "status_name": "In Progress"
}
```

**Success - Task Created:**
```json
{
  "status": "task_created_and_mapped",
  "tag_id": "04:52:A3:B2:5E:6F:80",
  "task_title": "Water Plants",
  "task_index": 3
}
```

**Error - Unmapped Tag:**
```json
{
  "error": "unmapped_tag",
  "message": "Tag not mapped to any task. Provide task_title to create or map to existing task."
}
```

## Setting Up NFC Tags with NFC Tools

### Option 1: Using NFC Tools App (Android/iOS)

1. **Install NFC Tools** from Play Store or App Store

2. **Write a Record to the Tag:**
   - Open NFC Tools
   - Go to "Write" tab
   - Add a record → "Custom URL / URI"
   - Enter your server URL with parameters

3. **URL Format:**

   For Android (using Tasker or HTTP Request Shortcuts):
   ```
   http://YOUR_SERVER_IP:5002/api/nfc/scan
   ```

   For iOS (using Shortcuts app):
   ```
   http://YOUR_SERVER_IP:5002/api/nfc/scan
   ```

### Option 2: NFC Tools Pro with Tasks

1. **Install NFC Tools Pro** (paid app with automation)

2. **Create a Task:**
   - Open NFC Tools Pro
   - Go to "Tasks" tab
   - Create new task
   - Add action: "Send HTTP request"
   
3. **Configure HTTP Request:**
   ```
   URL: http://YOUR_SERVER_IP:5002/api/nfc/scan
   Method: POST
   Headers: 
     - Authorization: Bearer taskplanner2025
     - Content-Type: application/json
   Body:
   {
     "tag_id": "{tagid}",
     "task_title": "Your Task Name Here"
   }
   ```

4. **Write Task to Tag:**
   - Select the task you created
   - Hold your NFC tag to phone
   - The task will be written to the tag

### Option 3: Using HTTP Request Shortcuts (Android)

1. **Install HTTP Request Shortcuts** app

2. **Create a Shortcut:**
   - URL: `http://YOUR_SERVER_IP:5002/api/nfc/scan`
   - Method: POST
   - Request Body:
     ```json
     {
       "tag_id": "{nfc_tag_id}",
       "task_title": "Your Task Name"
     }
     ```
   - Headers:
     ```
     Authorization: Bearer taskplanner2025
     Content-Type: application/json
     ```

3. **Trigger via NFC:**
   - Use Tasker or NFC Tasks to launch the shortcut when tag is scanned

### Option 4: Tasker Integration (Android)

1. **Install Tasker** and **NFC for Tasker** plugin

2. **Create Tasker Profile:**
   - Event → Plugin → NFC for Tasker → NFC Tag
   - Select your NFC tag

3. **Create Task:**
   - Action → Net → HTTP Post
   - Server: `http://YOUR_SERVER_IP:5002`
   - Path: `/api/nfc/scan`
   - Headers:
     ```
     Authorization: Bearer taskplanner2025
     Content-Type: application/json
     ```
   - Data / File:
     ```json
     {
       "tag_id": "%nfc_id",
       "task_title": "Your Task Name"
     }
     ```

## Manual API Testing

### Using curl

**Increment a mapped task:**
```bash
curl -X POST http://localhost:5002/api/nfc/scan \
  -H "Authorization: Bearer taskplanner2025" \
  -H "Content-Type: application/json" \
  -d '{
    "tag_id": "04:52:A3:B2:5E:6F:80",
    "task_title": "Water Plants"
  }'
```

**Create a new task mapping:**
```bash
curl -X POST http://localhost:5002/api/nfc/mappings \
  -H "Authorization: Bearer taskplanner2025" \
  -H "Content-Type: application/json" \
  -d '{
    "tag_id": "04:52:A3:B2:5E:6F:80",
    "task_title": "Water Plants"
  }'
```

### Using Python

```python
import requests

SERVER_URL = "http://localhost:5002"
AUTH_TOKEN = "taskplanner2025"

def scan_nfc_tag(tag_id, task_title):
    """Simulate NFC tag scan."""
    response = requests.post(
        f"{SERVER_URL}/api/nfc/scan",
        headers={
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "tag_id": tag_id,
            "task_title": task_title
        }
    )
    return response.json()

# Example usage
result = scan_nfc_tag("04:52:A3:B2:5E:6F:80", "Water Plants")
print(result)
```

## Data Storage

### NFC Mappings File: `data/nfc_mappings.json`

```json
{
  "04:52:A3:B2:5E:6F:80": "Water Plants",
  "04:A1:B2:C3:D4:E5:F6": "Check Mail",
  "04:11:22:33:44:55:66": "Take Medication"
}
```

### NFC Pings Log: `data/nfc_pings.json`

```json
[
  {
    "tag_id": "04:52:A3:B2:5E:6F:80",
    "action": "task_incremented",
    "task_title": "Water Plants",
    "task_index": 1,
    "new_status": 1,
    "reader": "nfc_tools",
    "timestamp": "2025-10-15T14:32:11.123456"
  }
]
```

## Task Status Cycle

Each NFC scan increments the task status:

```
0 (Not Started / Red) → 1 (In Progress / Yellow) → 2 (Completed / Green) → 0 (cycles back)
```

## Security Considerations

1. **Change the default auth token** in production:
   ```bash
   export TASK_AUTH_TOKEN="your-secure-token-here"
   ```

2. **Use HTTPS** in production (not HTTP)

3. **Restrict server access** with firewall rules:
   ```bash
   sudo ufw allow from 192.168.1.0/24 to any port 5002
   ```

4. **Consider adding IP whitelisting** for mobile devices

## Troubleshooting

### Tag Not Incrementing Task

1. **Check server is running:**
   ```bash
   curl http://localhost:5002/api/health
   ```

2. **Check logs:**
   ```bash
   tail -f /var/log/task_planner.log
   ```

3. **Verify authentication:**
   - Make sure the `Authorization` header is included
   - Token should be: `Bearer taskplanner2025`

4. **Check network connectivity:**
   - Ping the server from your phone
   - Make sure port 5002 is open

### Task Not Found

- The task may have been deleted
- Provide `task_title` in the scan request to recreate it

### LED Not Updating

- Check hardware connections
- Verify GPIO pins are configured correctly
- Run LED test: `python main.py --ledtest`

## Advanced Usage

### Bulk Import Mappings

```bash
curl -X POST http://localhost:5002/api/nfc/mappings \
  -H "Authorization: Bearer taskplanner2025" \
  -H "Content-Type: application/json" \
  -d '{
    "tag_id": "TAG_ID_1",
    "task_title": "Task 1"
  }'
```

### View All Mappings

```bash
curl http://localhost:5002/api/nfc/mappings \
  -H "Authorization: Bearer taskplanner2025"
```

### View Recent Pings

```bash
curl "http://localhost:5002/api/nfc/pings?limit=20" \
  -H "Authorization: Bearer taskplanner2025"
```

### Get NFC Statistics

```bash
curl http://localhost:5002/api/nfc/stats \
  -H "Authorization: Bearer taskplanner2025"
```

## Example Workflow

1. **Initial Setup:**
   - Start the web server: `python main.py` → option 6
   - Write NFC tag with HTTP POST action to `/api/nfc/scan`

2. **First Scan:**
   - Scan the tag
   - Task "Water Plants" is created with status 0 (Not Started)
   - LED turns RED

3. **Second Scan:**
   - Scan the tag again
   - Task status increments to 1 (In Progress)
   - LED turns YELLOW

4. **Third Scan:**
   - Scan the tag again
   - Task status increments to 2 (Completed)
   - LED turns GREEN

5. **Fourth Scan:**
   - Scan the tag again
   - Task status cycles back to 0 (Not Started)
   - LED turns RED

## Support

For issues or questions:
- Check the logs in `data/nfc_pings.json`
- Verify mappings in `data/nfc_mappings.json`
- Test API endpoints manually with curl
- Run hardware test: `python main.py --ledtest`

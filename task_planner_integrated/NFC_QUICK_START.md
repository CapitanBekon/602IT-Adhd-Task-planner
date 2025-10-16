# NFC Tag Integration - Quick Start

## 🎯 What This Does

When you scan an NFC tag:
1. The tag sends a request to your server
2. The server finds or creates the task
3. The task status increments (Not Started → In Progress → Completed → Not Started)
4. The LED changes color (Red → Yellow → Green → Red)
5. Everything is logged in `data/nfc_pings.json`

## 📋 Prerequisites

1. **Running Server**: Start the web server
   ```bash
   python main.py
   # Choose option 6: Start Web Server
   ```

2. **Network Access**: Your phone must be on the same network as the Raspberry Pi

3. **NFC Tools App**: Install on your Android/iOS device

## 🚀 Quick Setup Guide

### Step 1: Find Your Server IP

```bash
hostname -I
# Example output: 192.168.1.100
```

### Step 2: Test Server is Running

From your computer:
```bash
curl http://localhost:5002/api/health
```

From your phone's browser:
```
http://192.168.1.100:5002
```

### Step 3: Configure NFC Tag

**Using NFC Tools App:**

1. Open NFC Tools
2. Go to **Tasks** tab
3. Create New Task:
   - Name: "Task Planner Scan"
   - Add Action → **Send HTTP Request**
   
4. Configure HTTP Request:
   ```
   URL: http://192.168.1.100:5002/api/nfc/scan
   Method: POST
   Headers:
     Authorization: Bearer taskplanner2025
     Content-Type: application/json
   Body:
   {
     "tag_id": "{tagid}",
     "task_title": "Water Plants"
   }
   ```

5. Write to NFC Tag:
   - Select the task
   - Hold NFC tag to phone
   - Confirm write

### Step 4: Test the Tag

1. Scan the NFC tag with your phone
2. Watch the server console for logs
3. Check the LED - it should light up RED (task created, status 0)
4. Scan again - LED turns YELLOW (status 1 - In Progress)
5. Scan again - LED turns GREEN (status 2 - Completed)
6. Scan again - LED turns RED (cycles back to 0)

## 🧪 Testing Without NFC Tags

### Option 1: Use the Interactive Simulator

```bash
cd /home/markus/Desktop/task_planner_integrated
python nfc_simulator.py
```

Then follow the menu to simulate tag scans.

### Option 2: Use the Quick Test Script

```bash
cd /home/markus/Desktop/task_planner_integrated
chmod +x test_nfc_scan.sh
./test_nfc_scan.sh
```

### Option 3: Use curl Directly

```bash
# First scan - creates task
curl -X POST http://localhost:5002/api/nfc/scan \
  -H "Authorization: Bearer taskplanner2025" \
  -H "Content-Type: application/json" \
  -d '{"tag_id": "TEST-001", "task_title": "Water Plants"}'

# Second scan - increments to In Progress
curl -X POST http://localhost:5002/api/nfc/scan \
  -H "Authorization: Bearer taskplanner2025" \
  -H "Content-Type: application/json" \
  -d '{"tag_id": "TEST-001", "task_title": "Water Plants"}'

# Third scan - increments to Completed
curl -X POST http://localhost:5002/api/nfc/scan \
  -H "Authorization: Bearer taskplanner2025" \
  -H "Content-Type: application/json" \
  -d '{"tag_id": "TEST-001", "task_title": "Water Plants"}'
```

## 📱 Alternative NFC App Options

### Android: HTTP Request Shortcuts

1. Install "HTTP Request Shortcuts"
2. Create shortcut with same configuration as above
3. Use Tasker to trigger shortcut on NFC scan

### Android: Tasker + AutoInput

1. Install Tasker and AutoInput
2. Create profile: Event → Plugin → NFC
3. Task: HTTP Post (see configuration above)

### iOS: Shortcuts App

1. Open Shortcuts app
2. Create new Automation
3. Trigger: NFC
4. Action: Get Contents of URL (POST request with JSON body)

## 📊 View Your Data

### View All Mappings
```bash
curl http://localhost:5002/api/nfc/mappings \
  -H "Authorization: Bearer taskplanner2025"
```

### View Recent Scans
```bash
curl http://localhost:5002/api/nfc/pings?limit=20 \
  -H "Authorization: Bearer taskplanner2025"
```

### View All Tasks
```bash
curl http://localhost:5002/api/tasks \
  -H "Authorization: Bearer taskplanner2025"
```

## 🎨 Task Status & LED Colors

| Status | Name | LED Color | Next Status |
|--------|------|-----------|-------------|
| 0 | Not Started | 🔴 Red | In Progress |
| 1 | In Progress | 🟡 Yellow | Completed |
| 2 | Completed | 🟢 Green | Not Started |

## 📁 Data Files

All data is stored in the `data/` directory:

- `data/nfc_mappings.json` - Tag ID to task title mappings
- `data/nfc_pings.json` - Log of all tag scans (last 1000)
- `data/tasks.json` - All tasks and their status

## 🔧 Troubleshooting

### Server Won't Start
```bash
# Check if port 5002 is in use
sudo lsof -i :5002

# Try a different port (edit web/app.py)
```

### Tag Scan Not Working

1. **Check server logs**: Look at the terminal running the server
2. **Test with curl**: Use the curl command above to verify server is working
3. **Check authorization**: Make sure the Bearer token is correct
4. **Network issues**: Ping the server from your phone

### LED Not Changing

1. **Run LED test**:
   ```bash
   python main.py --ledtest
   ```

2. **Check GPIO pins**: Make sure they match your wiring in `main.py`

3. **Check power**: Ensure LEDs have proper power and resistors

### Task Not Created

- Check server console for errors
- Verify JSON format in the NFC tag
- Make sure `task_title` is included in the request

## 🔐 Security Notes

**The default auth token is `taskplanner2025`**

For production use:
1. Change the token: `export TASK_AUTH_TOKEN="your-secure-token"`
2. Use HTTPS instead of HTTP
3. Add firewall rules to restrict access

## 📖 Full Documentation

See `NFC_INTEGRATION_GUIDE.md` for complete API documentation and advanced usage.

## 🎓 Example Workflow

**Scenario**: You want to track watering your plants

1. **Write NFC Tag**: Use NFC Tools to configure a tag for "Water Plants"
2. **Place Tag**: Stick the tag near your plants
3. **First Scan**: Scan when you start watering
   - Task created with status 0 (Not Started)
   - LED turns RED
4. **Second Scan**: Scan when watering is in progress
   - Status changes to 1 (In Progress)
   - LED turns YELLOW
5. **Third Scan**: Scan when finished
   - Status changes to 2 (Completed)
   - LED turns GREEN
6. **Next Day**: Scan to start the cycle again
   - Status resets to 0 (Not Started)
   - LED turns RED

## 💡 Tips

- **Use descriptive task titles**: "Water Plants" not just "Plants"
- **One tag per task**: Don't reuse tags for different tasks
- **Test first**: Use the simulator before writing to actual tags
- **Keep logs**: The ping log helps debug issues
- **Regular backups**: Backup the `data/` directory regularly

## 🆘 Need Help?

1. Check the logs in `data/nfc_pings.json`
2. Run the simulator to test without hardware: `python nfc_simulator.py`
3. Verify server health: `curl http://localhost:5002/api/health`
4. Test LEDs: `python main.py --ledtest`

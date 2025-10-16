# Example NFC Tag Configuration for NFC Tools

## Tag 1: Water Plants
```json
{
  "tag_id": "04:AA:BB:CC:DD:EE:01",
  "task_title": "Water Plants"
}
```

**NFC Tools Configuration:**
- URL: http://YOUR_PI_IP:5002/api/nfc/scan
- Method: POST
- Headers:
  ```
  Authorization: Bearer taskplanner2025
  Content-Type: application/json
  ```
- Body:
  ```json
  {
    "tag_id": "{tagid}",
    "task_title": "Water Plants"
  }
  ```

## Tag 2: Check Mail
```json
{
  "tag_id": "04:AA:BB:CC:DD:EE:02",
  "task_title": "Check Mail"
}
```

## Tag 3: Take Medication
```json
{
  "tag_id": "04:AA:BB:CC:DD:EE:03",
  "task_title": "Take Medication"
}
```

## Tag 4: Feed Pets
```json
{
  "tag_id": "04:AA:BB:CC:DD:EE:04",
  "task_title": "Feed Pets"
}
```

## Tag 5: Exercise
```json
{
  "tag_id": "04:AA:BB:CC:DD:EE:05",
  "task_title": "Exercise"
}
```

## Testing These Tags

### Using curl:
```bash
# Test each tag
for tag in "01" "02" "03" "04" "05"; do
  curl -X POST http://localhost:5002/api/nfc/scan \
    -H "Authorization: Bearer taskplanner2025" \
    -H "Content-Type: application/json" \
    -d "{\"tag_id\": \"04:AA:BB:CC:DD:EE:${tag}\", \"task_title\": \"Task ${tag}\"}"
  echo ""
done
```

### Using the simulator:
```bash
python nfc_simulator.py
# Choose option 7 for quick demo
```

## Notes

- Replace `YOUR_PI_IP` with your Raspberry Pi's IP address (find with `hostname -I`)
- The `{tagid}` placeholder in NFC Tools will be automatically replaced with the actual tag UID
- Each scan increments the task status: 0 (Red) → 1 (Yellow) → 2 (Green) → 0 (cycles)
- All scans are logged in `data/nfc_pings.json`

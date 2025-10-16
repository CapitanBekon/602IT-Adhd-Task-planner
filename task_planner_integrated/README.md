# Task Planner - Integrated Task Management System

A comprehensive task management system with hardware integration, NFC support, and web interface.

## Features

### 🎯 Core Task Management
- Create, update, and delete tasks
- Task prioritization and effort estimation
- Due date tracking
- Subtask support with hierarchical structure
- Multiple sorting options (priority, due date, status, effort, title)
- JSON persistence with automatic saving

### 📱 NFC Integration
- Map NFC tags to specific tasks
- Tap to increment task status (Not Started → In Progress → Completed)
- Automatic task creation from new tags
- Comprehensive logging of all NFC interactions
- Tag management and statistics
- **See [NFC_QUICK_START.md](NFC_QUICK_START.md) for setup guide**
- **See [NFC_INTEGRATION_GUIDE.md](NFC_INTEGRATION_GUIDE.md) for full API documentation**

### ⚙️ Hardware Support
- RGB LED status indication (Red: Not Started, Yellow: In Progress, Green: Completed)
- Physical button controls for task interaction
- Support for multiple task-button-LED groups
- Hardware synchronization with task states
- Raspberry Pi GPIO compatibility with mock fallback for development

### 🌐 Web Interface
- Modern, responsive web UI
- Real-time task management
- NFC tag scanning via web interface
- Hardware status monitoring
- Mobile-friendly design

### 🖥️ Console Interface
- Full-featured terminal interface
- Interactive task creation with subtask support
- Hardware testing and diagnostics
- NFC management tools
- Integrated web server launcher

## Installation

### Prerequisites
```bash
# For Raspberry Pi with GPIO support
sudo apt update
sudo apt install python3-pip python3-venv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask RPi.GPIO
```

### Development Setup (No GPIO)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install minimal dependencies
pip install flask
```

## Hardware Setup

### LED Connections (Common Anode RGB LEDs)
```
Task 1 LED: R=GPIO17, G=GPIO27, B=GPIO22
Task 2 LED: R=GPIO23, G=GPIO24, B=GPIO25
```

### Button Connections (Active Low with Pull-up)
```
Task 1 Button: GPIO5
Task 2 Button: GPIO6
```

### Wiring Diagram
```
[3.3V] ── [LED Common Anode]
[GPIO17] ── [220Ω] ── [LED Red]
[GPIO27] ── [220Ω] ── [LED Green] 
[GPIO22] ── [220Ω] ── [LED Blue]

[GPIO5] ── [Button] ── [GND]
[GPIO6] ── [Button] ── [GND]
```

## Quick Start

### 1. Start the Application
```bash
cd task_planner_integrated
python main.py
```

### 2. Start the Web Server
From the console menu, select option 6 to start the web server.
Access at: http://localhost:5002

### 3. Test Your Hardware (Optional)
```bash
python main.py --ledtest
```

### 4. Setup NFC Tags
See **[NFC_QUICK_START.md](NFC_QUICK_START.md)** for complete NFC setup instructions.

## Usage

### Console Interface
The main console interface provides:
- Task management (add, remove, sort)
- NFC tag mapping and management
- Hardware testing and diagnostics
- Web server launcher

### Web Interface
Start the web server from the console menu or directly:
```bash
python web/app.py
```
Access at: http://localhost:5002

### NFC Integration

**Quick Test:**
```bash
# Simulate an NFC scan
python nfc_simulator.py

# Or use curl
curl -X POST http://localhost:5002/api/nfc/scan \
  -H "Authorization: Bearer taskplanner2025" \
  -H "Content-Type: application/json" \
  -d '{"tag_id": "TEST-001", "task_title": "Water Plants"}'
```

**How It Works:**
1. Scan an NFC tag with your phone using NFC Tools
2. The tag sends a POST request to `/api/nfc/scan`
3. The server finds or creates the task
4. Task status increments (0 → 1 → 2 → 0)
5. LED changes color (Red → Yellow → Green → Red)

**Full Documentation:**
- **[NFC_QUICK_START.md](NFC_QUICK_START.md)** - Setup guide for NFC Tools
- **[NFC_INTEGRATION_GUIDE.md](NFC_INTEGRATION_GUIDE.md)** - Complete API reference

## API Endpoints

### Authentication
All API endpoints require Bearer token authentication:
```
Authorization: Bearer taskplanner2025
```

### Task Management
- `GET /api/tasks` - Get all tasks
- `POST /api/tasks` - Create new task
- `GET /api/tasks/{id}` - Get specific task
- `PUT /api/tasks/{id}/status` - Update task status
- `DELETE /api/tasks/{id}` - Delete task
- `POST /api/tasks/sort` - Sort tasks

### NFC Management  
- `GET /api/nfc/mappings` - Get all NFC mappings
- `POST /api/nfc/scan` - Process NFC tag scan
- `POST /api/nfc/mappings` - Create NFC mapping
- `DELETE /api/nfc/mappings/{tag_id}` - Remove NFC mapping
- `GET /api/nfc/pings` - Get recent NFC activity

### Hardware Control
- `GET /api/hardware/status` - Get hardware status
- `POST /api/hardware/sync` - Sync hardware with tasks

## Configuration

### Pin Assignments
Edit `main.py` to configure GPIO pins:
```python
self.LED_PIN_TRIPLETS = [
    (17, 27, 22),  # Task 1: R, G, B
    (23, 24, 25),  # Task 2: R, G, B
]

self.BUTTON_PINS = [
    5,  # Task 1 button
    6,  # Task 2 button  
]
```

### Authentication
Change the authentication token in production:
```python
# In web/app.py
self.auth_token = os.getenv("TASK_AUTH_TOKEN", "your_secure_token")
```

## File Structure
```
task_planner_integrated/
├── main.py                 # Main application entry point
├── core/
│   ├── task_manager.py     # Core task management logic
│   └── nfc_manager.py      # NFC integration system
├── hardware/
│   ├── gpio_compat.py      # GPIO compatibility layer
│   ├── led_controller.py   # LED control functions
│   ├── button_controller.py # Button input handling
│   └── hardware_groups.py  # Task-hardware integration
├── web/
│   └── app.py             # Flask web server
├── templates/
│   └── index.html         # Web interface
├── data/                  # Persistent data storage
│   ├── tasks.json         # Task data
│   ├── nfc_mappings.json  # NFC tag mappings
│   └── nfc_pings.json     # NFC activity log
└── tests/                 # Test files
```

## Development Features

### GPIO Mock
The system includes a GPIO compatibility layer that provides a mock GPIO interface for development on non-Raspberry Pi systems. All GPIO operations work identically whether using real hardware or the mock.

### Testing
- Hardware simulation for button presses
- LED color testing sequences  
- NFC simulation via web interface
- Comprehensive logging and error handling

## Extending the System

### Adding More Hardware
```python
# Add more LED/button combinations to main.py
self.LED_PIN_TRIPLETS.append((new_r, new_g, new_b))
self.BUTTON_PINS.append(new_button_pin)
```

### Custom Task Actions
Override `_handle_task_interaction()` in `TaskPlannerApp` to customize button behavior.

### Additional NFC Readers
The NFC system supports multiple readers - specify reader ID in scan requests for tracking.

## Troubleshooting

### GPIO Permissions
```bash
sudo usermod -a -G gpio $USER
# Log out and back in
```

### Port Already in Use
```bash
# Find and kill process using port 5002
sudo lsof -t -i:5002 | xargs sudo kill -9
```

### Mock GPIO Warning
If you see "REAL_GPIO=False", the system is running in development mode without actual GPIO hardware. This is normal for development environments.

## License
This project is open source. Feel free to modify and distribute according to your needs.
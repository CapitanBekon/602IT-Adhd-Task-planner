#!/usr/bin/env python3
"""
Simple button hardware test for the task planner project.
Based on your `buttonPrint.py` outline but uses the project's `hardware.gpio_compat` (if available)
for a mock-friendly environment and falls back to RPi.GPIO.

Usage:
  BTN_PIN=6 BTN_PULL=UP python3 hardware/button_test.py

Environment:
  BTN_PIN  - BCM pin number (default 6)
  BTN_PULL - UP (default) or DOWN

This script polls the button and prints presses/releases.
"""

import os
import time
from pathlib import Path

# Try to import project managers to integrate with LED/controller logic
USE_PROJECT_INTEGRATION = True
try:
    from core.task_manager import TaskManager
    from hardware.hardware_groups import HardwareManager
except Exception:
    USE_PROJECT_INTEGRATION = False

# Prefer the project's gpio_compat which may provide a mock for testing.
try:
    from hardware import gpio_compat as gpio_compat
    GPIO = gpio_compat
    USING_PROJECT_GPIO = True
except Exception:
    try:
        import RPi.GPIO as GPIO  # type: ignore
        USING_PROJECT_GPIO = False
    except Exception:
        # Minimal fallback mock so script can run on non-Pi environments without failing hard
        class _MockGPIO:
            BCM = 'BCM'
            IN = 'IN'
            PUD_UP = 'PUD_UP'
            PUD_DOWN = 'PUD_DOWN'
            HIGH = 1
            LOW = 0

            def __init__(self):
                self._states = {}

            def setmode(self, mode):
                pass

            def setup(self, pin, mode, pull_up_down=None):
                self._states[pin] = self.HIGH

            def input(self, pin):
                # always return HIGH (not pressed for pull-up configs)
                return self._states.get(pin, self.HIGH)

            def cleanup(self):
                pass

        GPIO = _MockGPIO()
        USING_PROJECT_GPIO = False

buttonPin = int(os.getenv('BTN_PIN', '6'))  # BCM pin for button
pull = os.getenv('BTN_PULL', 'UP').upper()  # UP or DOWN

# Setup GPIO
GPIO.setmode(GPIO.BCM)
if pull == 'DOWN':
    GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
else:
    GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print(f"Using BCM pin {buttonPin} with pull-{pull} (project gpio: {USING_PROJECT_GPIO})")
try:
    raw = GPIO.input(buttonPin)
    print(f"Initial raw GPIO input: {raw} (0=LOW, 1=HIGH)")
except Exception as e:
    print(f"Warning: could not read initial GPIO input: {e}")

last_pressed = None
poll_interval = float(os.getenv('BTN_POLL', '0.05'))

# If possible, set up TaskManager + HardwareManager so button presses update LEDs
hardware_manager = None
task_manager = None
if USE_PROJECT_INTEGRATION:
    try:
        # Resolve project root and data dir
        project_root = Path(__file__).resolve().parents[1]
        data_dir = project_root / 'data'

        task_manager = TaskManager(str(data_dir))
        hardware_manager = HardwareManager(task_manager)

        # Register groups for existing tasks if not already present. Use defaults
        # if tasks file is empty — these defaults mirror main.py's configuration.
        default_led_triplets = [(17, 27, 22), (23, 24, 25)]
        default_button_pins = [5, 6]

        for idx in range(min(len(default_led_triplets), len(default_button_pins))):
            task_id = idx + 1
            r, g, b = default_led_triplets[idx]
            btn = default_button_pins[idx]
            # Avoid re-registering if group already exists
            if task_id not in hardware_manager.groups:
                hardware_manager.register_task_group(task_id=task_id, button_pin=btn,
                                                     r_pin=r, g_pin=g, b_pin=b,
                                                     task_callback=None)
    except Exception as e:
        print(f"Warning: unable to integrate with project managers: {e}")
        hardware_manager = None
        task_manager = None

try:
    while True:
        time.sleep(poll_interval)
        try:
            val = GPIO.input(buttonPin)
        except Exception as e:
            print(f"GPIO read error: {e}")
            continue

        # If using pull-up, pressed == LOW. If pull-down, pressed == HIGH.
        if pull == 'DOWN':
            pressed = (val == GPIO.HIGH)
        else:
            pressed = (val == GPIO.LOW)

        if last_pressed is None:
            # On first loop just record state (avoid noisy early prints)
            last_pressed = pressed
            continue

        if pressed and not last_pressed:
            print("Button Pressed")
            # If we have a hardware manager, find the matching group and cycle its status
            if hardware_manager and task_manager:
                try:
                    # Find group by button pin
                    for tid, group in hardware_manager.groups.items():
                        for btn in group.buttons:
                            if btn.get('pin') == buttonPin:
                                # Cycle task status in task manager and update LEDs
                                new_status = task_manager.increment_completion(tid)
                                hardware_manager.update_task_led(tid, new_status)
                                print(f"Cycled Task {tid} -> status {new_status}")
                                break
                except Exception as e:
                    print(f"Error updating task/LED on button press: {e}")

        elif not pressed and last_pressed:
            print("Button Released")
        last_pressed = pressed
except KeyboardInterrupt:
    print('\nExiting and cleaning up GPIO...')
    try:
        GPIO.cleanup()
    except Exception:
        pass



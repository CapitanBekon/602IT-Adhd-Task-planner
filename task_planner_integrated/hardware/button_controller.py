"""Button controller for task interaction.

Provides an optional polling fallback (enabled via env var TASK_BUTTON_POLLING=1)
for environments where GPIO edge-detection is unavailable or unreliable.
"""

import logging
import os
import threading
import time
from typing import Dict, Callable, Any
from .gpio_compat import GPIO

logger = logging.getLogger(__name__)

class ButtonController:
    """Controls button inputs for task interaction."""
    
    def __init__(self):
        self.buttons = {}  # button_id -> button config
        self.callbacks = {}  # button_id -> callback function
        self._gpio_initialized = False
        # Polling configuration (optional fallback)
        self._polling_enabled = os.getenv('TASK_BUTTON_POLLING', '0') in ('1', 'true', 'True')
        try:
            self._poll_interval = float(os.getenv('TASK_BUTTON_POLL_INTERVAL', '0.02'))
        except Exception:
            self._poll_interval = 0.02
        self._poll_thread = None
        self._poll_thread_run = False
        self._last_states: Dict[str, bool] = {}
        
    def _ensure_gpio_setup(self):
        """Ensure GPIO is properly configured (call once)."""
        if not self._gpio_initialized:
            try:
                GPIO.setwarnings(False)
                GPIO.setmode(GPIO.BCM)
                self._gpio_initialized = True
                logger.info("GPIO initialized in BCM mode for button controller")
            except Exception as e:
                logger.warning(f"GPIO already configured or error: {e}")
        
    def setup_button(self, button_id: str, pin: int, pull_up: bool = True, 
                     callback: Callable[[str, int], None] = None) -> bool:
        """Setup a button with optional callback."""
        self._ensure_gpio_setup()
        try:
            pull_mode = GPIO.PUD_UP if pull_up else GPIO.PUD_DOWN
            GPIO.setup(pin, GPIO.IN, pull_up_down=pull_mode)
            
            # Test initial state
            initial_state = GPIO.input(pin)
            logger.info(f"Setup button '{button_id}' on GPIO{pin} with pull_{'up' if pull_up else 'down'}; "
                       f"initial state: {'LOW (pressed)' if initial_state == GPIO.LOW else 'HIGH (released)'}")
            
            button_config = {
                'pin': pin,
                'pull_up': pull_up,
                'callback': callback
            }
            self.buttons[button_id] = button_config
            
            if callback:
                self.callbacks[button_id] = callback
                # Try to setup GPIO event detection, but don't treat failure as fatal.
                try:
                    GPIO.add_event_detect(pin, GPIO.BOTH,
                                        callback=lambda channel: self._handle_button_event(button_id, channel),
                                        bouncetime=250)
                except Exception as e:
                    # Some platforms or permission modes may not support edge detection.
                    # Keep the button registered and callback stored so the app can
                    # still call callbacks via test helpers or polling.
                    logger.warning(f"GPIO.add_event_detect failed for GPIO{pin}: {e} - enabling polling fallback")
                    # Enable polling fallback automatically so button presses are still detected
                    self._polling_enabled = True
                    self._ensure_polling_started()

            # If polling fallback is enabled, ensure the poll thread is running
            if self._polling_enabled:
                self._ensure_polling_started()

            return True
            
        except Exception as e:
            logger.error(f"Failed to setup button '{button_id}' on GPIO{pin}: {e}")
            return False
            
    def _handle_button_event(self, button_id: str, channel: int) -> None:
        """Internal GPIO event handler."""
        try:
            if button_id not in self.buttons:
                return
                
            button_config = self.buttons[button_id]
            pin = button_config['pin']
            pull_up = button_config['pull_up']
            callback = button_config['callback']
            
            # Read current state
            current_state = GPIO.input(pin)
            
            # For pull-up configuration, button press is LOW
            # For pull-down configuration, button press is HIGH
            is_pressed = (current_state == GPIO.LOW) if pull_up else (current_state == GPIO.HIGH)
            
            # Only trigger callback on button press (not release)
            if is_pressed and callback:
                logger.info(f"Button '{button_id}' pressed on GPIO{pin}")
                callback(button_id, pin)
                
        except Exception as e:
            logger.error(f"Error handling button event for '{button_id}': {e}")
            
    def set_callback(self, button_id: str, callback: Callable[[str, int], None]) -> bool:
        """Set or update callback for a button."""
        if button_id not in self.buttons:
            logger.error(f"Button '{button_id}' not found")
            return False
            
        try:
            self.callbacks[button_id] = callback
            self.buttons[button_id]['callback'] = callback
            
            # Update GPIO event detection; be tolerant if platform doesn't support it
            pin = self.buttons[button_id]['pin']
            try:
                GPIO.remove_event_detect(pin)
            except Exception:
                # ignore if removal isn't supported
                pass

            try:
                GPIO.add_event_detect(pin, GPIO.BOTH,
                                    callback=lambda channel: self._handle_button_event(button_id, channel),
                                    bouncetime=250)
            except Exception as e:
                logger.warning(f"GPIO.add_event_detect failed while updating callback for GPIO{pin}: {e} - callback will still be stored")
            
            logger.info(f"Updated callback for button '{button_id}'")
            return True
            
        except Exception as e:
            logger.error(f"Error setting callback for button '{button_id}': {e}")
            return False
            
    def get_button_state(self, button_id: str) -> bool:
        """Get current state of a button. Returns True if pressed."""
        if button_id not in self.buttons:
            return False
            
        try:
            button_config = self.buttons[button_id]
            pin = button_config['pin']
            pull_up = button_config['pull_up']
            
            current_state = GPIO.input(pin)
            return (current_state == GPIO.LOW) if pull_up else (current_state == GPIO.HIGH)
            
        except Exception as e:
            logger.error(f"Error reading button state for '{button_id}': {e}")
            return False
            
    def remove_button(self, button_id: str) -> bool:
        """Remove a button and its GPIO event detection."""
        if button_id not in self.buttons:
            return False
            
        try:
            pin = self.buttons[button_id]['pin']
            GPIO.remove_event_detect(pin)
            
            del self.buttons[button_id]
            if button_id in self.callbacks:
                del self.callbacks[button_id]
                
            logger.info(f"Removed button '{button_id}'")
            return True
            
        except Exception as e:
            logger.error(f"Error removing button '{button_id}': {e}")
            return False
            
    def list_buttons(self) -> Dict[str, Any]:
        """Get list of all configured buttons."""
        return {btn_id: {
            'pin': config['pin'],
            'pull_up': config['pull_up'],
            'has_callback': config['callback'] is not None,
            'current_state': self.get_button_state(btn_id)
        } for btn_id, config in self.buttons.items()}
        
    def cleanup(self) -> None:
        """Clean up all buttons and GPIO."""
        try:
            # Stop polling thread if running
            try:
                self._stop_polling()
            except Exception:
                pass

            for button_id in list(self.buttons.keys()):
                self.remove_button(button_id)
            GPIO.cleanup()
            logger.info("Button controller cleanup completed")
        except Exception as e:
            logger.error(f"Error during button cleanup: {e}")
            
    def test_button(self, button_id: str) -> None:
        """Test a button by triggering its callback manually (for development)."""
        if button_id in self.buttons and self.buttons[button_id]['callback']:
            pin = self.buttons[button_id]['pin']
            logger.info(f"Testing button '{button_id}' manually")
            self.buttons[button_id]['callback'](button_id, pin)

    # --- Polling fallback implementation ---------------------------------
    def _ensure_polling_started(self) -> None:
        """Start polling thread if not already running."""
        if self._poll_thread and self._poll_thread.is_alive():
            return

        # Initialize last-known states to avoid emitting a press event on start
        try:
            for btn_id, cfg in list(self.buttons.items()):
                try:
                    pin = cfg['pin']
                    pull_up = cfg.get('pull_up', True)
                    current_state_raw = GPIO.input(pin)
                    is_pressed = (current_state_raw == GPIO.LOW) if pull_up else (current_state_raw == GPIO.HIGH)
                    self._last_states[btn_id] = bool(is_pressed)
                except Exception:
                    # If we cannot read a pin during init, default to not pressed
                    self._last_states[btn_id] = False
        except Exception:
            pass

        self._poll_thread_run = True
        self._poll_thread = threading.Thread(target=self._poll_loop, name='ButtonPoller', daemon=True)
        self._poll_thread.start()
        logger.info(f"Button polling started (interval={self._poll_interval}s)")

    def _stop_polling(self, join_timeout: float = 1.0) -> None:
        """Stop polling thread gracefully."""
        try:
            self._poll_thread_run = False
            if self._poll_thread and self._poll_thread.is_alive():
                self._poll_thread.join(timeout=join_timeout)
        except Exception as e:
            logger.warning(f"Error stopping poll thread: {e}")
        finally:
            self._poll_thread = None

    def _poll_loop(self) -> None:
        """Background loop that polls button GPIO states and triggers callbacks."""
        try:
            while self._poll_thread_run:
                for btn_id, cfg in list(self.buttons.items()):
                    try:
                        pin = cfg['pin']
                        pull_up = cfg.get('pull_up', True)
                        callback = cfg.get('callback')

                        current_state_raw = GPIO.input(pin)
                        is_pressed = (current_state_raw == GPIO.LOW) if pull_up else (current_state_raw == GPIO.HIGH)

                        last = self._last_states.get(btn_id, False)
                        # Detect rising edge of press (released -> pressed)
                        if is_pressed and not last:
                            if callback:
                                try:
                                    logger.debug(f"Polling detected press for {btn_id} on GPIO{pin}")
                                    callback(btn_id, pin)
                                except Exception as cb_e:
                                    logger.error(f"Error in button callback for '{btn_id}': {cb_e}")
                            self._last_states[btn_id] = True
                        elif not is_pressed and last:
                            # released
                            self._last_states[btn_id] = False

                    except Exception as inner_e:
                        logger.debug(f"Error polling button '{btn_id}': {inner_e}")

                time.sleep(self._poll_interval)
        except Exception as e:
            logger.error(f"Button polling loop terminated with error: {e}")
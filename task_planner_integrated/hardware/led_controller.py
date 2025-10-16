"""LED controller for RGB status indication."""

from typing import Dict, Callable
import logging
from .gpio_compat import GPIO

logger = logging.getLogger(__name__)

class LEDController:
    """Controls RGB LEDs for task status indication."""
    
    def __init__(self):
        self.leds = {}  # pin_id -> LED config
        self._gpio_initialized = False
        
    def _ensure_gpio_setup(self):
        """Ensure GPIO is properly configured (call once)."""
        if not self._gpio_initialized:
            try:
                GPIO.setwarnings(False)
                GPIO.setmode(GPIO.BCM)
                self._gpio_initialized = True
                logger.info("GPIO initialized in BCM mode for LED controller")
            except Exception as e:
                logger.warning(f"GPIO already configured or error: {e}")
        
    def setup_rgb_led(self, led_id: str, r_pin: int, g_pin: int, b_pin: int) -> Dict[str, int]:
        """Setup an RGB LED with given pins (common-anode)."""
        self._ensure_gpio_setup()
        try:
            GPIO.setup(r_pin, GPIO.OUT, initial=GPIO.HIGH)
            GPIO.setup(g_pin, GPIO.OUT, initial=GPIO.HIGH)
            GPIO.setup(b_pin, GPIO.OUT, initial=GPIO.HIGH)
            
            pins = {'r': r_pin, 'g': g_pin, 'b': b_pin}
            self.leds[led_id] = pins
            
            logger.info(f"Setup RGB LED '{led_id}' on pins R{r_pin} G{g_pin} B{b_pin}")
            return pins
            
        except Exception as e:
            logger.error(f"Failed to setup LED '{led_id}': {e}")
            return {}
            
    def led_off(self, led_id: str = None, r_pin: int = None, g_pin: int = None, b_pin: int = None) -> None:
        """Turn off LED (all colors high for common-anode)."""
        try:
            if led_id and led_id in self.leds:
                pins = self.leds[led_id]
                GPIO.output(pins['r'], GPIO.HIGH)
                GPIO.output(pins['g'], GPIO.HIGH)
                GPIO.output(pins['b'], GPIO.HIGH)
            elif r_pin is not None and g_pin is not None and b_pin is not None:
                GPIO.output(r_pin, GPIO.HIGH)
                GPIO.output(g_pin, GPIO.HIGH)
                GPIO.output(b_pin, GPIO.HIGH)
        except Exception as e:
            logger.error(f"Error turning off LED: {e}")

    def led_red(self, led_id: str = None, r_pin: int = None, g_pin: int = None, b_pin: int = None) -> None:
        """Set LED to red."""
        try:
            if led_id and led_id in self.leds:
                pins = self.leds[led_id]
                GPIO.output(pins['r'], GPIO.LOW)
                GPIO.output(pins['g'], GPIO.HIGH)
                GPIO.output(pins['b'], GPIO.HIGH)
            elif r_pin is not None and g_pin is not None and b_pin is not None:
                GPIO.output(r_pin, GPIO.LOW)
                GPIO.output(g_pin, GPIO.HIGH)
                GPIO.output(b_pin, GPIO.HIGH)
        except Exception as e:
            logger.error(f"Error setting LED to red: {e}")

    def led_yellow(self, led_id: str = None, r_pin: int = None, g_pin: int = None, b_pin: int = None) -> None:
        """Set LED to yellow."""
        try:
            if led_id and led_id in self.leds:
                pins = self.leds[led_id]
                GPIO.output(pins['r'], GPIO.LOW)
                GPIO.output(pins['g'], GPIO.LOW)
                GPIO.output(pins['b'], GPIO.HIGH)
            elif r_pin is not None and g_pin is not None and b_pin is not None:
                GPIO.output(r_pin, GPIO.LOW)
                GPIO.output(g_pin, GPIO.LOW)
                GPIO.output(b_pin, GPIO.HIGH)
        except Exception as e:
            logger.error(f"Error setting LED to yellow: {e}")

    def led_green(self, led_id: str = None, r_pin: int = None, g_pin: int = None, b_pin: int = None) -> None:
        """Set LED to green."""
        try:
            if led_id and led_id in self.leds:
                pins = self.leds[led_id]
                GPIO.output(pins['r'], GPIO.HIGH)
                GPIO.output(pins['g'], GPIO.LOW)
                GPIO.output(pins['b'], GPIO.HIGH)
            elif r_pin is not None and g_pin is not None and b_pin is not None:
                GPIO.output(r_pin, GPIO.HIGH)
                GPIO.output(g_pin, GPIO.LOW)
                GPIO.output(b_pin, GPIO.HIGH)
        except Exception as e:
            logger.error(f"Error setting LED to green: {e}")
            
    def led_blue(self, led_id: str = None, r_pin: int = None, g_pin: int = None, b_pin: int = None) -> None:
        """Set LED to blue."""
        try:
            if led_id and led_id in self.leds:
                pins = self.leds[led_id]
                GPIO.output(pins['r'], GPIO.HIGH)
                GPIO.output(pins['g'], GPIO.HIGH)
                GPIO.output(pins['b'], GPIO.LOW)
            elif r_pin is not None and g_pin is not None and b_pin is not None:
                GPIO.output(r_pin, GPIO.HIGH)
                GPIO.output(g_pin, GPIO.HIGH)
                GPIO.output(b_pin, GPIO.LOW)
        except Exception as e:
            logger.error(f"Error setting LED to blue: {e}")

    def led_purple(self, led_id: str = None, r_pin: int = None, g_pin: int = None, b_pin: int = None) -> None:
        """Set LED to purple."""
        try:
            if led_id and led_id in self.leds:
                pins = self.leds[led_id]
                GPIO.output(pins['r'], GPIO.LOW)
                GPIO.output(pins['g'], GPIO.HIGH)
                GPIO.output(pins['b'], GPIO.LOW)
            elif r_pin is not None and g_pin is not None and b_pin is not None:
                GPIO.output(r_pin, GPIO.LOW)
                GPIO.output(g_pin, GPIO.HIGH)
                GPIO.output(b_pin, GPIO.LOW)
        except Exception as e:
            logger.error(f"Error setting LED to purple: {e}")

    def set_led_color(self, led_id: str, color: str) -> None:
        """Set LED to a specific color by name."""
        color_map = {
            'off': self.led_off,
            'red': self.led_red,
            'yellow': self.led_yellow,
            'green': self.led_green,
            'blue': self.led_blue,
            'purple': self.led_purple
        }
        
        if color.lower() in color_map:
            color_map[color.lower()](led_id=led_id)
        else:
            logger.warning(f"Unknown color: {color}")
            
    def cleanup(self) -> None:
        """Turn off all LEDs and cleanup GPIO."""
        try:
            for led_id in self.leds:
                self.led_off(led_id=led_id)
            GPIO.cleanup()
            logger.info("LED controller cleanup completed")
        except Exception as e:
            logger.error(f"Error during LED cleanup: {e}")

# Status to LED color mappings
STATUS_TO_LED_FUNC = {
    0: 'red',     # Not started
    1: 'yellow',  # In progress
    2: 'green'    # Completed
}

STATUS_TO_COLOR = {
    0: "red",
    1: "yellow", 
    2: "green"
}
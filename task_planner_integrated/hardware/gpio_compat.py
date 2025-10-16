"""GPIO compatibility layer for Raspberry Pi and development environments.

If running on a Raspberry Pi with RPi.GPIO installed, this module simply
re-exports the real library. If not, it provides a lightweight mock that
implements the subset of the API used by this project so the rest of the
code can execute (useful for development/testing on non-Pi machines).
"""
from __future__ import annotations

try:  # pragma: no cover - simple import guard
    import RPi.GPIO as _GPIO  # type: ignore
    GPIO = _GPIO
    REAL_GPIO = True
except Exception:  # ModuleNotFoundError or other import failure
    REAL_GPIO = False

    class _MockGPIO:
        # Constants (symbolic only)
        BCM = "BCM"
        BOARD = "BOARD"
        IN = "IN"
        OUT = "OUT"
        HIGH = 1
        LOW = 0
        PUD_UP = "PUD_UP"
        PUD_DOWN = "PUD_DOWN"
        BOTH = "BOTH"

        def __init__(self):
            self._pins = {}
            self._callbacks = {}
            self._warnings = False
            self._mode = None

        # API methods used by the project
        def setwarnings(self, flag: bool):
            self._warnings = flag

        def setmode(self, mode):
            self._mode = mode

        def setup(self, pin, direction, pull_up_down=None, initial=None):
            self._pins[pin] = {
                "dir": direction,
                "pud": pull_up_down,
                "value": self.HIGH if initial is None else initial,
            }

        def output(self, pin, value):
            if pin in self._pins:
                self._pins[pin]["value"] = value

        def input(self, pin):
            # Default HIGH (unpressed for pull-up) if unknown
            return self._pins.get(pin, {}).get("value", self.HIGH)

        def add_event_detect(self, pin, edge, callback=None, bouncetime=200):
            if callback:
                self._callbacks[pin] = callback

        def remove_event_detect(self, pin):
            self._callbacks.pop(pin, None)

        def trigger(self, pin, value=None):  # helper for tests
            if value is not None:
                self.output(pin, value)
            cb = self._callbacks.get(pin)
            if cb:
                cb(pin)

        def cleanup(self):
            self._pins.clear()
            self._callbacks.clear()

    GPIO = _MockGPIO()

__all__ = ["GPIO", "REAL_GPIO"]
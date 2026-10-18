"""
scanner_reader.py
Cross-platform USB QR/Barcode Scanner Listener for Robuverse.

Supports:
- Linux (Raspberry Pi 5): Direct background hardware capture via evdev (/dev/input/event*)
  Runs headless without needing desktop GUI or terminal focus.
- Windows/Dev: Console stdin listener & API trigger for immediate local testing.
"""

import sys
import threading
import time
import logging
from typing import Callable, Optional

logger = logging.getLogger("scanner_reader")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")


class QRScannerListener:
    def __init__(self, on_scan_callback: Callable[[str], None]):
        self.on_scan = on_scan_callback
        self.is_running = False
        self.platform = sys.platform
        self.thread: Optional[threading.Thread] = None
        self.device_name: str = "Unknown"

    def start(self):
        self.is_running = True
        if self.platform.startswith("linux"):
            logger.info("Operating System detected: Linux (Raspberry Pi mode)")
            self.thread = threading.Thread(target=self._run_linux_evdev, daemon=True)
        else:
            logger.info(f"Operating System detected: {self.platform} (Console/Windows mode)")
            self.thread = threading.Thread(target=self._run_windows_console, daemon=True)
        
        self.thread.start()

    def stop(self):
        self.is_running = False

    def _run_windows_console(self):
        """
        Console input listener for Windows testing.
        USB QR scanners act as HID keyboards, typing text followed by Enter.
        """
        self.device_name = "Windows USB Keyboard / Console Input"
        logger.info("Scanner listener ready on Windows. You can scan a QR code into this terminal now!")
        
        while self.is_running:
            try:
                line = sys.stdin.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                scanned_text = line.strip()
                if scanned_text:
                    logger.info(f"[SCAN RECEIVED]: {scanned_text}")
                    self.on_scan(scanned_text)
            except Exception as e:
                logger.error(f"Error reading console input: {e}")
                time.sleep(1)

    def _run_linux_evdev(self):
        """
        Direct hardware capture for Raspberry Pi 5 using evdev.
        Grabs the USB scanner device so input works in the background (headless)
        and doesn't interfere with the system terminal.
        """
        try:
            import evdev
            from evdev import ecodes
        except ImportError:
            logger.error("evdev is not installed! On Raspberry Pi, run: pip install evdev")
            return

        # Keycode mapping table for standard keyboard characters
        KEY_MAP = {
            ecodes.KEY_0: ("0", ")"), ecodes.KEY_1: ("1", "!"), ecodes.KEY_2: ("2", "@"),
            ecodes.KEY_3: ("3", "#"), ecodes.KEY_4: ("4", "$"), ecodes.KEY_5: ("5", "%"),
            ecodes.KEY_6: ("6", "^"), ecodes.KEY_7: ("7", "&"), ecodes.KEY_8: ("8", "*"),
            ecodes.KEY_9: ("9", "("),
            ecodes.KEY_A: ("a", "A"), ecodes.KEY_B: ("b", "B"), ecodes.KEY_C: ("c", "C"),
            ecodes.KEY_D: ("d", "D"), ecodes.KEY_E: ("e", "E"), ecodes.KEY_F: ("f", "F"),
            ecodes.KEY_G: ("g", "G"), ecodes.KEY_H: ("h", "H"), ecodes.KEY_I: ("i", "I"),
            ecodes.KEY_J: ("j", "J"), ecodes.KEY_K: ("k", "K"), ecodes.KEY_L: ("l", "L"),
            ecodes.KEY_M: ("m", "M"), ecodes.KEY_N: ("n", "N"), ecodes.KEY_O: ("o", "O"),
            ecodes.KEY_P: ("p", "P"), ecodes.KEY_Q: ("q", "Q"), ecodes.KEY_R: ("r", "R"),
            ecodes.KEY_S: ("s", "S"), ecodes.KEY_T: ("t", "T"), ecodes.KEY_U: ("u", "U"),
            ecodes.KEY_V: ("v", "V"), ecodes.KEY_W: ("w", "W"), ecodes.KEY_X: ("x", "X"),
            ecodes.KEY_Y: ("y", "Y"), ecodes.KEY_Z: ("z", "Z"),
            ecodes.KEY_SPACE: (" ", " "),
            ecodes.KEY_MINUS: ("-", "_"),
            ecodes.KEY_EQUAL: ("=", "+"),
            ecodes.KEY_LEFTBRACE: ("[", "{"),
            ecodes.KEY_RIGHTBRACE: ("]", "}"),
            ecodes.KEY_BACKSLASH: ("\\", "|"),
            ecodes.KEY_SEMICOLON: (";", ":"),
            ecodes.KEY_APOSTROPHE: ("'", '"'),
            ecodes.KEY_GRAVE: ("`", "~"),
            ecodes.KEY_COMMA: (",", "<"),
            ecodes.KEY_DOT: (".", ">"),
            ecodes.KEY_SLASH: ("/", "?"),
        }

        while self.is_running:
            target_device = None
            try:
                # Find input devices
                devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
                logger.info(f"Scanning for input devices... Found {len(devices)} device(s).")

                # Match devices with barcode/scanner/keyboard keywords
                for dev in devices:
                    name_lower = dev.name.lower()
                    if any(term in name_lower for term in ["scanner", "barcode", "qr", "hid", "keyboard"]):
                        target_device = dev
                        break
                
                # If no specific keyword matches, pick the first device with keyboard capability
                if not target_device and devices:
                    for dev in devices:
                        caps = dev.capabilities()
                        if ecodes.EV_KEY in caps:
                            target_device = dev
                            break

                if not target_device:
                    logger.warning("No USB scanner/keyboard found. Retrying in 3 seconds...")
                    time.sleep(3)
                    continue

                self.device_name = f"{target_device.name} ({target_device.fn})"
                logger.info(f"Connected to scanner hardware: {self.device_name}")

                # Optional: grab device exclusively so keystrokes don't type into Linux console
                try:
                    target_device.grab()
                except Exception as e:
                    logger.debug(f"Device grab skipped/failed: {e}")

                buffer = []
                shift_pressed = False

                for event in target_device.read_loop():
                    if not self.is_running:
                        break

                    if event.type == ecodes.EV_KEY:
                        # Shift key state
                        if event.code in (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT):
                            shift_pressed = (event.value != 0)
                            continue

                        # Key down event
                        if event.value == 1:
                            if event.code in (ecodes.KEY_ENTER, ecodes.KEY_KPENTER):
                                scanned_text = "".join(buffer).strip()
                                buffer.clear()
                                if scanned_text:
                                    logger.info(f"[PI SCAN RECEIVED]: {scanned_text}")
                                    self.on_scan(scanned_text)
                            elif event.code == ecodes.KEY_BACKSPACE:
                                if buffer:
                                    buffer.pop()
                            elif event.code in KEY_MAP:
                                regular, shifted = KEY_MAP[event.code]
                                char = shifted if shift_pressed else regular
                                buffer.append(char)

            except Exception as e:
                logger.error(f"Scanner connection lost: {e}. Reconnecting in 2 seconds...")
                time.sleep(2)
            finally:
                if target_device:
                    try:
                        target_device.ungrab()
                    except Exception:
                        pass

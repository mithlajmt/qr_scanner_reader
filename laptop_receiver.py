"""
laptop_receiver.py
Robuverse Wireless Virtual USB Barcode Wedge.

Runs in the background on your laptop. Connects to the Raspberry Pi 5 / Robot
over Wi-Fi. When a QR code is scanned on the robot, this script automatically
types the scanned value and presses Enter into whatever window/app is currently focused
(Notepad, Excel, web browsers, billing software, etc.).
"""

import sys
import json
import time
import asyncio
import logging
from typing import Optional

try:
    from pynput.keyboard import Controller, Key
    keyboard_controller = Controller()
except ImportError:
    keyboard_controller = None

try:
    import websockets
except ImportError:
    print("Error: 'websockets' is not installed. Run: pip install websockets")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("virtual_scanner")


def inject_keystrokes(text: str, hit_enter: bool = True):
    """
    Simulates physical USB scanner keystrokes into the active window.
    """
    if keyboard_controller:
        # Cross-platform typing via pynput
        keyboard_controller.type(text)
        if hit_enter:
            time.sleep(0.01)
            keyboard_controller.press(Key.enter)
            keyboard_controller.release(Key.enter)
    else:
        # Fallback for Windows using ctypes
        import ctypes
        user32 = ctypes.windll.user32
        for char in text:
            user32.keybd_event(0, ord(char), 0x0004, 0)         # KEYEVENTF_UNICODE = 0x0004
            user32.keybd_event(0, ord(char), 0x0004 | 0x0002, 0) # KEYEVENTF_KEYUP = 0x0002
            time.sleep(0.002)
        if hit_enter:
            user32.keybd_event(0x0D, 0, 0, 0)
            user32.keybd_event(0x0D, 0, 0x0002, 0)


async def receiver_loop(host: str, port: int = 8000):
    uri = f"ws://{host}:{port}/ws"
    
    print("\n" + "=" * 65)
    print("  ROBUVERSE WIRELESS VIRTUAL USB SCANNER")
    print("=" * 65)
    print(f" Target Robot Host : {host}:{port}")
    print(f" Connecting to     : {uri}")
    print("=" * 65)
    print(" Instructions:")
    print("  1. Leave this window open in the background.")
    print("  2. Click into any app (Notepad, Excel, Chrome, etc.).")
    print("  3. Whenever a QR is scanned on the robot, it will type right there!")
    print("=" * 65 + "\n")

    retry_delay = 2
    while True:
        try:
            logger.info(f"Connecting to robot at {uri}...")
            async with websockets.connect(uri) as ws:
                logger.info(" Connected to Robot! Virtual USB Scanner is ACTIVE.\n")
                retry_delay = 2  # Reset backoff on successful connect
                
                while True:
                    message = await ws.recv()
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "NEW_SCAN":
                            scan_data = data.get("data", {})
                            scanned_val = scan_data.get("value", "")
                            source = scan_data.get("source", "Scanner")
                            timestamp = scan_data.get("timestamp", time.strftime("%H:%M:%S"))
                            
                            if scanned_val:
                                print(f" [{timestamp}] SCAN DETECTED from {source}:", flush=True)
                                print(f"    --> Typing: \"{scanned_val}\" + [ENTER]", flush=True)
                                
                                # Inject keystrokes directly into active application
                                inject_keystrokes(scanned_val, hit_enter=True)
                                print("     Typing complete.\n", flush=True)
                                
                        elif msg_type == "INIT_STATE":
                            total = data.get("total_scans", 0)
                            logger.info(f" Initialized state. Total scans on robot so far: {total}")
                            
                    except json.JSONDecodeError:
                        pass
        except (websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.ConnectionClosedOK,
                OSError) as e:
            logger.warning(f"Connection lost ({e}). Reconnecting in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 1.5, 10)
        except Exception as e:
            logger.error(f"Unexpected error: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


def main():
    # If IP is passed as argument, e.g. python laptop_receiver.py 192.168.1.5
    if len(sys.argv) > 1:
        target_host = sys.argv[1].strip()
    else:
        print("\nEnter Robot / Pi IP address (Press ENTER to use 'localhost'): ", end="", flush=True)
        user_input = sys.stdin.readline().strip()
        target_host = user_input if user_input else "localhost"

    # Strip http:// or ws:// if user typed it
    target_host = target_host.replace("http://", "").replace("https://", "").replace("ws://", "").replace("wss://", "")
    if ":" in target_host:
        host, port_str = target_host.split(":")
        port = int(port_str)
    else:
        host = target_host
        port = 8000

    try:
        asyncio.run(receiver_loop(host, port))
    except KeyboardInterrupt:
        print("\nVirtual USB Scanner stopped by user. Goodbye!")


if __name__ == "__main__":
    main()

# 🤖 Robuverse Robot Chest QR Scanner

A lightweight, zero-latency QR code scanning and telemetry system for the Robuverse Robot. 
Mount the USB QR scanner to the robot's chest connected to a **Raspberry Pi 5**, and view scans live on any laptop, tablet, or mobile phone connected to the same Wi-Fi network.

---

## 📑 Table of Contents
- [How It Works](#-how-it-works)
- [How to Run on Windows (Testing Mode)](#-how-to-run-on-windows-testing-mode)
- [How to Run on Raspberry Pi 5 (Robot Deployment)](#-how-to-run-on-raspberry-pi-5-robot-deployment)
- [How to View on Another Laptop or Phone](#-how-to-view-on-another-laptop-or-phone)
- [Dashboard Features](#-dashboard-features)
- [REST API for Robot Scripts](#-rest-api-for-robot-scripts)
- [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## ⚡ How It Works

```
┌──────────────┐
│   QR Code    │
└──────┬───────┘
       │ (Physical Scan)
       ▼
┌───────────────────────────┐
│ USB QR Scanner (Chest)    │ ── Standard USB HID Keyboard mode
└──────────────┬────────────┘
               │ (USB Cable)
               ▼
┌───────────────────────────┐
│ Raspberry Pi 5 / PC       │
│  ├── scanner_reader.py    │ ── Linux: grabs /dev/input/event* (headless/background)
│  │                        │    Windows: listens to console/terminal keystrokes
│  └── server.py (FastAPI)  │ ── Broadcasts scans via WebSockets on Port 8000
└──────────────┬────────────┘
                               │ (Local Wi-Fi Network)
                               ▼
     ┌────────────────────────────────────────────────────────┐
     │                                                        │
     ▼                                                        ▼
┌───────────────────────────┐            ┌────────────────────────────────────────┐
│ Laptop / Mobile Browser   │            │ Laptop Virtual USB Receiver            │
│  └── Live Cyberpunk HUD   │            │  └── laptop_receiver.py                │
│      (http://<ip>:8000)   │            │      Directly types into Notepad/Excel │
└───────────────────────────┘            └────────────────────────────────────────┘
```

---

## ⌨️ Wireless Virtual USB Scanner Mode (Typing into Notepad/Excel)

If you want the laptop to behave **as if the scanner was physically plugged into it via USB** (automatically typing scanned values and pressing Enter into Notepad, Excel, or any application):

1. **On your laptop**, simply double-click:
   ```
   start_receiver.bat
   ```
   *(Or run `python laptop_receiver.py <ROBOT_IP>` in terminal)*
2. It will connect to your robot over Wi-Fi.
3. Open **Notepad, Word, Excel, or any web form** and click anywhere to place your cursor.
4. When someone scans a QR code on the robot, **it types the string into your app and hits `Enter` automatically!**

---

## 💻 How to Run on Windows (Testing Mode)

Since your USB scanner is currently connected to your Windows computer, you can run and test the complete system right now.

### Option A: One-Click Launch (Easiest)
Simply double-click the **`start.bat`** file in the project folder.

---

### Option B: Using Terminal / PowerShell

1. Open PowerShell or Command Prompt in the project directory:
   ```powershell
   cd c:\Users\ACM\Desktop\robuverse_internal\scanner_project
   ```

2. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\activate
   ```

3. Start the server:
   ```powershell
   python server.py
   ```

4. Open your browser:
   - Navigate to: **[http://localhost:8000](http://localhost:8000)**
   - Scan any QR code with your USB scanner!

---

## 🤖 How to Run on Raspberry Pi 5 (Robot Deployment)

When you are ready to mount the scanner onto the robot with the Raspberry Pi 5:

### 1. Transfer the Project to the Pi
From your laptop terminal:
```bash
scp -r scanner_project pi@<pi-ip>:~/scanner_project
```
*(Or clone it directly using `git clone`)*

### 2. Run the Startup Script
On the Raspberry Pi:
```bash
cd ~/scanner_project
chmod +x start.sh
./start.sh
```
This script will automatically create the `.venv`, install `fastapi`, `uvicorn`, and `evdev`, and start the scanner service.

---

### 3. (Recommended) Auto-Start on Robot Boot (Systemd)
To ensure the scanner server runs automatically whenever the robot powers on (without needing a monitor, keyboard, or SSH):

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/robuverse-scanner.service
   ```

2. Paste the following configuration:
   ```ini
   [Unit]
   Description=Robuverse QR Scanner Daemon
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/scanner_project
   ExecStart=/home/pi/scanner_project/.venv/bin/python /home/pi/scanner_project/server.py
   Restart=always
   RestartSec=3

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable robuverse-scanner
   sudo systemctl start robuverse-scanner
   ```

4. Check service status:
   ```bash
   sudo systemctl status robuverse-scanner
   ```

---

## 🌐 How to View on Another Laptop or Phone

You do **not** need to install any software on your viewing laptop or mobile phone.

1. Ensure both the Pi (or host PC) and your viewing laptop are connected to the **same Wi-Fi router or mobile hotspot**.
2. Find the IP address:
   - The IP address is printed in the terminal when you run `python server.py`.
   - It is also displayed in the lower telemetry bar on the dashboard.
   - Example IP: `192.168.1.5`
3. On your second laptop or phone, open your browser (Chrome, Edge, Safari, Firefox) and go to:
   ```
   http://<YOUR_IP>:8000
   ```
   *(e.g., `http://192.168.1.5:8000`)*

---

## 🎛️ Dashboard Features

- **Real-Time WebSocket Sync:** 0ms latency display of scanned codes.
- **Audio Chime:** Plays a synthesized futuristic beep on every scan (can be muted via the **Sound: ON/OFF** toggle).
- **One-Click Copy:** Easily copy the scanned string to your clipboard.
- **Scan History:** Displays a chronological log of all recent scans with timestamps.
- **Manual / Remote Simulation:** An input field on the dashboard allows you to type or paste a QR code to simulate scans remotely for testing.

---

## 📡 REST API for Robot Scripts

If your robot has other Python scripts (e.g. ROS nodes, motor controllers, speech systems) that need to trigger or fetch scans:

| Method | Endpoint | Description | Example Payload |
|---|---|---|---|
| `GET` | `/api/info` | Returns system info, IP, and connected clients | — |
| `GET` | `/api/history` | Returns the list of recent scans | — |
| `POST` | `/api/scan` | Triggers a scan event programmatically | `{"value": "QR_CODE_123", "source": "ROS Node"}` |

---

## 🛠️ Troubleshooting & FAQs

### 1. Permission Denied on Linux (`/dev/input/event*`)
If running on Raspberry Pi without root, ensure the `pi` user is in the `input` group:
```bash
sudo usermod -a -G input $USER
```
Then log out and log back in, or restart the Pi.

### 2. Can't open the webpage from another laptop?
- Check that both machines are on the **exact same Wi-Fi network**.
- On Windows, make sure Windows Defender Firewall allows Python / Port 8000 on Private Networks.
- On Linux/Pi, ensure UFW isn't blocking port 8000:
  ```bash
  sudo ufw allow 8000
  ```

### 3. How do I stop the server?
Press `Ctrl + C` in the terminal running the server.

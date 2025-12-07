#!/usr/bin/env python3
"""
AURA Python Bridge v3.0 (USB-Smart Port Detection)
--------------------------------------------------

Auto-detects REAL ESP32 USB ports only (ignores Bluetooth COM ports).
Handles session events, uploads to Django, and sends CLEAR_SESSION.
"""

import sys
import time
import json
import threading
from typing import Dict, List

import serial
import serial.tools.list_ports
import requests


# =========================
# CONFIG
# =========================

SERIAL_PORT = None     # leave None → auto USB detection
BAUD_RATE = 115200

DJANGO_BASE_URL = "http://127.0.0.1:8000"
SESSION_UPLOAD_PATH = "/api/iot/session/upload/"

API_TOKEN = None
DEVICE_ID = "CLASSROOM-1"
RETRY_DELAY = 10


# =========================
# SMART USB PORT AUTO-DETECTOR
# =========================

def select_esp32_usb_port() -> str:
    """Selects only USB ports that look like ESP32 devices."""

    ESP_KEYWORDS = ["usb", "esp", "wroom", "s3", "uart", "cp210", "ch910", "serial"]

    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("[ERROR] No serial ports found.")
        sys.exit(1)

    print("Available serial ports:")
    for p in ports:
        print(f"  - {p.device} ({p.description})")

    usb_candidates = []

    for p in ports:
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()

        # AVOID Bluetooth virtual COMs completely
        if "bluetooth" in desc:
            continue

        # Match ESP32 style USB ports
        if any(k in desc for k in ESP_KEYWORDS) or any(k in hwid for k in ESP_KEYWORDS):
            usb_candidates.append(p)

    if usb_candidates:
        best = usb_candidates[0]
        print(f"[INFO] Auto-selected ESP32 USB port: {best.device} ({best.description})")
        return best.device

    # Fallback to manual
    print("\n[WARN] No ESP32 USB ports detected.")
    for i, p in enumerate(ports):
        print(f"{i+1}. {p.device} ({p.description})")

    choice = int(input("Select port number: "))
    return ports[choice - 1].device


# =========================
# SESSION STORAGE
# =========================

sessions: Dict[int, List[dict]] = {}
pending_sessions: Dict[int, List[dict]] = {}
sessions_lock = threading.Lock()


def add_event(event: dict):
    sid = int(event.get("session_id", 0))
    if sid not in sessions:
        sessions[sid] = []
    sessions[sid].append(event)
    print(f"[SESS] Added event to session {sid}: {event.get('type')} {event.get('uid')}")


def build_session_payload(session_id: int) -> dict:
    with sessions_lock:
        return {
            "device_id": DEVICE_ID,
            "session_id": session_id,
            "events": sessions.get(session_id, []),
        }


# =========================
# DJANGO UPLOAD
# =========================

def get_headers():
    h = {"Content-Type": "application/json"}
    if API_TOKEN:
        h["Authorization"] = f"Token {API_TOKEN}"
    return h


def upload_session_to_django(session_id: int, ser: serial.Serial) -> bool:
    payload = build_session_payload(session_id)
    if not payload["events"]:
        print(f"[UPLOAD] Session {session_id} empty → skipping")
        return True

    url = DJANGO_BASE_URL.rstrip("/") + SESSION_UPLOAD_PATH
    print(f"[UPLOAD] POST Session {session_id} → {url}")

    try:
        resp = requests.post(url, json=payload, headers=get_headers(), timeout=10)
    except Exception as e:
        print(f"[ERROR] Django upload error: {e}")
        return False

    if resp.status_code >= 200 and resp.status_code < 300:
        print(f"[UPLOAD] Session {session_id} uploaded OK")

        # Tell gateway to clear
        cmd = f"CLEAR_SESSION {session_id}\n"
        try:
            ser.write(cmd.encode())
            print(f"[GATEWAY] Sent {cmd.strip()}")
        except Exception as e:
            print(f"[WARN] Failed CLEAR_SESSION send: {e}")

        with sessions_lock:
            sessions.pop(session_id, None)
            pending_sessions.pop(session_id, None)

        return True

    print(f"[ERROR] Django rejected upload {resp.status_code}: {resp.text}")
    return False


def mark_session_pending(session_id: int):
    with sessions_lock:
        pending_sessions[session_id] = sessions.get(session_id, []).copy()
    print(f"[PENDING] Session {session_id} saved for retry.")


def retry_pending_sessions(ser: serial.Serial):
    with sessions_lock:
        retry_list = list(pending_sessions.keys())

    for sid in retry_list:
        print(f"[RETRY] Retrying session {sid}...")
        if upload_session_to_django(sid, ser):
            print("[RETRY] Success")
        else:
            print("[RETRY] Still failed")


# =========================
# SERIAL READER
# =========================

def parse_rx_line(line: str):
    if not line.startswith("[RX] "):
        return None
    try:
        return json.loads(line[5:].strip())
    except:
        print(f"[ERROR] Bad JSON: {line}")
        return None


def main_loop(ser: serial.Serial):
    print("[BRIDGE] Listening for NRF events...")

    last_retry = time.time()

    while True:
        # Retry logic
        if time.time() - last_retry > RETRY_DELAY and pending_sessions:
            retry_pending_sessions(ser)
            last_retry = time.time()

        if ser.in_waiting == 0:
            time.sleep(0.01)
            continue

        try:
            line = ser.readline().decode(errors="ignore").strip()
        except Exception as e:
            print(f"[ERROR] Serial read failed: {e}")
            time.sleep(1)
            continue

        if not line:
            continue

        print(f"[SER] {line}")

        event = parse_rx_line(line)
        if not event:
            continue

        add_event(event)

        if event.get("type") == "session_end":
            sid = int(event.get("session_id", 0))
            print(f"[SESS] SESSION_END → Uploading {sid}")
            if not upload_session_to_django(sid, ser):
                mark_session_pending(sid)


# =========================
# ENTRY POINT
# =========================

def open_serial():
    port = SERIAL_PORT or select_esp32_usb_port()
    print(f"[INFO] Opening {port} @ {BAUD_RATE}")
    ser = serial.Serial(port, BAUD_RATE, timeout=1)
    time.sleep(2)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    return ser


def main():
    print("=== AURA Python Bridge v3.0 ===")
    print(f"Using Django: {DJANGO_BASE_URL}")

    ser = open_serial()

    try:
        main_loop(ser)
    except KeyboardInterrupt:
        print("\n[BRIDGE] Exiting...")
    except Exception as e:
        print(f"[FATAL] {e}")
    finally:
        try:
            ser.close()
        except:
            pass


if __name__ == "__main__":
    main()

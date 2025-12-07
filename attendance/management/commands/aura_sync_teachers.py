from django.core.management.base import BaseCommand
from attendance.models import TeacherProfile
import serial
import serial.tools.list_ports
import json
import time

class Command(BaseCommand):
    help = "Sync teacher NFC UIDs to ESP32-S3 over USB"

    def handle(self, *args, **kwargs):
        print("=== AURA Teacher Sync ===")

        # find ESP32 usb
        ports = serial.tools.list_ports.comports()
        esp_port = None
        for p in ports:
            if ("USB Serial" in p.description) or ("CH910" in p.description) or ("CP210" in p.description):
                esp_port = p.device
                break

        if not esp_port:
            print("[ERROR] ESP32-S3 USB not found.")
            return

        print(f"[INFO] Using port: {esp_port}")

        # gather UIDs
        teachers = TeacherProfile.objects.exclude(nfc_uid__isnull=True).exclude(nfc_uid__exact="")
        uid_list = [t.nfc_uid.strip() for t in teachers]

        print(f"[INFO] {len(uid_list)} teachers found.")
        print(uid_list)

        # open serial
        ser = serial.Serial(esp_port, 115200, timeout=1)
        time.sleep(2)

        payload = json.dumps({"teachers": uid_list})
        cmd = f"CACHE_SET {payload}\n"



        print(f"[SEND] {cmd}")
        ser.write(cmd.encode())

        time.sleep(1)
        print(ser.read_all().decode(errors="ignore"))
        ser.close()

        print("[DONE] Teacher sync complete.")

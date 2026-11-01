"""Lê uso de CPU/RAM/disco e temperaturas num thread de fundo (a interface só lê o último valor)."""
import os
import threading
import time

import psutil

import hardware


class Sampler:
    def __init__(self):
        self.data = {"cpu": 0.0, "ram": 0.0, "disk": 0.0, "disk_free_gb": 0.0,
                     "temp_cpu": None, "temp_gpu": None}
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._tt = threading.Thread(target=self._temps, daemon=True)

    def start(self):
        self._t.start()
        self._tt.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        drive = os.environ.get("SystemDrive", "C:") + "\\" if os.name == "nt" else "/"
        psutil.cpu_percent()
        while not self._stop.is_set():
            try:
                self.data["cpu"] = psutil.cpu_percent()
                self.data["ram"] = psutil.virtual_memory().percent
                u = psutil.disk_usage(drive)
                self.data["disk"], self.data["disk_free_gb"] = u.percent, u.free / 2 ** 30
            except Exception:
                pass
            self._stop.wait(1.5)

    def _temps(self):
        while not self._stop.is_set():
            try:
                t = hardware.read_temps()
                self.data["temp_cpu"], self.data["temp_gpu"] = t["cpu"], t["gpu"]
            except Exception:
                pass
            self._stop.wait(8)

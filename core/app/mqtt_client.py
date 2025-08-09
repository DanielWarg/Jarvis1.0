from __future__ import annotations

import os
from typing import Optional

from paho.mqtt import client as mqtt


MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TLS = os.getenv("MQTT_TLS", "0") == "1"


_client: Optional[mqtt.Client] = None
_connected: bool = False


def _on_connect(client: mqtt.Client, userdata, flags, rc, properties=None):
    global _connected
    _connected = rc == 0


def get_client() -> mqtt.Client:
    global _client
    if _client is not None:
        return _client
    c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    c.on_connect = _on_connect
    if MQTT_TLS:
        c.tls_set()
    _client = c
    return _client


def ping_mqtt(timeout_sec: float = 2.0) -> bool:
    try:
        c = get_client()
        c.connect_async(MQTT_HOST, MQTT_PORT, keepalive=10)
        c.loop_start()
        # Vänta kort på connect-callback
        import time

        start = time.time()
        while time.time() - start < timeout_sec:
            if _connected:
                break
            time.sleep(0.05)
        c.loop_stop()
        try:
            c.disconnect()
        except Exception:
            pass
        return _connected
    except Exception:
        return False



"""Board readings over MQTT: the XIAO ESP32S3 Sense (in Velxio or real) publishes JSON readings to a public broker
and the backend subscribes, so the laptop never has to be reachable from the internet.

Topic: aau-hack26/rooms/<room_id>/readings   Payload: the same JSON as POST /api/readings.
Topic: aau-hack26/rooms/<room_id>/frame      Payload: an encrypted camera JPEG (app/vision.py).
Settings: MQTT_HOST (default broker.hivemq.com), MQTT_PORT (1883), MQTT_TOPIC (aau-hack26/rooms/+/readings),
MQTT_FRAME_TOPIC (aau-hack26/rooms/+/frame);
MQTT_FEED=0 turns it off (tests). The broker is public, so anyone can publish there: fine for a demo, use a private
broker with credentials for anything real.
"""

import json
import logging
import os
from collections.abc import Callable

import paho.mqtt.client as mqtt

log = logging.getLogger(__name__)


LED_TOPIC = "aau-hack26/rooms/{room}/led"
client: mqtt.Client | None = None


def led(room_id: str, sos: bool) -> None:
    """Board LED: "sos" blinks it (open emergency on the room display), "off" stops. Retained, so a board that
    (re)connects gets the current state at once."""
    if client is not None:
        client.publish(LED_TOPIC.format(room=room_id), "sos" if sos else "off", qos=1, retain=True)


def start(handle: Callable[[dict], None], frame: Callable[[str, bytes], None] | None = None) -> mqtt.Client:
    host = os.environ.get("MQTT_HOST", "broker.hivemq.com")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    topic = os.environ.get("MQTT_TOPIC", "aau-hack26/rooms/+/readings")
    frame_topic = os.environ.get("MQTT_FRAME_TOPIC", "aau-hack26/rooms/+/frame")
    global client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def on_connect(c, _userdata, _flags, reason_code, _props):
        log.info("MQTT connected to %s (%s), subscribing to %s", host, reason_code, topic)
        c.subscribe(topic)
        if frame:
            c.subscribe(frame_topic)

    def on_message(_c, _userdata, msg):
        if msg.retain:
            return  # A replay on subscription is not a new heartbeat.
        if frame and mqtt.topic_matches_sub(frame_topic, msg.topic):
            frame(msg.topic.split("/")[-2], msg.payload)
            return
        try:
            data = json.loads(msg.payload)
            if isinstance(data, dict):
                handle(data)
        except Exception:  # a bad message must never stop the subscriber
            log.exception("MQTT reading on %s rejected", msg.topic)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(host, port, keepalive=30)
    client.loop_start()   # background thread, reconnects on its own
    return client

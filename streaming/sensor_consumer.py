"""Kafka consumer for real-time factory sensor data.

Consumes temperature, pressure, and humidity readings from
production line sensors. Writes to SQLite for dashboard
consumption and triggers alerts on threshold breaches.

Requires: pip install confluent-kafka

Usage:
    python streaming/sensor_consumer.py

Environment:
    KAFKA_BOOTSTRAP_SERVERS: Kafka broker address (default: localhost:9092)
    KAFKA_TOPIC: Topic to consume (default: factory.sensors)
    KAFKA_GROUP_ID: Consumer group (default: opsmind-sensors)
"""

import json
import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "sensor_data.db"

THRESHOLDS = {
    "temperature": {"min": -5.0, "max": 8.0},
    "pressure": {"min": 0.5, "max": 4.0},
    "humidity": {"min": 20.0, "max": 80.0},
}


def init_db(db_path: Path = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT NOT NULL,
            location TEXT NOT NULL,
            reading_type TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT,
            timestamp TEXT NOT NULL,
            is_alert BOOLEAN DEFAULT FALSE,
            ingested_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT NOT NULL,
            location TEXT NOT NULL,
            reading_type TEXT NOT NULL,
            value REAL NOT NULL,
            threshold_min REAL,
            threshold_max REAL,
            alert_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            acknowledged BOOLEAN DEFAULT FALSE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_ts ON sensor_readings(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_location ON sensor_readings(location)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(timestamp)")
    conn.commit()
    conn.close()


def check_threshold(reading_type: str, value: float) -> Optional[str]:
    if reading_type not in THRESHOLDS:
        return None
    bounds = THRESHOLDS[reading_type]
    if value < bounds["min"]:
        return "BELOW_MIN"
    if value > bounds["max"]:
        return "ABOVE_MAX"
    return None


def process_message(msg_value: bytes, db_path: Path = DB_PATH) -> dict:
    data = json.loads(msg_value)
    sensor_id = data["sensor_id"]
    location = data["location"]
    reading_type = data["reading_type"]
    value = float(data["value"])
    unit = data.get("unit", "")
    timestamp = data.get("timestamp", datetime.utcnow().isoformat())

    alert_type = check_threshold(reading_type, value)
    is_alert = alert_type is not None

    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO sensor_readings
           (sensor_id, location, reading_type, value, unit, timestamp, is_alert)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (sensor_id, location, reading_type, value, unit, timestamp, is_alert),
    )

    if is_alert:
        bounds = THRESHOLDS[reading_type]
        conn.execute(
            """INSERT INTO alerts
               (sensor_id, location, reading_type, value,
                threshold_min, threshold_max, alert_type, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sensor_id, location, reading_type, value,
             bounds["min"], bounds["max"], alert_type, timestamp),
        )
        logger.warning(
            f"ALERT: {reading_type} {alert_type} at {location} "
            f"(value={value}, bounds={bounds})"
        )

    conn.commit()
    conn.close()

    return {"sensor_id": sensor_id, "value": value, "alert": alert_type}


def run_consumer() -> None:
    try:
        from confluent_kafka import Consumer, KafkaError
    except ImportError:
        raise ImportError("Kafka support requires: pip install confluent-kafka")

    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.environ.get("KAFKA_TOPIC", "factory.sensors")
    group_id = os.environ.get("KAFKA_GROUP_ID", "opsmind-sensors")

    init_db()

    consumer = Consumer({
        "bootstrap.servers": bootstrap,
        "group.id": group_id,
        "auto.offset.reset": "latest",
        "enable.auto.commit": True,
    })
    consumer.subscribe([topic])

    logger.info(f"Consuming from {topic} at {bootstrap}")
    msg_count = 0

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error(f"Consumer error: {msg.error()}")
                continue

            result = process_message(msg.value())
            msg_count += 1
            if msg_count % 100 == 0:
                logger.info(f"Processed {msg_count} messages")

    except KeyboardInterrupt:
        logger.info(f"Shutting down. Processed {msg_count} messages total.")
    finally:
        consumer.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_consumer()

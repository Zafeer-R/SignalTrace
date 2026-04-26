"""Central configuration for the real-time entity pipeline."""

import os


KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
FETCH_INTERVAL_SEC = int(os.getenv("FETCH_INTERVAL_SEC", "10"))
WINDOW_DURATION = os.getenv("WINDOW_DURATION", "2 minutes")
SLIDE_DURATION = os.getenv("SLIDE_DURATION", "1 minute")
TOP_N_ENTITIES = int(os.getenv("TOP_N_ENTITIES", "10"))
NER_MODEL = os.getenv("NER_MODEL", "en_core_web_sm")

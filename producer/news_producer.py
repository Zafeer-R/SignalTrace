"""Fetch financial news and publish normalized article events to Kafka."""

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from kafka import KafkaProducer

# Allow `python producer/news_producer.py` to import repo-root modules.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import FETCH_INTERVAL_SEC, KAFKA_BOOTSTRAP


RAW_ARTICLES_TOPIC = "raw-articles"
FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/news"
REQUEST_TIMEOUT_SEC = 15


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger(__name__)


def load_api_key() -> str:
    """Return the configured Finnhub API key or fail fast."""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise RuntimeError("FINNHUB_API_KEY is required in the environment or .env file.")
    return api_key


def build_producer() -> KafkaProducer:
    """Create a JSON-serializing Kafka producer."""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
    )


def fetch_news(api_key: str) -> list[dict]:
    """Fetch the latest general-news batch from Finnhub."""
    response = requests.get(
        FINNHUB_NEWS_URL,
        params={"category": "general", "token": api_key},
        timeout=REQUEST_TIMEOUT_SEC,
    )
    response.raise_for_status()

    articles = response.json()
    if not isinstance(articles, list):
        raise ValueError("Finnhub response was not a list of articles.")
    return articles


def normalize_article(article: dict) -> dict | None:
    """Map a Finnhub article into the repo's raw-article event contract."""
    headline = (article.get("headline") or "").strip()
    url = (article.get("url") or "").strip()
    if not headline or not url:
        return None

    return {
        "event_id": str(uuid.uuid4()),
        "source": "finnhub",
        # Spark parses this exact UTC wire format downstream, so keep the
        # producer timestamp stable and timezone-explicit.
        "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "headline": headline,
        "body": article.get("summary") or None,
        "url": url,
        "category": (article.get("category") or "general").strip() or "general",
    }


def publish_articles(producer: KafkaProducer, articles: list[dict]) -> int:
    """Normalize and publish articles, waiting for broker acknowledgement."""
    published_count = 0
    for article in articles:
        event = normalize_article(article)
        if event is None:
            LOGGER.warning("Skipping article missing required headline/url fields: %s", article)
            continue

        # Wait for broker acknowledgement so a successful log line means the
        # event really reached Kafka, not just the client buffer.
        producer.send(RAW_ARTICLES_TOPIC, event).get(timeout=10)
        published_count += 1

    if published_count:
        producer.flush()
    return published_count


def main() -> None:
    """Run the polling loop indefinitely."""
    load_dotenv()
    api_key = load_api_key()
    producer = build_producer()

    LOGGER.info(
        "Starting news producer for topic '%s' with bootstrap server '%s' and interval %s seconds.",
        RAW_ARTICLES_TOPIC,
        KAFKA_BOOTSTRAP,
        FETCH_INTERVAL_SEC,
    )

    while True:
        try:
            articles = fetch_news(api_key)
            published_count = publish_articles(producer, articles)
            LOGGER.info("Fetched %s articles and published %s events.", len(articles), published_count)
        except requests.RequestException as exc:
            LOGGER.exception("News API request failed; retrying after sleep: %s", exc)
        except Exception as exc:
            LOGGER.exception("Producer loop failed; retrying after sleep: %s", exc)

        time.sleep(FETCH_INTERVAL_SEC)


if __name__ == "__main__":
    main()

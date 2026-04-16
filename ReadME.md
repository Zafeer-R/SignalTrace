# Real-Time Entity Intelligence Pipeline

A production-style streaming pipeline that ingests live financial news, extracts named entities using NLP, tracks their mention frequency in real-time, and surfaces insights through a live Kibana dashboard — all orchestrated across Kafka, PySpark Structured Streaming, and the Elastic Stack.

> Built to explore event-driven architecture patterns: durable event schemas, multi-topic routing, stateful stream processing, and real-time visualization.

---

## What This Does

Every article published to a financial news feed becomes an event. That event flows through a pipeline that:

1. **Ingests** live text from Finnhub / NewsAPI via a Python producer
2. **Publishes** raw article payloads as structured events to Kafka (`raw-articles`)
3. **Processes** each event in PySpark Structured Streaming — NER extraction, entity normalization, running counts
4. **Emits** enriched entity-frequency events downstream to a second Kafka topic (`entity-counts`)
5. **Indexes** events into Elasticsearch via Logstash
6. **Visualizes** the top 10 trending entities live in Kibana

The pipeline is always on. There is no batch job, no cron trigger, no manual refresh.

---

## Architecture

```
[Finnhub / NewsAPI]
        |
        v
[Python Producer] ──── Kafka Topic: raw-articles ────> [PySpark Structured Streaming]
                                                                  |
                                                         NER (spaCy / Flair)
                                                         Entity normalization
                                                         Running window counts
                                                                  |
                                                                  v
                                              Kafka Topic: entity-counts
                                                                  |
                                                                  v
                                                    [Logstash] ──> [Elasticsearch]
                                                                          |
                                                                          v
                                                                    [Kibana Dashboard]
                                                                    Top 10 Entities
                                                                    Live Bar Chart
```

**Design decisions worth noting:**

- Two-topic separation (`raw-articles` / `entity-counts`) keeps ingestion decoupled from processing. If the Spark job goes down, raw events are retained in Kafka and can be replayed from offset.
- Spark's stateful aggregation uses a sliding window (configurable) so entity counts reflect a rolling time horizon, not a forever-accumulating global count.
- Event schemas are explicit and versioned — both topics have defined field contracts documented below.

---

## Event Schemas

### `raw-articles` (Producer → Kafka)

```json
{
  "event_id": "uuid-v4",
  "source": "finnhub | newsapi",
  "fetched_at": "ISO-8601 timestamp",
  "headline": "string",
  "body": "string | null",
  "url": "string",
  "category": "string"
}
```

### `entity-counts` (Spark → Kafka)

```json
{
  "window_start": "ISO-8601 timestamp",
  "window_end": "ISO-8601 timestamp",
  "entity": "string",
  "entity_type": "ORG | PERSON | GPE | PRODUCT",
  "count": "integer",
  "trigger_at": "ISO-8601 timestamp"
}
```

Explicit schemas are the foundation of reliable event-driven systems. Downstream consumers (Logstash, future services) depend on field contracts, not assumptions.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data Source | Finnhub API / NewsAPI |
| Message Broker | Apache Kafka |
| Stream Processor | PySpark Structured Streaming |
| NLP / NER | spaCy (`en_core_web_sm`) |
| Indexing | Logstash |
| Search / Storage | Elasticsearch |
| Visualization | Kibana |
| Containerization | Docker Compose |
| Language | Python 3.10+ |

---

## Quickstart

### Prerequisites

- Docker and Docker Compose installed
- Python 3.10+
- A free Finnhub API key: [finnhub.io](https://finnhub.io) (or NewsAPI: [newsapi.org](https://newsapi.org))

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/entity-intelligence-pipeline.git
cd entity-intelligence-pipeline
```

### 2. Set environment variables

```bash
cp .env.example .env
# Edit .env and add your FINNHUB_API_KEY or NEWSAPI_KEY
```

### 3. Spin up the infrastructure

```bash
docker-compose up -d
```

This starts Zookeeper, Kafka, Elasticsearch, Logstash, and Kibana. Wait ~30 seconds for Kafka to be ready.

### 4. Create Kafka topics

```bash
docker exec -it kafka kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic raw-articles \
  --partitions 3 \
  --replication-factor 1

docker exec -it kafka kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic entity-counts \
  --partitions 3 \
  --replication-factor 1
```

### 5. Install Python dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 6. Start the producer

```bash
python producer/news_producer.py
```

The producer will begin publishing article events to `raw-articles` every few seconds.

### 7. Start the Spark streaming job

```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  spark/entity_stream.py
```

The Spark job will begin consuming from `raw-articles`, extracting entities, and publishing aggregated counts to `entity-counts`.

### 8. Open Kibana

Navigate to [http://localhost:5601](http://localhost:5601).

- Go to **Index Management** and verify `entity-counts-*` is being indexed
- Open **Discover** to inspect raw event documents
- Import the dashboard from `kibana/dashboard_export.ndjson` for the pre-built Top 10 Entities bar chart

---

## Project Structure

```
entity-intelligence-pipeline/
├── producer/
│   └── news_producer.py        # Fetches live articles, publishes to raw-articles topic
├── spark/
│   └── entity_stream.py        # PySpark job: NER extraction + windowed entity counts
├── logstash/
│   └── pipeline.conf           # Logstash config: Kafka → Elasticsearch
├── kibana/
│   └── dashboard_export.ndjson # Pre-built Kibana dashboard (importable)
├── schemas/
│   ├── raw_article.json        # Event schema: raw-articles topic
│   └── entity_count.json       # Event schema: entity-counts topic
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Configuration

All tuneable parameters live in `config.py` or `.env`:

| Parameter | Default | Description |
|---|---|---|
| `KAFKA_BOOTSTRAP` | `localhost:9092` | Kafka broker address |
| `FETCH_INTERVAL_SEC` | `10` | How often the producer polls the news API |
| `WINDOW_DURATION` | `5 minutes` | Spark sliding window for entity counts |
| `SLIDE_DURATION` | `1 minute` | Slide interval for the window |
| `TOP_N_ENTITIES` | `10` | Number of entities surfaced in Kibana |
| `NER_MODEL` | `en_core_web_sm` | spaCy model used for extraction |

---

## Kafka Offset Management and Replay

One of the more interesting properties of this architecture: because raw article events are persisted in Kafka (retention configurable), the Spark job can be restarted at any offset without data loss. To replay from the beginning:

```python
# In entity_stream.py, change:
.option("startingOffsets", "latest")
# to:
.option("startingOffsets", "earliest")
```

This is the property that makes event-driven pipelines more resilient than direct API → DB writes.

---

## What I'd Extend Next

- **Dead letter queue**: Route malformed events to a `raw-articles-dlq` topic instead of dropping them, with a consumer that alerts on parse failures
- **Schema registry**: Use Confluent Schema Registry to enforce `entity-counts` field contracts at the broker level, not just by convention
- **Graph layer**: Push `entity-counts` events into a Neo4j graph to model co-occurrence relationships between entities — which companies get mentioned together, in what context, over what time windows
- **Backpressure handling**: Currently the producer doesn't throttle against Kafka lag; adding a lag monitor that slows fetch rate under consumer backpressure would make this more production-realistic

---

## Background

This project was built to develop hands-on intuition for event-driven systems: how events flow, how schemas become contracts between services, and how stateful stream processing differs from batch aggregation. The two-topic pattern, explicit schemas, and replay semantics are all patterns that appear in production data infrastructure — not just streaming tutorials.

---

## References

- [Kafka Quickstart](https://kafka.apache.org/quickstart)
- [PySpark Structured Streaming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [spaCy NER Documentation](https://spacy.io/usage/linguistic-features#named-entities)
- [Elastic Stack Downloads](https://www.elastic.co/downloads)
- [Finnhub Python SDK](https://pypi.org/project/finnhub-python/)
# Real-Time Entity Intelligence Pipeline

A streaming pipeline that ingests live financial news, extracts named entities, tracks mention frequency in near real time, and surfaces the result in Kibana.

> Built to practice event-driven design: explicit schemas, Kafka topic boundaries, stateful stream processing, replayability, and dashboard delivery.

---

## What This Does

Each fetched article becomes an event that moves through this path:

1. A Python producer fetches live news from Finnhub
2. The producer publishes normalized article events to Kafka topic `raw-articles`
3. A PySpark Structured Streaming job reads `raw-articles`
4. Spark extracts named entities with spaCy and computes rolling counts
5. Spark publishes aggregated entity-count events to Kafka topic `entity-counts`
6. Logstash reads `entity-counts` and indexes the events into Elasticsearch
7. Kibana visualizes the top 10 most-mentioned entities in a reusable dashboard

---

## Architecture

```text
[Finnhub]
    |
    v
[Python Producer] --> Kafka topic: raw-articles --> [PySpark Structured Streaming]
                                                       |
                                                       v
                                             Kafka topic: entity-counts
                                                       |
                                                       v
                                                  [Logstash]
                                                       |
                                                       v
                                                [Elasticsearch]
                                                       |
                                                       v
                                             [Kibana Dashboard]
```

### Why two Kafka topics?

- `raw-articles` is the durable ingestion topic
- `entity-counts` is the downstream analytics topic

This separation keeps ingestion decoupled from processing. If Spark stops, the producer can still publish raw events. When Spark comes back, it can replay from Kafka offsets instead of re-calling the news API.

---

## Event Schemas

### `raw-articles`

```json
{
  "event_id": "uuid-v4",
  "source": "finnhub",
  "fetched_at": "ISO-8601 UTC timestamp",
  "headline": "string",
  "body": "string | null",
  "url": "string",
  "category": "string"
}
```

### `entity-counts`

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

The canonical schema files live in:

- `schemas/raw_article.json`
- `schemas/entity_count.json`

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data Source | Finnhub API |
| Broker | Apache Kafka |
| Stream Processing | PySpark Structured Streaming 4.1.1 |
| NLP | spaCy `en_core_web_sm` |
| Indexing | Logstash |
| Storage / Search | Elasticsearch 7.10.1 |
| Visualization | Kibana 7.10.1 |
| Orchestration | Docker Compose |
| Python Runtime | Python 3.10+ |

---

## Working Development Setup

This repo currently works best with a split local setup:

- Docker Desktop on Windows for infrastructure
  - Zookeeper
  - Kafka
  - Elasticsearch
  - Kibana
  - Logstash
- WSL2 Ubuntu for Python execution
  - `producer/news_producer.py`
  - `spark/entity_stream.py`

This avoids the native Windows Spark/Hadoop filesystem problems encountered during development.

---

## Quickstart

### Prerequisites

- Docker Desktop
- WSL2 with Ubuntu
- Python 3 installed in WSL
- Java 17 installed in WSL
- A Finnhub API key

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/Message-Analysis-RealTime.git
cd Message-Analysis-RealTime
```

### 2. Create the environment file

On Windows or WSL:

```bash
cp .env.example .env
```

Edit `.env` and set:

```text
FINNHUB_API_KEY=your_real_key
```

### 3. Start Docker services on Windows

From PowerShell in the repo root:

```powershell
docker-compose up -d zookeeper
docker-compose up -d kafka
docker-compose up -d elasticsearch
docker-compose up -d kibana
docker-compose up -d logstash
```

### 4. Create Kafka topics

From PowerShell:

```powershell
docker exec -it kafka kafka-topics.sh --create --bootstrap-server localhost:9092 --topic raw-articles --partitions 3 --replication-factor 1
docker exec -it kafka kafka-topics.sh --create --bootstrap-server localhost:9092 --topic entity-counts --partitions 3 --replication-factor 1
```

If the topics already exist, Kafka will report that and you can continue.

### 5. Set up Python in WSL

From Ubuntu:

```bash
cd /mnt/d/Message-Analysis-RealTime
python3 -m venv .venv-wsl
source .venv-wsl/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 6. Start the producer in WSL

Terminal 1:

```bash
cd /mnt/d/Message-Analysis-RealTime
source .venv-wsl/bin/activate
python producer/news_producer.py
```

### 7. Start the Spark stream in WSL

Terminal 2:

```bash
cd /mnt/d/Message-Analysis-RealTime
source .venv-wsl/bin/activate
python spark/entity_stream.py
```

If restartability fails after a previous bad run, clear the streaming checkpoint first:

```bash
rm -rf /mnt/d/Message-Analysis-RealTime/spark/checkpoints/entity_stream
```

### 8. Verify Kafka flow

From PowerShell:

```powershell
docker exec -it kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic raw-articles --from-beginning
docker exec -it kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic entity-counts --from-beginning
```

### 9. Open Kibana

Open:

- `http://localhost:5601`

Then:

- create or select the `entity-counts-*` data view if needed
- go to Discover to confirm documents exist
- import `kibana/dashboard_export.ndjson` if the dashboard is not already present
- open the `Entity Intelligence - Live` dashboard

For a post-reboot service startup checklist, see:

- `afterRestartInstructions.md`

---

## Project Structure

```text
Message-Analysis-RealTime/
|-- producer/
|   `-- news_producer.py
|-- spark/
|   |-- entity_stream.py
|   |-- checkpoints/
|   `-- logs/
|-- logstash/
|   `-- pipeline.conf
|-- kibana/
|   `-- dashboard_export.ndjson
|-- schemas/
|   |-- raw_article.json
|   `-- entity_count.json
|-- scripts/
|   `-- validate_phase1.ps1
|-- context/
|   `-- project_context.md
|-- docker-compose.yml
|-- config.py
|-- requirements.txt
|-- .env.example
`-- ReadME.md
```

---

## Configuration

Primary tuneable parameters live in `config.py` or `.env`.

| Parameter | Default | Description |
|---|---|---|
| `KAFKA_BOOTSTRAP` | `localhost:9092` | Host/WSL Kafka bootstrap address |
| `FETCH_INTERVAL_SEC` | `10` | Producer poll interval |
| `WINDOW_DURATION` | `2 minutes` | Rolling Spark aggregation window |
| `SLIDE_DURATION` | `1 minute` | Spark window slide interval |
| `TOP_N_ENTITIES` | `10` | Target number of entities surfaced in Kibana |
| `NER_MODEL` | `en_core_web_sm` | spaCy model used for extraction |

---

## Replay and Offsets

The Spark stream currently reads Kafka with:

```python
.option("startingOffsets", "latest")
```

To replay from the beginning for debugging, change it to:

```python
.option("startingOffsets", "earliest")
```

Because the pipeline keeps raw events in Kafka, Spark can be restarted and re-run from offsets without re-fetching the original articles.

---

## Known Local Caveat

The Phase 5 stream is functionally complete, but local checkpoint reuse is not yet fully hardened. If the stream fails after an interrupted run, deleting:

```text
spark/checkpoints/entity_stream
```

may be required before restarting.

---

## What I'd Extend Next

- Add a dead-letter topic for malformed raw article events
- Add schema validation before producer publish
- Add a graph layer for entity co-occurrence
- Add Kafka lag / backpressure monitoring

---

## References

- [Kafka Quickstart](https://kafka.apache.org/quickstart)
- [PySpark Structured Streaming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [spaCy Named Entity Recognition](https://spacy.io/usage/linguistic-features#named-entities)
- [Elastic Stack Downloads](https://www.elastic.co/downloads)
- [Finnhub API](https://finnhub.io)

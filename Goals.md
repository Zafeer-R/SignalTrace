# Build Plan for Real-Time Entity Intelligence Pipeline

This file tracks every deliverable needed to make the README fully honest.
Work top to bottom. Do not skip ahead — each phase depends on the one before it.
Mark tasks `[x]` as you complete them.

---

## Phase 1 — Repo Skeleton and Infrastructure

Goal: `docker-compose up -d` works end to end before writing a single line of application code.

- [x] Initialize git repo, create `main` branch
- [x] Create folder structure exactly as documented in README: [mkdir producer, spark ..]
  ```
  producer/
  spark/
  logstash/
  kibana/
  schemas/
  ```
- [x] Write `docker-compose.yml` with the following services: [ni docker-compose.yml -ItemType File]
  - Zookeeper
  - Kafka (broker)
  - Elasticsearch
  - Logstash
  - Kibana
- [x] Create a placeholder `logstash/pipeline.conf` so the Logstash volume mount in `docker-compose.yml` points to a real file before startup
- [x] Verify all 5 services start cleanly with `docker-compose up -d`
- [x] Verify Kibana is reachable at `http://localhost:5601`
- [x] Create `.env.example` with placeholder keys:
  ```
  FINNHUB_API_KEY=your_key_here
  NEWSAPI_KEY=your_key_here
  KAFKA_BOOTSTRAP=localhost:9092
  ```
- [x] Create `requirements.txt` with initial dependencies:
  - `kafka-python`
  - `requests`
  - `pyspark`
  - `spacy`
  - `python-dotenv`
  - `uuid`
- [x] Create and activate a virtual environment for local Python development before installing dependencies
- [x] Confirm venv creation, `pip install -r requirements.txt`, and `python -m spacy download en_core_web_sm` run without errors

**Checkpoint:** Infrastructure is running. No application code exists yet, but the environment is ready.

---

## Phase 2 — Event Schemas

Goal: Schema files exist and are the source of truth for field names used everywhere else.

- [x] Create `schemas/raw_article.json`:
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
- [x] Create `schemas/entity_count.json`:
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
- [x] Write `config.py` in repo root with all configurable parameters:
  - `KAFKA_BOOTSTRAP`
  - `FETCH_INTERVAL_SEC` (default: 10)
  - `WINDOW_DURATION` (default: "5 minutes")
  - `SLIDE_DURATION` (default: "1 minute")
  - `TOP_N_ENTITIES` (default: 10)
  - `NER_MODEL` (default: "en_core_web_sm")

**Checkpoint:** Schema files are committed. Any future field name change starts here, not in the code.

---

## Phase 3 — Kafka Topics

Goal: Both topics exist in the running Kafka broker with correct partition counts.

- [ ] Create `raw-articles` topic (3 partitions, replication-factor 1):
  ```bash
  docker exec -it kafka kafka-topics.sh --create \
    --bootstrap-server localhost:9092 \
    --topic raw-articles \
    --partitions 3 \
    --replication-factor 1
  ```
- [ ] Create `entity-counts` topic (3 partitions, replication-factor 1):
  ```bash
  docker exec -it kafka kafka-topics.sh --create \
    --bootstrap-server localhost:9092 \
    --topic entity-counts \
    --partitions 3 \
    --replication-factor 1
  ```
- [ ] Verify both topics exist:
  ```bash
  docker exec -it kafka kafka-topics.sh --list --bootstrap-server localhost:9092
  ```

**Checkpoint:** Two topics are live. Producer and consumer can now be built independently.

---

## Phase 4 — Python Producer

Goal: `producer/news_producer.py` runs, fetches real articles, and publishes valid `raw-articles` events to Kafka continuously.

- [ ] Implement Finnhub or NewsAPI client (pick one, get API key from `.env`)
- [ ] Write fetch loop that polls every `FETCH_INTERVAL_SEC` seconds
- [ ] For each article, construct a JSON payload matching `schemas/raw_article.json` exactly:
  - Generate `event_id` with `uuid.uuid4()`
  - Set `fetched_at` to current UTC ISO-8601 timestamp
  - Map API response fields to schema fields
- [ ] Serialize payload to JSON and publish to `raw-articles` topic using `kafka-python`
- [ ] Add basic error handling: API failures should log and retry, not crash the loop
- [ ] Smoke test: run the producer for 60 seconds, then consume from `raw-articles` manually to confirm events are flowing:
  ```bash
  docker exec -it kafka kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic raw-articles \
    --from-beginning
  ```

**Checkpoint:** Real article events are accumulating in `raw-articles`. Events match the schema.

---

## Phase 5 — PySpark Structured Streaming Job

Goal: `spark/entity_stream.py` reads from `raw-articles`, extracts named entities, aggregates counts over a sliding window, and writes enriched events to `entity-counts`.

- [ ] Set up Spark session with Kafka package:
  ```
  org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0
  ```
- [ ] Read stream from `raw-articles` topic using `readStream`
- [ ] Deserialize JSON payloads — define a schema matching `schemas/raw_article.json`
- [ ] Extract `headline` and `body` fields for NER processing
- [ ] Apply spaCy NER (`en_core_web_sm`) via a Pandas UDF or `mapInPandas`:
  - Extract entities of types: `ORG`, `PERSON`, `GPE`, `PRODUCT`
  - Normalize entity text (strip whitespace, title-case)
  - Explode: one row per entity per article
- [ ] Apply sliding window aggregation:
  - Window on `fetched_at` timestamp
  - `WINDOW_DURATION` = 5 minutes, `SLIDE_DURATION` = 1 minute
  - Group by `(window, entity, entity_type)`, count occurrences
- [ ] At each trigger, serialize output rows to JSON matching `schemas/entity_count.json`
- [ ] Write stream to `entity-counts` topic using `writeStream`
- [ ] Set `startingOffsets` to `"latest"` by default (document how to change to `"earliest"` for replay)
- [ ] Smoke test: with producer running, start Spark job and consume from `entity-counts` manually:
  ```bash
  docker exec -it kafka kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic entity-counts \
    --from-beginning
  ```

**Checkpoint:** `entity-counts` is receiving windowed entity frequency events. Counts update every minute.

---

## Phase 6 — Logstash → Elasticsearch

Goal: Events from `entity-counts` are indexed into Elasticsearch automatically via Logstash.

- [ ] Write `logstash/pipeline.conf`:
  - Input: Kafka consumer reading from `entity-counts`
  - Filter: Parse JSON payload, map fields
  - Output: Elasticsearch index `entity-counts-%{+YYYY.MM.dd}`
- [ ] Mount `logstash/pipeline.conf` into the Logstash container via `docker-compose.yml`
- [ ] Verify Logstash is loading only the intended project pipeline config and not the image's default Beats pipeline
- [ ] Restart Logstash and verify pipeline starts without errors:
  ```bash
  docker logs logstash
  ```
- [ ] In Kibana → Index Management, confirm `entity-counts-*` index exists and documents are appearing
- [ ] In Kibana → Discover, inspect a few documents and confirm all fields from `schemas/entity_count.json` are present

**Checkpoint:** Events flow end to end: NewsAPI → Kafka → Spark → Kafka → Logstash → Elasticsearch.

---

## Phase 7 — Kibana Dashboard

Goal: A pre-built, importable dashboard exists showing the top 10 most-mentioned entities in a live bar chart.

- [ ] In Kibana, create an index pattern for `entity-counts-*`
- [ ] Build a bar chart visualization:
  - X-axis: `entity` field
  - Y-axis: sum of `count`
  - Sort descending, limit to top 10
  - Set auto-refresh interval (e.g., every 30 seconds)
- [ ] Add visualization to a dashboard titled "Entity Intelligence — Live"
- [ ] Export dashboard to `kibana/dashboard_export.ndjson` via Kibana → Stack Management → Saved Objects → Export
- [ ] Commit the export file to the repo
- [ ] Verify a fresh import works: delete the dashboard, re-import from the file, confirm it renders

**Checkpoint:** Anyone who clones the repo can import the dashboard and see a live visualization within minutes.

---

## Phase 8 — Polish and GitHub Readiness

Goal: The repo is in a state where Gautham can clone it, follow the README, and have a running pipeline in under 15 minutes.

- [ ] Walk through the entire README quickstart from scratch in a clean environment — fix anything that breaks
- [ ] Confirm folder structure matches the README exactly
- [ ] Confirm all config parameters in `config.py` match the table in the README
- [ ] Add inline comments to `news_producer.py` and `entity_stream.py` explaining non-obvious decisions
- [ ] Write a short `# Why two topics?` comment block at the top of `entity_stream.py` explaining the decoupling rationale
- [ ] Ensure `.env` is in `.gitignore` and `.env.example` is committed
- [ ] Tag the release: `git tag v1.0.0`

**Checkpoint:** README is fully honest. Every claim in it is backed by working code.

---

## Phase 9 — Extensions (Post-Submission, Before Interview)

Do these only after Phase 8 is fully complete. These are the "What I'd Extend Next" items from the README — if any are built, move them out of the README extensions section and into the main architecture description.

- [ ] **Dead letter queue**: Add `raw-articles-dlq` topic; route malformed/unparseable events there instead of dropping
- [ ] **Schema enforcement**: Add basic schema validation in the producer before publishing (reject events missing required fields)
- [ ] **Graph layer**: Push `entity-counts` events into a local Neo4j instance; write a Cypher query showing entity co-occurrence within the same time window
- [ ] **Backpressure monitor**: Log Kafka consumer lag from Spark; emit a warning if lag exceeds a threshold

---

## Status Tracker

| Phase | Description | Status |
|---|---|---|
| 1 | Repo skeleton + Docker infrastructure | complete |
| 2 | Event schemas + config | Not started |
| 3 | Kafka topics | Not started |
| 4 | Python producer | Not started |
| 5 | PySpark streaming job | Not started |
| 6 | Logstash → Elasticsearch | Not started |
| 7 | Kibana dashboard | Not started |
| 8 | Polish + GitHub readiness | Not started |
| 9 | Extensions | Not started |

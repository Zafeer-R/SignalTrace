# Project Context

This file is the running project memory for work done in this repo.
Update it whenever the project state changes or when an issue/decision is worth preserving for later phases.

## Usage

- Record what was completed
- Record errors encountered and how they were resolved
- Record decisions that may affect later phases
- Record any temporary compromises that must be revisited

---

## Phase 1 Summary

Status: Complete

### Completed work

- Initialized the local Git repository and aligned work to the `main` branch
- Created the documented top-level folders:
  - `producer/`
  - `spark/`
  - `logstash/`
  - `kibana/`
  - `schemas/`
- Created `docker-compose.yml` with services for:
  - Zookeeper
  - Kafka
  - Elasticsearch
  - Logstash
  - Kibana
- Created `.env.example` with:
  - `FINNHUB_API_KEY=your_key_here`
  - `NEWSAPI_KEY=your_key_here`
  - `KAFKA_BOOTSTRAP=localhost:9092`
- Created `requirements.txt` with:
  - `kafka-python`
  - `requests`
  - `pyspark`
  - `spacy`
  - `python-dotenv`
  - `uuid`
- Created a local Python virtual environment at `.venv`
- Installed Python dependencies in `.venv`
- Downloaded the spaCy model `en_core_web_sm`
- Created `logstash/pipeline.conf` as a placeholder file
- Verified Kibana was reachable at `http://localhost:5601`
- Verified the five Phase 1 containers were intended to run through Docker Compose

### Errors encountered in Phase 1

#### 1. Git branch mismatch: `Main` vs `main`

- Local branch name casing caused pushes to go to an unintended remote branch
- Resolution: rename the local branch to lowercase `main`

#### 2. `fatal: main cannot be resolved to branch`

- Cause: no valid local `main` branch existed yet, usually because there was no initial commit or the branch name differed
- Resolution: create the initial commit and normalize the branch name to `main`

#### 3. `HEAD~1` could not be resolved

- Cause: there was only a single initial commit, so there was no parent commit to reset to
- Resolution used/discussed: remove the current HEAD ref instead of resetting to `HEAD~1`

#### 4. Docker Compose YAML environment formatting issues

- Cause: mixed YAML styles caused Compose parsing problems, especially in `environment`
- Example issue: list-of-maps syntax under `environment` instead of either:
  - mapping style: `KEY: value`
  - list-of-strings style: `- KEY=value`
- Resolution: normalize the YAML format for services such as Kibana and Zookeeper

#### 5. Kibana environment parse error

- Error seen: `services.kibana.environment.[0]: unexpected type map[string]interface {}`
- Cause: Kibana `environment` was written as a list item containing a YAML map
- Resolution: rewrite as a proper mapping or `KEY=value` list item

#### 6. Kafka container startup failure

- Error seen in `docker logs kafka`:
  - `ERROR: Missing environment variable KAFKA_LISTENERS. Must be specified when using KAFKA_ADVERTISED_LISTENERS`
- Cause: `KAFKA_ADVERTISED_LISTENERS` was set without `KAFKA_LISTENERS`
- Resolution: add:
  - `KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092`

#### 7. Logstash pipeline filename typo

- Cause: the file was named `pipline.conf` instead of `pipeline.conf`
- Effect: the intended bind mount could not point to the correct local file
- Resolution: rename it to `logstash/pipeline.conf`

#### 8. Logstash loaded default Beats pipeline unexpectedly

- Evidence from logs:
  - Logstash was listening on port `5044`
  - `pipeline.sources` showed both:
    - `/usr/share/logstash/pipeline/logstash.conf`
    - `/usr/share/logstash/pipeline/pipeline.conf`
- Cause: the Docker image contains a default `logstash.conf`, and the current volume mount adds `pipeline.conf` rather than replacing the whole pipeline directory
- Current decision: leave this as-is for Phase 1 because container startup was the immediate goal

#### 9. Validation script import-check syntax error

- Error seen:
  - Python `SyntaxError` from code using `@('kafka', ...)`
- Cause: PowerShell array syntax was accidentally embedded into Python code in the validation script
- Follow-up needed: update the validator to generate a Python list literal instead

#### 10. Docker access/permission inconsistency

- From the agent shell, Docker inspection commands sometimes failed with access-denied errors to the Docker named pipe or Docker config
- On the user side, `docker compose ps` and `docker logs` succeeded
- Practical takeaway: when container state needs confirmation, prefer the user's direct Docker output if agent-side Docker access is restricted

#### 11. Docker Desktop Linux engine pipe unavailable

- Error seen:
  - `unable to get image 'wurstmeister/zookeeper': error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/images/wurstmeister/zookeeper/json": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.`
- Cause:
  - Docker Desktop was not fully running, or its Linux container engine was unavailable
  - on Windows, the Docker CLI talks to Docker Desktop through the named pipe `//./pipe/dockerDesktopLinuxEngine`
  - if that pipe does not exist, Docker commands fail before image pulls or container startup begin
- Resolution:
  - start or restart Docker Desktop
  - wait until Docker reports that it is running
  - ensure Docker Desktop is using Linux containers
  - verify with:
    - `docker version`
    - `docker info`
  - rerun:
    - `docker-compose up -d`

### Decisions and carry-forward notes

#### A. Logstash default pipeline behavior must be revisited in Phase 6

- Current mount:
  - `./logstash/pipeline.conf:/usr/share/logstash/pipeline/pipeline.conf`
- Because the image also contains `/usr/share/logstash/pipeline/logstash.conf`, Logstash loads both files
- This is acceptable for Phase 1 only because the goal was container startup
- Before or during Phase 6, verify Logstash loads only the intended project pipeline config and not the image default Beats config

#### B. Placeholder `logstash/pipeline.conf` was created for startup, not for real data flow

- The placeholder file exists only to support early Docker bring-up
- It must be replaced with the real Kafka -> Elasticsearch pipeline in Phase 6

#### C. Phase 1 completion criteria used in practice

- All five infrastructure services were brought up through Docker Compose
- Kibana was reachable
- Local Python environment and dependency setup were completed
- Some container verification had to rely on direct user-provided Docker output due environment access limits in the agent shell

#### D. Validation script exists and should be maintained

- File:
  - `scripts/validate_phase1.ps1`
- Purpose:
  - smoke-check repo structure, Docker Compose parsing, service status, Kibana reachability, venv presence, package imports, and spaCy model availability
- Known issue to fix later:
  - the import-check command currently builds invalid Python syntax

### Files created or updated during Phase 1

- `docker-compose.yml`
- `.env.example`
- `requirements.txt`
- `logstash/pipeline.conf`
- `scripts/validate_phase1.ps1`
- `Goals.md`

---

## Phase 2 Summary

Status: Complete

### Completed work

- Created `schemas/raw_article.json` as the source-of-truth contract for `raw-articles`
- Created `schemas/entity_count.json` as the source-of-truth contract for `entity-counts`
- Added root-level `config.py` with environment-driven defaults for:
  - `KAFKA_BOOTSTRAP`
  - `FETCH_INTERVAL_SEC`
  - `WINDOW_DURATION`
  - `SLIDE_DURATION`
  - `TOP_N_ENTITIES`
  - `NER_MODEL`
- Removed placeholder drift that would have caused confusion later:
  - deleted `schemas/raw_articles.json`
  - deleted `schemas/config.py`

### Decisions and carry-forward notes

- Canonical schema filenames are singular and match the README exactly:
  - `schemas/raw_article.json`
  - `schemas/entity_count.json`
- Runtime configuration lives at repo root in `config.py`, not under `schemas/`
- Future code in the producer, Spark job, and Logstash config should use these exact field names to avoid contract drift

### Files created or updated during Phase 2

- `schemas/raw_article.json`
- `schemas/entity_count.json`
- `config.py`
- `Goals.md`
- `context/project_context.md`

---

## Phase 3 Summary

Status: Complete

### Completed work

- Created Kafka topic `raw-articles` with:
  - `3` partitions
  - replication factor `1`
- Created Kafka topic `entity-counts` with:
  - `3` partitions
  - replication factor `1`
- Verified both topics exist in the running Kafka broker

### Errors encountered in Phase 3

#### 1. PowerShell line continuation broke Kafka CLI commands

- The documented Kafka examples were pasted using Bash-style line continuation with `\`
- In PowerShell, `\` does not continue a command onto the next line
- Effect:
  - PowerShell attempted to run fragments like `bootstrap-server`, `topic`, `partitions`, and `replication-factor` as separate commands
  - this produced `CommandNotFoundException` errors
- Resolution:
  - use one-line Kafka commands in PowerShell, or
  - use PowerShell backticks `` ` `` for multiline commands

#### 2. Misparsed topic-create command produced Kafka option error

- Error seen:
  - `Only one of --bootstrap-server or --zookeeper must be specified`
- Cause:
  - the multiline command was broken by PowerShell before Kafka parsed it correctly
- Resolution:
  - rerun the command as a valid single-line PowerShell command

### Decisions and carry-forward notes

- Any Kafka CLI command documented for this repo should be translated to PowerShell-safe syntax when used locally on Windows
- The canonical Phase 3 topics are:
  - `raw-articles`
  - `entity-counts`
- These topics are now infrastructure dependencies for later phases:
  - Phase 4 writes to `raw-articles`
  - Phase 5 reads `raw-articles` and writes `entity-counts`
  - Phase 6 consumes `entity-counts`

### Files created or updated during Phase 3

- `Goals.md`
- `context/project_context.md`

---

## Phase 4 Summary

Status: Complete, with one quality caveat noted below

### Completed work

- Implemented `producer/news_producer.py`
- Wired the producer to load environment variables from `.env`
- Added repo-root config usage by importing:
  - `KAFKA_BOOTSTRAP`
  - `FETCH_INTERVAL_SEC`
  from root `config.py`
- Implemented Finnhub polling against:
  - `https://finnhub.io/api/v1/news`
  - category `general`
- Normalized upstream articles into the exact `schemas/raw_article.json` contract:
  - `event_id`
  - `source`
  - `fetched_at`
  - `headline`
  - `body`
  - `url`
  - `category`
- Added Kafka publishing to topic `raw-articles` using `kafka-python`
- Added request timeout protection for the Finnhub API call
- Added retry-safe loop behavior so transient API or runtime failures log and retry instead of terminating the process
- Added a `main()` entry point so the producer does not start an infinite loop on import
- Fixed module import behavior so running:
  - `python producer/news_producer.py`
  can still import the repo-root `config.py`

### Errors encountered in Phase 4

#### 1. Initial producer published raw Finnhub payloads instead of schema-shaped events

- The first version sent the upstream article object directly to Kafka
- This would have broken the Phase 4 schema contract and the Phase 5 Spark reader expectations
- Resolution:
  - added explicit normalization into the repo's raw-article schema

#### 2. Config drift in fetch interval

- The first version defaulted `FETCH_INTERVAL_SEC` to `3600`
- Repo configuration requires the default to come from root `config.py`, where the default is `10`
- Resolution:
  - import config from root `config.py` instead of redefining it in the producer

#### 3. Repo-root import failure when running the producer directly

- Error seen:
  - `ModuleNotFoundError: No module named 'config'`
- Cause:
  - running `python producer/news_producer.py` places `producer/` on `sys.path`, not the repo root
- Resolution:
  - prepend the repo root to `sys.path` before importing `config`

#### 4. PowerShell line continuation broke the Kafka smoke-test command

- The topic consumer command was initially pasted using Bash-style `\`
- PowerShell split the command and attempted to run fragments like `bootstrap-server`, `topic`, and `from-beginning` as separate commands
- Resolution:
  - use one-line commands in PowerShell, or
  - use PowerShell backticks `` ` `` for multiline commands

### Decisions and carry-forward notes

- The producer currently uses Finnhub `summary` as the best available source for schema field `body`
- The producer uses current UTC time for `fetched_at` when the event is created, not the upstream publication timestamp
- Kafka send calls wait for broker acknowledgement with `.get(timeout=10)` to surface delivery failures promptly
- The producer now satisfies the written Phase 4 goals, assuming the local smoke test was run successfully

#### Quality caveat to revisit

- The current producer does not deduplicate overlapping Finnhub results across polling cycles
- Practical effect:
  - the same article may be published more than once if Finnhub returns it in multiple fetch batches
- This does not block Phase 4 completion under the written checklist, but it can inflate entity counts later in Phase 5 and downstream visualizations in Phase 7
- Recommended follow-up:
  - add lightweight deduplication using a stable upstream identifier such as article URL or Finnhub article ID, with a bounded in-memory cache

### Files created or updated during Phase 4

- `producer/news_producer.py`
- `Goals.md`
- `context/project_context.md`

---

## Phase 5 Troubleshooting Summary

Status: Functionally complete, with a restart/checkpoint caveat

### Current problem

- PySpark/Spark startup is failing on Windows before any real streaming logic can run
- This is currently blocking implementation and runtime validation of `spark/entity_stream.py`

### Errors encountered in Phase 5 setup

#### 1. `spark-submit` resolved to the virtual environment wrapper, not a standalone Spark install

- `Get-Command spark-submit` returned:
  - `D:\Message-Analysis-RealTime\.venv\Scripts\spark-submit.cmd`
- This confirmed the project is relying on the `pyspark` package's Windows launcher inside the venv

#### 2. `SPARK_HOME` was initially unset

- `$env:SPARK_HOME` returned nothing
- Spark startup attempted to infer `SPARK_HOME` automatically and failed

#### 3. Spark Windows launcher defaulted to `python3`, which is not valid in this environment

- Error seen:
  - `Missing Python executable 'python3'`
- Cause:
  - the Windows helper script `find-spark-home.cmd` defaults to `python3` unless `PYSPARK_PYTHON` or `PYSPARK_DRIVER_PYTHON` is explicitly set

#### 4. Spark launcher failed with:

- `The system cannot find the path specified.`
- `Failed to find Spark jars directory.`
- `You need to build Spark before running this program.`

- Initial interpretation:
  - Spark was inferring the wrong `SPARK_HOME`
  - the launcher was falling back to the repo root or another invalid location

#### 5. Direct execution through Python hit the same startup problem

- Running:
  - `.\.venv\Scripts\python.exe spark\entity_stream.py`
  still failed with:
  - `The system cannot find the path specified.`
- This indicates the failure is not limited to the top-level `spark-submit` command and is likely inside PySpark's Windows helper/launcher path

#### 6. Pip-installed PySpark layout differs from what the Windows batch helpers appear to expect

- The venv PySpark install does contain:
  - `bin/`
  - `jars/`
- But it does not contain:
  - `conf/`
- One likely hypothesis is that the Windows batch launcher path assumes a fuller Spark distribution layout than the pip install provides on this machine

### Resolution and investigation steps already tried

- Verified `java -version` works correctly:
  - OpenJDK 17 is installed and available
- Verified these paths exist:
  - `.venv\Lib\site-packages\pyspark`
  - `.venv\Lib\site-packages\pyspark\bin\spark-submit.cmd`
  - `.venv\Lib\site-packages\pyspark\jars`
  - `.venv\Scripts\python.exe`
- Set the following environment variables explicitly in PowerShell:
  - `SPARK_HOME=D:\Message-Analysis-RealTime\.venv\Lib\site-packages\pyspark`
  - `PYSPARK_PYTHON=D:\Message-Analysis-RealTime\.venv\Scripts\python.exe`
  - `PYSPARK_DRIVER_PYTHON=D:\Message-Analysis-RealTime\.venv\Scripts\python.exe`
  - prepended `%SPARK_HOME%\bin` to `PATH`
- Confirmed those environment variables and paths evaluate correctly with:
  - `$env:SPARK_HOME`
  - `$env:PYSPARK_PYTHON`
  - `$env:PYSPARK_DRIVER_PYTHON`
  - `Test-Path`
- Tried running the direct launcher:
  - `& "$env:SPARK_HOME\bin\spark-submit.cmd" --version`
- Tried resolving the Python path explicitly with `Resolve-Path`
- Tried running the minimal Spark script directly with:
  - `.\.venv\Scripts\python.exe spark\entity_stream.py`
- Tried adding Kafka package config directly in code:
  - `spark.jars.packages=org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0`

### Current working hypothesis

- The blocker is not Java, the existence of Spark jars, or the basic presence of PySpark files
- The blocker is most likely PySpark's Windows batch-launcher path resolution in this pip-based venv setup
- A standalone Spark distribution may be more reliable on Windows than the pip-installed wrapper flow for this project

### Carry-forward notes

- Before continuing serious Phase 5 implementation work, Spark startup itself must be made reliable
- If the pip-installed `pyspark` launcher continues to fail, the fallback path is:
  - install a standalone Apache Spark distribution
  - set `SPARK_HOME` to that standalone install
  - use its `bin\spark-submit.cmd`
- Once Spark startup is fixed, Phase 5 implementation can proceed with:
  - reading `raw-articles`
  - parsing `schemas/raw_article.json`
  - running NER
  - producing `entity-counts`

### Files created or updated during Phase 5 troubleshooting

- `spark/entity_stream.py`
- `context/project_context.md`

### Additional Phase 5 investigation and current state

#### What was verified

- `producer/news_producer.py` is able to fetch Finnhub articles and publish them to Kafka
- Consuming `raw-articles` manually shows many valid JSON events
- Spark can now start on the machine after earlier launcher/setup fixes
- The Kafka connector package mismatch was identified and corrected once the actual Spark runtime version was confirmed as `4.1.1`

#### Errors and failure patterns seen after Spark startup

##### 1. Kafka connector version mismatch

- Error seen:
  - `java.lang.NoSuchMethodError: scala.Predef$.wrapRefArray`
- Cause:
  - the Kafka package originally used in `spark/entity_stream.py` targeted the wrong Spark/Scala runtime
- Resolution attempted:
  - confirmed runtime Spark version was `4.1.1`
  - updated connector target to the Spark 4.1.1 / Scala 2.13 artifact

##### 2. Local executor / driver instability on native Windows

- Errors seen:
  - `NullPointerException` in `BlockManagerMasterEndpoint.register()`
  - repeated heartbeat / RPC timeout failures
- Cause:
  - exact root cause still not fully proven, but the failure pattern is in Spark local runtime coordination on Windows rather than in Kafka topic setup
- Resolution attempted:
  - forced local mode with a single worker:
    - `master("local[1]")`
  - set:
    - `spark.driver.host=127.0.0.1`
    - `spark.driver.bindAddress=127.0.0.1`
    - `spark.local.hostname=127.0.0.1`
  - increased:
    - `spark.network.timeout`
    - `spark.executor.heartbeatInterval`
    - `spark.rpc.askTimeout`
  - disabled:
    - shuffle service in local mode
    - Hadoop native library usage

##### 3. Streaming append mode rejected without watermark

- Error seen:
  - `Invalid streaming output mode: append. This output mode is not supported for streaming aggregations without watermark`
- Cause:
  - the stream performs windowed aggregation and was trying to use `append` mode without watermarking
- Resolution attempted:
  - added watermark on `fetched_at_ts` before the windowed aggregation

##### 4. No visible output on `entity-counts`

- Observation:
  - `raw-articles` shows many incoming article events
  - `entity-counts` shows zero messages
- Why this matters:
  - this strongly suggests the issue is in `spark/entity_stream.py`, either in parsing, entity extraction, aggregation, or Kafka sink output

#### Why things may not be working right now

1. Event-time parsing may have been dropping rows silently

- `entity_stream.py` filters out rows where `fetched_at_ts` is null
- If Spark cannot parse `fetched_at`, the rest of the stream becomes empty
- A deeper contract fix was applied:
  - producer now emits `fetched_at` in a single canonical UTC format:
    - `YYYY-MM-DDTHH:MM:SSZ`
  - Spark now parses that exact shape with:
    - `yyyy-MM-dd'T'HH:mm:ssX`

2. Watermark + append mode may delay output enough to look broken during debugging

- The current design uses:
  - watermark
  - sliding window aggregation
  - append mode
- That means output is not necessarily immediate
- Even if processing is correct, results may not appear right away in `entity-counts`

3. Native Windows Spark stability remains a likely environmental risk

- Even after several local-mode hardening changes, Spark has shown Windows-specific instability patterns
- This may still interfere with consistent query execution

#### Steps taken during debugging

- Ran `entity_stream.py` in full Kafka-output mode
- Switched `entity_stream.py` temporarily to console sink for direct inspection
- Simplified the stream to parsing-stage debug output to isolate where rows might be disappearing
- Restored the full pipeline after tightening the producer/Spark timestamp contract
- Added human-readable per-run logs under:
  - `spark/logs/`
- Kept Spark checkpoints under:
  - `spark/checkpoints/entity_stream/`

#### Current design notes

- `spark/checkpoints/entity_stream/` is Spark recovery/state data, not human-readable logs
- `spark/logs/` contains per-run application log files for manual inspection
- `entity_stream.py` currently reads from `raw-articles`, extracts entities, applies watermark + sliding window aggregation, and writes to `entity-counts`

#### Potential ways to make Phase 5 work reliably

1. Continue validating the current native Windows setup

- Keep producer and Spark running together
- Inspect the latest file under `spark/logs/`
- Confirm whether the stream is staying active or terminating silently
- If needed, add one more controlled console checkpoint after timestamp parsing or after entity extraction

2. Reduce streaming complexity temporarily for proof of life

- Temporarily bypass the aggregation and Kafka sink
- Print parsed rows or exploded entity rows directly to the console
- Use this only to confirm the exact stage where data disappears, then restore the full pipeline

3. Add duplicate suppression in the producer

- This does not fix the current Spark failure directly
- But it will prevent repeated Finnhub articles from inflating counts once Phase 5 starts working

4. Move Spark execution to WSL2 if native Windows remains unstable

- This is the strongest fallback if Spark continues to fail in native Windows local mode
- It avoids a large class of Windows-specific launcher, temp-file, and local runtime issues

5. Use a standalone Spark distribution consistently if pip-installed runtime behavior remains inconsistent

- The project already moved through launcher/runtime ambiguity during setup
- A dedicated Spark install may be more predictable than relying on pip-installed PySpark wrappers on Windows

#### Honest current status

- The producer side is working
- Kafka input topic `raw-articles` is confirmed to have valid events
- Phase 5 is now functionally complete: `spark/entity_stream.py` has produced valid end-to-end output in `entity-counts`
- Example observed output:
  - `{"window_start":"2026-04-23 00:10:00","window_end":"2026-04-23 00:15:00","entity":"The International Maritime Organization","entity_type":"ORG","count":28,"trigger_at":"2026-04-23 00:20:36.604"}`
- Remaining caveat:
  - restartability is not yet fully clean across all runs
  - during debugging and after stateful query changes, rerunning sometimes required deleting:
    - `spark/checkpoints/entity_stream`
  - this means the stream logic works, but checkpoint reuse is not yet fully hardened

### Final Phase 5 working state

- Running Spark from WSL2 avoided the earlier native Windows Hadoop/checkpoint crash
- The current stream can:
  - read `raw-articles`
  - parse the article schema
  - extract allowed entities with spaCy
  - aggregate over event-time windows
  - write valid JSON records to `entity-counts`

### Carry-forward notes for later phases

- Spark should be run from WSL2 for the current development workflow
- If restartability matters later, revisit checkpoint reuse behavior before calling the stream operationally hardened
- The checkpoint cleanup command used during debugging was:
  - `rm -rf /mnt/d/Message-Analysis-RealTime/spark/checkpoints/entity_stream`

---

## Phase 6 Summary

Status: Complete

### Completed work

- Replaced the placeholder `logstash/pipeline.conf` with a real Kafka -> Elasticsearch pipeline
- Configured Logstash to consume the `entity-counts` topic
- Parsed the JSON payloads emitted by Spark
- Converted `count` to an integer and mapped `trigger_at` into `@timestamp`
- Indexed records into Elasticsearch daily indices:
  - `entity-counts-%{+YYYY.MM.dd}`
- Verified Elasticsearch created and populated the `entity-counts-*` index
- Verified documents were visible in Kibana after creating/selecting the appropriate data view
- Verified documents in Kibana Discover contained the expected schema fields:
  - `window_start`
  - `window_end`
  - `entity`
  - `entity_type`
  - `count`
  - `trigger_at`

### Errors encountered in Phase 6

#### 1. Logstash could not connect to Kafka due to advertised listener mismatch

- Error seen in Logstash:
  - connection attempts to `localhost/127.0.0.1:9092` from inside the container
- Cause:
  - Kafka was advertising only `localhost:9092`, which works for host-side clients but not for other containers
- Resolution:
  - updated Kafka to use dual listeners:
    - internal listener for Docker-network clients
    - external listener for host/WSL clients
  - updated Logstash to connect to Kafka via the internal listener

#### 2. Kibana initially failed to connect to Elasticsearch consistently

- Symptoms:
  - `localhost:5601` was not reliably reachable
  - Kibana logs showed `No living connections` / `ECONNREFUSED` to Elasticsearch during startup
- Resolution:
  - restarted services cleanly
  - brought the stack back up in dependency order
  - confirmed Kibana eventually became reachable and Discover showed indexed records

### Decisions and carry-forward notes

- Logstash/Elasticsearch flow is now working end to end for the project pipeline
- Docker service startup order matters for local recovery:
  - `zookeeper`
  - `kafka`
  - `elasticsearch`
  - `kibana`
  - `logstash`
- A remaining hygiene item from the build plan is:
  - verify Logstash loads only the intended project pipeline config and not the default Beats pipeline from the image
- Despite that open hygiene item, the functional Phase 6 goal is complete because data is reaching Elasticsearch and is visible in Kibana

### Files created or updated during Phase 6

- `logstash/pipeline.conf`
- `docker-compose.yml`
- `Goals.md`
- `context/project_context.md`

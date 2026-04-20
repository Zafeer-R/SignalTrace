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

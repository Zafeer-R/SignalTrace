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

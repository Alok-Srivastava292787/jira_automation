# 📅 DAY 04 — Sprint 01 | Production-Grade Logging
## Replace print() with Python logging + Structured Pipeline Logs

---

## 🔁 RETROSPECTIVE — Day 03 (Complete BEFORE starting Day 04)

### Required Fix from Day 03 Review
```bash
cd C:\Users\Lenovo\python-de-journey
git checkout sprint-01/day-03-pandas-intro

# 1. Fix T2: change JOIN to LEFT JOIN film_category / LEFT JOIN category
#    Add COALESCE(c.name, 'Uncategorised') AS category
#    Rerun: Films loaded should now show 1000

# 2. Add to dq_findings.md:
#    - payment.payment_date is 2007 while rental.rental_date is 2005 (Pagila seed gap)
#    - film_category: 42 films have no category (inner join silently dropped them)

python sprint-01/day-03/data_explorer.py   # verify 1000 films
git add sprint-01/day-03/
git commit -m "[DAY-003][FIX] T2 LEFT JOIN retains all 1000 films; DQ findings updated"
git push

# Merge to develop, create Day 04 branch
git checkout develop
git merge sprint-01/day-03-pandas-intro
git push origin develop
git checkout -b sprint-01/day-04-logging
```

---

 🗂️ JIRA CARD

| Field           | Value                                                  |
|-----------------|--------------------------------------------------------|
| Epic            | EP-01: Environment & Foundations                       |
| Story           | ST-01: Setup Complete Python Dev Environment           |
| Task ID         | TASK-001                                               |
| Sprint          | Sprint 01 (Days 1–7)                                   |
| Story Points    | 3                                                      |
| Assignee        | Alok Srivastava                                        |
| Labels          | setup, python, git, postgresql, day-01                 |
| Status          | In Progress                                            |
| Acceptance Criteria | Python 3.11+ running, VS Code configured, Git repo live, PostgreSQL installed and accessible |
| Epic            | EP-01: Environment & Foundations                             |
| Story           | ST-02: Explore DVD Rental Schema + Python SQL Fundamentals   |
| Task ID         | TASK-002                                                     |
| Sprint          | Sprint 01 (Days 1–7)                                         |
| Story Points    | 3                                                            |
| Labels          | postgresql, psycopg2, sql, schema, dvdrental, day-02         |
| Acceptance Criteria | ERD understood; 6 Python query scripts producing correct output; results written to CSV; pushed to git |
| Epic            | EP-01: Environment & Foundations                             |
| Story           | ST-03: Pandas DataFrames from PostgreSQL Data                |
| Task ID         | TASK-003                                                     |
| Sprint          | Sprint 01 (Days 1–7)                                         |
| Story Points    | 3                                                            |
| Labels          | pandas, dataframe, eda, postgresql, day-03                   |
| Acceptance Criteria | 4 DataFrames loaded from DB; .info()/.describe() used; 3 transformations applied; DataFrame written back to PostgreSQL; pushed to git |
| Epic            | EP-01: Environment & Foundations                                 |
| Story           | ST-04: Production Logging for Data Pipelines                     |
| Task ID         | TASK-004                                                         |
| Sprint          | Sprint 01 (Days 1–7)                                             |
| Story Points    | 2                                                                |
| Labels          | logging, pipeline, loguru, structured-logs, day-04               |
| Acceptance Criteria | `print()` removed from db_utils + data_explorer; log files written per run; log levels working; log rotation configured; git pushed |


---
## 📁 GIT REPO DETAIL

| Field         | Value                                     |
|---------------|-------------------------------------------|
| Branch        | `sprint-01/day-04-logging`                |
| Base Branch   | `develop`                                 |
| Commit Prefix | `[DAY-004]`                               |
| Folder        | `sprint-01/day-04/`                       |
| Files to Push | `logger.py`, `pipeline_log_demo.py`, updated `db_utils.py`, `logs/` |

---

## 📚 BACKGROUND

Every script you've written so far uses `print()` for output. That works in a notebook or a
one-off query. It does not work in production because:

| `print()`                    | `logging`                              |
|------------------------------|----------------------------------------|
| Always outputs               | Configurable by level (DEBUG/INFO/...) |
| No timestamp                 | Timestamp on every line                |
| No source info               | File + line number available           |
| Lost when process exits      | Written to rotating files              |
| Can't silence in tests       | Tests set level=ERROR to silence       |
| No structure                 | JSON-structured logs for log aggregators|

In data engineering, **logs are your audit trail**. When a pipeline fails at 3am, the log
file tells you which table, which row count, which query, and exactly what went wrong.
Without structured logging you are flying blind.

### Python Logging Architecture

```
Your Code
    │
    ▼
Logger ("pipeline.etl", "db.connection", etc.)
    │  level filter (DEBUG / INFO / WARNING / ERROR / CRITICAL)
    ▼
Handler ──► StreamHandler  → console
         ├► FileHandler    → logs/pipeline_YYYYMMDD.log
         └► RotatingFileHandler → auto-rotate at 5MB, keep 7 files
    │
    ▼
Formatter
    "[2025-01-15 09:32:11] INFO  pipeline.etl | Loaded 1000 rows from film"
```

### Two approaches — standard `logging` vs `loguru`
| Feature           | `logging` (stdlib)    | `loguru`               |
|-------------------|-----------------------|------------------------|
| Setup             | Verbose boilerplate   | One `from loguru import logger` |
| Rotation          | Manual RotatingHandler| `rotation="5 MB"` inline |
| Structured (JSON) | Extra code            | `serialize=True`       |
| Async support     | No                    | Yes                    |
| Use when          | Library code          | Application/pipeline code |

**Today:** learn both. `logging` for `db_utils.py` (library — shouldn't impose loguru).
`loguru` for pipeline scripts (fast, clean, readable).

---

## 🎯 OBJECTIVES

1. Build `logger.py` — centralised logging factory (used by all future pipelines)
2. Upgrade `db_utils.py` — replace all `print()` with `logging` calls
3. Upgrade `data_explorer.py` — replace `print()` with `loguru`
4. Demonstrate log levels: DEBUG, INFO, WARNING, ERROR
5. Configure log rotation (5MB max, 7 file retention)
6. Write structured JSON logs for one pipeline run
7. Push to git

---

## ⏱️ TIME BUDGET (2 hrs)

| Block | Duration | Activity                                        |
|-------|----------|-------------------------------------------------|
| A     | 15 min   | Fix Day 03 + branch setup                       |
| B     | 35 min   | `logger.py` — centralised logging module        |
| C     | 30 min   | Upgrade `db_utils.py` + `data_explorer.py`      |
| D     | 20 min   | `pipeline_log_demo.py` — levels + rotation demo |
| E     | 20 min   | Log + git push                                  |

---

## 📝 EXERCISES

---

### EXERCISE 1 — logger.py: Centralised Logging Factory (Block B)
**[Full steps — this module is imported by every pipeline for 90 days]**

**Objective:** One module that any script imports to get a properly configured logger.
No more duplicating logging setup in every file.

Create `sprint-01/day-04/logger.py`:

```python
#!/usr/bin/env python3
"""
logger.py — Centralised Logging Factory
=========================================
Provides two loggers for the 90-day program:

  get_logger(name)         → stdlib logging.Logger  (for library modules)
  get_pipeline_logger()    → loguru logger           (for pipeline scripts)

Usage:
    # In library/utility modules (db_utils.py etc.):
    from logger import get_logger
    log = get_logger(__name__)
    log.info("Pool created")

    # In pipeline scripts:
    from logger import get_pipeline_logger
    logger = get_pipeline_logger()
    logger.info("Pipeline started | table={table} rows={rows}", table="film", rows=1000)
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime

# ── Resolve project root and logs directory ───────────────────────────────────
_here = Path(__file__).resolve().parent
for _candidate in [_here, _here.parent, _here.parent.parent]:
    if (_candidate / ".env").is_file() or (_candidate / "logs").exists():
        PROJECT_ROOT = _candidate
        break
else:
    PROJECT_ROOT = _here.parent.parent

LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# ── Log format constants ──────────────────────────────────────────────────────
LOG_FORMAT     = "[{asctime}] {levelname:<8} {name} | {message}"
LOG_DATE_FMT   = "%Y-%m-%d %H:%M:%S"
LOG_STYLE      = "{"          # use {}-style formatting (not %-style)

# File naming: one log file per day per pipeline
def _log_file(prefix: str = "pipeline") -> Path:
    date_str = datetime.now().strftime("%Y%m%d")
    return LOGS_DIR / f"{prefix}_{date_str}.log"


# ── stdlib logging factory ────────────────────────────────────────────────────
_configured_loggers: set[str] = set()

def get_logger(
    name: str,
    level: str = None,
    log_file_prefix: str = "pipeline",
) -> logging.Logger:
    """
    Return a configured stdlib Logger for library/utility code.

    Args:
        name:            Logger name — use __name__ to get module path
        level:           Override log level (default: LOG_LEVEL env var or INFO)
        log_file_prefix: Prefix for log filename (default: 'pipeline')

    Returns:
        logging.Logger with StreamHandler + RotatingFileHandler attached
    """
    logger = logging.getLogger(name)

    # Only configure once per name — avoid duplicate handlers on re-import
    if name in _configured_loggers:
        return logger

    # Resolve level: argument → env var → INFO
    resolved_level = getattr(
        logging,
        (level or os.getenv("LOG_LEVEL", "INFO")).upper(),
        logging.INFO,
    )
    logger.setLevel(resolved_level)

    formatter = logging.Formatter(
        fmt=LOG_FORMAT, datefmt=LOG_DATE_FMT, style=LOG_STYLE
    )

    # Console handler — INFO and above
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Rotating file handler — DEBUG and above
    # Rotates at 5MB, keeps 7 files: pipeline_20250115.log, .1, .2, ...
    file_handler = logging.handlers.RotatingFileHandler(
        filename=_log_file(log_file_prefix),
        maxBytes=5 * 1024 * 1024,   # 5 MB
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Prevent propagation to root logger (avoid double logging)
    logger.propagate = False

    _configured_loggers.add(name)
    return logger


# ── loguru pipeline logger factory ───────────────────────────────────────────
def get_pipeline_logger(
    pipeline_name: str = "pipeline",
    level: str = None,
):
    """
    Return a configured loguru logger for pipeline/application scripts.
    loguru's logger is a global singleton — this function configures it
    on first call and returns it for subsequent calls.

    Features enabled:
      - Console: coloured, human-readable
      - File: rotating at 5MB, JSON-structured, 7-day retention
      - Automatic exception traceback capture

    Args:
        pipeline_name: Used as log file prefix (e.g. 'etl', 'dashboard')
        level:         Log level string (default: LOG_LEVEL env var or INFO)

    Returns:
        loguru.logger (global singleton, reconfigured each call)
    """
    try:
        from loguru import logger
    except ImportError:
        # Fallback: return stdlib logger with same interface
        return get_logger(pipeline_name, level)

    resolved_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()

    # Remove default loguru handler
    logger.remove()

    # Console sink — coloured, human-readable
    logger.add(
        sys.stdout,
        level=resolved_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File sink — JSON structured, rotating
    log_path = LOGS_DIR / f"{pipeline_name}_{{time:YYYYMMDD}}.log"
    logger.add(
        str(log_path),
        level="DEBUG",
        rotation="5 MB",
        retention=7,            # keep 7 rotated files
        compression="zip",      # compress old files
        serialize=True,         # write as JSON — parseable by log aggregators
        backtrace=True,         # full stack on exceptions
        diagnose=True,          # variable values in tracebacks
        encoding="utf-8",
    )

    return logger


# ── Convenience: log pipeline run boundaries ─────────────────────────────────
def log_pipeline_start(logger, pipeline_name: str, **context) -> None:
    """Log a standardised pipeline start message with context."""
    logger.info(
        f"{'='*50}\n"
        f"  PIPELINE START: {pipeline_name}\n"
        f"  Context: {context}\n"
        f"{'='*50}"
    )

def log_pipeline_end(logger, pipeline_name: str, rows_processed: int,
                     elapsed_sec: float, status: str = "SUCCESS") -> None:
    """Log a standardised pipeline end message."""
    logger.info(
        f"{'='*50}\n"
        f"  PIPELINE END: {pipeline_name} | {status}\n"
        f"  Rows: {rows_processed:,} | Elapsed: {elapsed_sec:.2f}s\n"
        f"{'='*50}"
    )
```

**✅ Checkpoint:**
```bash
cd sprint-01/day-04
python -c "
from logger import get_logger, get_pipeline_logger
log = get_logger('test')
log.info('stdlib logger working')
log.debug('this goes to file only')
pl = get_pipeline_logger('test_pipeline')
pl.info('loguru logger working')
"
# Should print 2 INFO lines to console
# Check logs/ folder for new .log file
```

---

### EXERCISE 2 — Upgrade db_utils.py (Block C)
**[Full steps — shows exactly what changes. Pattern repeated for all future modules]**

**Objective:** Replace the `log.debug(...)` stubs in your existing `db_utils.py` with
real logger calls. db_utils uses stdlib `logging` (not loguru) because it's a library
module — it should not force a logging framework on callers.

Open `sprint-01/day-02/db_utils.py` and make these changes:

```python
# CHANGE 1: At the top, replace:
#   log = logging.getLogger(__name__)
# WITH:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "day-04"))
from logger import get_logger
log = get_logger(__name__)

# CHANGE 2: In _get_pool(), replace the log.debug line with:
log.debug("Connection pool created | maxconn=%s host=%s db=%s",
          os.getenv("DB_POOL_SIZE", 5),
          os.getenv("DB_HOST"),
          os.getenv("DB_NAME"))

# CHANGE 3: In get_engine(), after engine created:
log.debug("SQLAlchemy engine created | url=%s:%s/%s",
          os.getenv("DB_HOST"), os.getenv("DB_PORT"), os.getenv("DB_NAME"))

# CHANGE 4: In dispose_engine():
log.info("SQLAlchemy engine disposed — all pool connections closed")

# CHANGE 5: In close_pool():
log.info("psycopg2 connection pool closed — all connections released")

# CHANGE 6: In execute_query() — add timing log:
import time
start = time.perf_counter()
# ... existing code ...
elapsed = time.perf_counter() - start
log.debug("execute_query | rows=%d elapsed=%.3fs sql=%.80s", len(rows), elapsed, sql.strip())
```

**Test:**
```bash
# Set LOG_LEVEL=DEBUG to see all messages
set LOG_LEVEL=DEBUG   # Windows
python -c "
import sys; sys.path.insert(0, 'sprint-01/day-02')
from db_utils import execute_query, close_pool
rows = execute_query('SELECT COUNT(*) FROM film')
print('Count:', rows[0][0])
close_pool()
"
# Should see DEBUG lines about pool creation, query timing
```

---

### EXERCISE 3 — pipeline_log_demo.py: Full Demo (Block D)
**[Partial steps — you fill in the ERROR and WARNING demonstrations]**

**Objective:** Run a mini-pipeline that demonstrates all 5 log levels,
exception capture, and structured JSON output.

Create `sprint-01/day-04/pipeline_log_demo.py`:

```python
#!/usr/bin/env python3
"""
pipeline_log_demo.py — Day 04 | Logging Demonstration
======================================================
Runs a short pipeline demonstrating:
  - All 5 log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Exception capture with full traceback
  - Structured JSON log output
  - Pipeline start/end markers
  - Per-table row count logging

Run: python pipeline_log_demo.py
Then open logs/demo_pipeline_YYYYMMDD.log to see JSON output.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "day-02"))

from logger import get_pipeline_logger, log_pipeline_start, log_pipeline_end
from db_utils import get_engine, execute_query, execute_scalar, close_pool, dispose_engine

logger = get_pipeline_logger("demo_pipeline")

TABLES = ["film", "customer", "rental", "payment", "inventory"]


def step_1_connect_and_count():
    """Step 1: Connect and log row counts for all tables."""
    logger.info("Step 1 | Connecting to database and counting rows")

    for table in TABLES:
        count = execute_scalar(f"SELECT COUNT(*) FROM {table}")
        # INFO: normal operational message
        logger.info("Table inventory | table={} rows={:,}", table, count)

        # DEBUG: detailed diagnostic — only visible when LOG_LEVEL=DEBUG
        logger.debug("Table details | table={} dtype_check=pending", table)


def step_2_detect_warning():
    """Step 2: Demonstrate WARNING level — data quality threshold breach."""
    logger.info("Step 2 | Checking data quality thresholds")

    null_returns = execute_scalar(
        "SELECT COUNT(*) FROM rental WHERE return_date IS NULL"
    )
    total_rentals = execute_scalar("SELECT COUNT(*) FROM rental")
    null_pct = null_returns / total_rentals * 100

    if null_pct > 5:
        # WARNING: something is unusual but pipeline can continue
        logger.warning(
            "Data quality | null return_date exceeds threshold | "
            "null_count={} total={} pct={:.1f}% threshold=5%",
            null_returns, total_rentals, null_pct
        )
    else:
        logger.info("Data quality | null return_date within threshold | pct={:.1f}%", null_pct)


def step_3_simulate_error():
    """
    Step 3: Demonstrate ERROR level — recoverable failure.

    YOUR TASK: Write code that:
      1. Attempts to query a table that does NOT exist: 'film_archive'
      2. Catches the exception
      3. Logs it at ERROR level with the exception details
      4. Logs a recovery message at WARNING level
      5. Continues (does not crash the pipeline)

    HINTS:
      - Use try/except around execute_query("SELECT * FROM film_archive")
      - logger.error("message | error={}", str(exc))  ← loguru syntax
      - logger.exception("message")  ← auto-captures current exception + traceback
      - After catch: logger.warning("Skipping film_archive — table not found, continuing")
    """
    logger.info("Step 3 | Testing error recovery")

    # YOUR CODE HERE
    raise NotImplementedError("Implement step_3 error handling — see hints above")


def step_4_log_summary():
    """Step 4: Write a structured summary row to the log."""
    logger.info("Step 4 | Writing pipeline summary")

    summary = {
        "pipeline":     "demo_pipeline",
        "tables_checked": len(TABLES),
        "status":       "SUCCESS",
    }
    # loguru accepts **kwargs for structured context
    logger.info("Pipeline summary | {}", summary)


def main():
    start_time = time.perf_counter()

    log_pipeline_start(logger, "demo_pipeline",
                       env="development", db="dvdrental")
    rows_processed = 0

    try:
        step_1_connect_and_count()
        rows_processed += sum(
            execute_scalar(f"SELECT COUNT(*) FROM {t}") for t in TABLES
        )

        step_2_detect_warning()

        try:
            step_3_simulate_error()
        except NotImplementedError as e:
            logger.warning("step_3 not implemented yet: {}", e)

        step_4_log_summary()

    except Exception as exc:
        # CRITICAL: unrecoverable failure — pipeline aborted
        logger.critical("Pipeline aborted | error={}", exc)
        raise
    finally:
        elapsed = time.perf_counter() - start_time
        log_pipeline_end(logger, "demo_pipeline",
                         rows_processed=rows_processed,
                         elapsed_sec=elapsed)
        close_pool()
        dispose_engine()


if __name__ == "__main__":
    main()
```

**After implementing step_3, verify the JSON log:**
```bash
# Run the demo
python sprint-01/day-04/pipeline_log_demo.py

# View the JSON log file (one JSON object per line)
# Windows PowerShell:
Get-Content logs\demo_pipeline_*.log | Select-Object -Last 20

# Or Python:
python -c "
import json, glob
files = glob.glob('logs/demo_pipeline_*.log')
if files:
    with open(sorted(files)[-1]) as f:
        for line in f:
            try:
                rec = json.loads(line)
                print(rec.get('record',{}).get('level',{}).get('name','?'),
                      '|', rec.get('record',{}).get('message',''))
            except: pass
"
```

**✅ Expected log levels in output:**
```
DEBUG    | Table details | table=film dtype_check=pending
INFO     | Table inventory | table=film rows=1,000
INFO     | Table inventory | table=customer rows=599
WARNING  | Data quality | null return_date exceeds threshold | pct=XX.X%
ERROR    | Query failed | table=film_archive error=...
WARNING  | Skipping film_archive — table not found, continuing
INFO     | Pipeline summary | {...}
INFO     | PIPELINE END: demo_pipeline | SUCCESS
```

---

### EXERCISE 4 — Git Push (Block E)

```bash
cd C:\Users\Lenovo\python-de-journey

# One clean commit — not two
git add sprint-01/day-04/
git add sprint-01/day-02/db_utils.py    # updated with logging
git add logs/.gitkeep                   # keep logs/ tracked but not log files

# Verify .gitignore excludes actual log files
# Add to .gitignore if not present:
#   logs/*.log
#   logs/*.log.*
#   logs/*.zip

git status   # review before commit

git commit -m "[DAY-004][S01] Production logging: logger.py module, db_utils upgraded, pipeline_log_demo with all 5 levels"
git push -u origin sprint-01/day-04-logging

python scripts/daily_log.py --day 4 --sprint 1 ^
  --message "Logging: logger.py with stdlib+loguru, db_utils upgraded, pipeline_log_demo all 5 levels + JSON file output" ^
  --status done
```

---

## ✅ DAY 04 COMPLETION CHECKLIST

| # | Task                                                                | Done? |
|---|---------------------------------------------------------------------|-------|
| 1 | Day 03 T2 LEFT JOIN fix committed (1000 films)                      | [ ]   |
| 2 | `sprint-01/day-04/` created                                         | [ ]   |
| 3 | `logger.py` created — imports cleanly                               | [ ]   |
| 4 | `get_logger()` writes to console AND rotating file                  | [ ]   |
| 5 | `get_pipeline_logger()` writes JSON to logs/                        | [ ]   |
| 6 | `db_utils.py` updated — no `print()` remaining                      | [ ]   |
| 7 | LOG_LEVEL=DEBUG shows pool creation + query timing                  | [ ]   |
| 8 | `pipeline_log_demo.py` runs step_1 + step_2                         | [ ]   |
| 9 | **step_3 written by you — error caught, logged, pipeline continues**| [ ]   |
|10 | JSON log file exists in `logs/` folder                              | [ ]   |
|11 | `logs/*.log` excluded from git (in .gitignore)                      | [ ]   |
|12 | Exactly ONE commit for Day 04 (no duplicate commits)                | [ ]   |
|13 | `git push` to `sprint-01/day-04-logging`                            | [ ]   |

---

## 🔍 SELF-CHECK — step_3 is correct when:

```bash
python sprint-01/day-04/pipeline_log_demo.py
# ✅ Pipeline does NOT crash
# ✅ ERROR line appears in console output
# ✅ WARNING "Skipping film_archive" appears after the error
# ✅ Pipeline END message still prints
# ✅ JSON log shows a record with level.name = "ERROR"
```

---

## ⚠️ WATCH OUT FOR

**Log file growing silently on Windows:**
`RotatingFileHandler` on Windows can fail to rotate if another process has the file open
(e.g. VS Code's log viewer). If rotation fails, add `delay=True` to the handler
constructor. This is a known Windows-specific issue.

**loguru's global singleton:**
`from loguru import logger` always gives the same object. Calling `get_pipeline_logger()`
twice with different names will reconfigure the same logger — the second call wins.
This is fine for single-pipeline scripts. In Sprint 09 (Airflow), each DAG gets its
own logger name to avoid this.

**Don't log passwords:**
`log.debug("Connecting with config=%s", db_config)` would print the password.
Always sanitise: `{k: '***' if 'pass' in k.lower() else v for k, v in cfg.items()}`

---

## 🔜 PREVIEW: DAY 05

**Topic:** Git workflow deep-dive + Python git automation  
**What you'll do:** Write a Python script using `GitPython` to automate daily branch
creation, commit, push, and PR creation. Also cover `git diff`, `git stash`, and
`git rebase` for the daily workflow. This replaces the manual `git_daily_push.sh` script.

---

*Day 04 | Sprint 01 | EP-01 | TASK-004*

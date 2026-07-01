"""Async database connection with graceful degradation.

Works identically without a database — all queries return empty results.
When DATABASE_URL is set, connects to PostgreSQL and runs migrations.
"""

import json
import logging
import os
import threading
from collections import deque
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_pool = None
_write_queue: deque = deque(maxlen=100000)
_writer_thread: Optional[threading.Thread] = None
_writer_stop = threading.Event()


_ALLOWED_TABLES = frozenset({
    "evidence_artifacts",
    "classification_records",
    "baseline_profiles",
    "baseline_build_jobs",
    "agent_actions",
    "verification_records",
    "learning_proposals",
})


async def init_db():
    global _pool
    url = os.getenv("DATABASE_URL")
    if not url:
        logger.info("DATABASE_URL not set — running without persistence")
        return

    try:
        import asyncpg
        _pool = await asyncpg.create_pool(url, min_size=2, max_size=10)
        await _run_migrations()
        _start_writer()
        logger.info("Database connected and migrations applied")
    except Exception as e:
        logger.warning("Database init failed (continuing without persistence): %s", str(e)[:200])
        _pool = None


async def close_db():
    global _pool
    _stop_writer()
    if _pool:
        await _pool.close()
        _pool = None


async def query(sql: str, *args) -> list:
    if _pool is None:
        return []
    try:
        async with _pool.acquire() as conn:
            rows = await conn.fetch(sql, *args)
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error("Query failed: %s", str(e)[:200])
        return []


def enqueue_write(table: str, data: dict):
    if table not in _ALLOWED_TABLES:
        logger.warning("Rejected write to unknown table: %s", table)
        return
    if _pool is None:
        return
    qlen = len(_write_queue)
    if qlen > 80000:
        logger.warning("Write queue near capacity: %d/100000", qlen)
    _write_queue.append((table, data))


async def _run_migrations():
    if _pool is None:
        return
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    if not migrations_dir.exists():
        return
    async with _pool.acquire() as conn:
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            try:
                sql = sql_file.read_text()
                await conn.execute(sql)
                logger.info("Migration applied: %s", sql_file.name)
            except Exception as e:
                logger.warning("Migration %s: %s", sql_file.name, str(e)[:200])


def _start_writer():
    global _writer_thread
    _writer_stop.clear()
    _writer_thread = threading.Thread(target=_writer_loop, daemon=True)
    _writer_thread.start()


def _stop_writer():
    _writer_stop.set()
    if _writer_thread and _writer_thread.is_alive():
        _writer_thread.join(timeout=5)


def _writer_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    while not _writer_stop.is_set():
        batch = []
        while _write_queue and len(batch) < 100:
            batch.append(_write_queue.popleft())
        if batch and _pool:
            loop.run_until_complete(_flush_batch(batch))
        _writer_stop.wait(timeout=0.5)
    loop.close()


async def _flush_batch(batch: list):
    if not _pool:
        return
    try:
        async with _pool.acquire() as conn:
            for table, data in batch:
                cols = list(data.keys())
                vals = []
                for v in data.values():
                    if isinstance(v, (dict, list)):
                        vals.append(json.dumps(v))
                    else:
                        vals.append(v)
                placeholders = ", ".join(f"${i+1}" for i in range(len(cols)))
                col_names = ", ".join(cols)
                await conn.execute(
                    f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})",
                    *vals,
                )
    except Exception as e:
        logger.error("Batch write failed: %s", str(e)[:200])

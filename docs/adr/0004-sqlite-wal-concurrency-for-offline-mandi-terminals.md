# ADR-0004: SQLite WAL Concurrency & Edge Portability for Offline Mandi Terminals

## Status
Accepted

## Date
2026-10-02 (Updated 2026-10-04)

## Context
APMC mandis in rural Maharashtra, Madhya Pradesh, and Karnataka frequently experience power fluctuations, intermittent internet connectivity, and dust-heavy field environments.

Engineers often default to cloud-hosted PostgreSQL clusters. However, in an offline mandi terminal or ruggedized edge gateway:
- Requiring an external database daemon introduces complex service orchestration, network latency overhead, and failure points when offline.
- Conversely, naive SQLite configurations suffer from `sqlite3.OperationalError: database is locked` when simultaneous HTTP requests attempt writes during rapid bulk sample uploads or concurrent background inference.

## Decision
We configure an **Industrial-Grade Embedded SQLite Architecture** with strict concurrency primitives (`backend/database.py`):

1. **Write-Ahead Logging (WAL Mode)**:
   - Configured via connection listener:
     `PRAGMA journal_mode = WAL;`
   - Readers never block writers, and writers never block readers. Readers see a snapshot of the database at the start of their transaction.

2. **Synchronous Normal & Busy Timeout**:
   - `PRAGMA synchronous = NORMAL;` (dramatically boosts disk I/O while maintaining crash safety in WAL mode).
   - `PRAGMA busy_timeout = 5000;` (locks wait up to 5,000 milliseconds for lock release before throwing exceptions, eliminating transient contention failures).

3. **In-Flight Schema Migrations**:
   - Dynamic schema alignment (`_ensure_columns_exist` in `database.py`) automatically discovers and applies missing columns (`image_sha256`, `cryptographic_seal`, `seal_status`) on application boot without external migration scripts.

## Consequences

### Positive
- 100% zero-dependency edge portability: The entire server runs on a single binary + database file on Raspberry Pi, Jetson Nano, laptop, or Docker container.
- High concurrency: Up to thousands of concurrent read queries per second with robust concurrent write safety.
- Instant crash recovery: WAL checkpointing recovers cleanly from sudden power disconnects.

### Negative / Trade-offs
- SQLite is limited to a single physical node writing to the database file; multi-master horizontal clustering is not supported without Litestream or Bedrock replication.

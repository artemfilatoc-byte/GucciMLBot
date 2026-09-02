# GucciMLBot Project Memory

## Overview

GucciMLBot is a Python Telegram bot built with aiogram 3.15, SQLAlchemy async, SQLite by default, and Telethon. It manages user access, imports Telegram user sessions, assigns proxies, creates Telegram bots through BotFather, stores created bot tokens, edits bot metadata, and supports admin tools.

## Runtime

- Entry point: `main.py`
- Start command: `python main.py`
- Dependencies: `requirements.txt`
- Default database: `bot.db` via `sqlite+aiosqlite:///bot.db`
- Tables are created automatically in `core.db.init_db()`
- SQLite-only lightweight migrations are in `core.db._migrate_schema()`

## Required Environment

- `BOT_TOKEN` is required.
- `TG_API_ID` and `TG_API_HASH` are required for Telethon account/session operations.
- `ADMIN_IDS` is optional and contains comma/semicolon-separated Telegram IDs.

Useful optional env values:

- `DATABASE_URL`
- `APP_TEMP_DIR`
- `TELETHON_CONNECT_TIMEOUT`
- `TELETHON_IMPORT_CONCURRENCY`
- `ACCOUNT_IMPORT_MAX_FILE_SIZE_MB`
- `ACCOUNT_IMPORT_MAX_SESSION_FILE_SIZE_MB`
- `ACCOUNT_IMPORT_MAX_ARCHIVE_FILES`
- `BOT_CREATE_CONCURRENCY`
- `BOT_CREATE_MAX_PER_ACCOUNT`
- `BOT_CREATE_MAX_COUNT`
- `BOT_USERNAME_MAX_ATTEMPTS`
- `BOT_USERNAME_PRECHECK`
- `BOT_CREATE_DELAY_MIN_SECONDS`
- `BOT_CREATE_DELAY_MAX_SECONDS`
- `BOTFATHER_RETRY_MAX_SECONDS`
- `BOTFATHER_USERNAME`
- `BOTFATHER_TIMEOUT_SECONDS`
- `TG_DEVICE_MODEL`
- `TG_SYSTEM_VERSION`
- `TG_APP_VERSION`
- `TG_LANG_CODE`
- `TG_SYSTEM_LANG_CODE`

## Architecture

- `core/`: configuration and database setup.
- `models.py`: SQLAlchemy models.
- `handlers/`: aiogram routers and FSM flows.
- `keyboards/`: inline keyboard builders and callback constants.
- `repositories/`: database access layer.
- `services/`: Telegram, BotFather, account import/check, broadcast, avatar, and background task logic.
- `texts/`: message formatting and static bot texts.
- `middlewares/`: access gate middleware.
- `assets/emoji_avatars/`: PNG avatar assets used for random bot avatars.

## Data Models

- `User`: Telegram user profile and access status.
- `AccessKey`: admin-generated activation keys.
- `TelegramAccount`: imported user account sessions, including optional proxy.
- `CreatedBot`: bots created via BotFather and their tokens.
- `TokenCreateBatch`: batch-level state for token creation.
- `TokenCreateBatchItem`: per-token success/failure result.

## Main Flows

Access:

- `middlewares.access.AccessMiddleware` blocks users without access.
- Allowed before access: `/start`, `/key`, `/admin`, and plain activation keys.
- Admin status comes from `ADMIN_IDS`.
- Access keys are generated, activated, listed, deleted, and tracked through `repositories.access`.

Accounts:

- `handlers.accounts` handles account list, import, deletion, proxy upload, and account checks.
- Import accepts `.session`, `.txt` StringSession files, or `.zip` archives.
- Import work is done in `services.account_import`.
- Account health cleanup is done in `services.account_checker`.
- Proxies are parsed in `services.telegram_client.parse_proxy_url`.

Bot tokens:

- `handlers.tokens` handles bot creation FSM, token list/export, token deletion, bot editing, batch result pages, stop requests, and bulk avatars.
- Creation is persisted as a resumable batch in `repositories.token_batch`.
- On startup, `resume_pending_token_batches()` resumes running/stopping batches.
- Bot creation logic is in `services.bot_creator`.
- Created bot editing is in `services.bot_editor`.
- Bulk avatar setting is in `services.bulk_avatar`.

Admin:

- `/admin` opens the admin panel.
- Admin can create/list/delete access keys, list/revoke users, refresh stats, and broadcast messages.
- Broadcast logic is in `services.broadcast`.

## Important Implementation Details

- aiogram FSM uses `MemoryStorage`, so user dialog state is not persisted across process restarts.
- Long-running work is launched through `services.background.spawn_background_task()`.
- Bot creation has global concurrency via `BOT_CREATE_CONCURRENCY`.
- Each Telegram account has an in-memory lock in `services.bot_creator` to avoid concurrent BotFather operations for the same account.
- Batch creation stores item results as they arrive, making restart recovery possible.
- SQLite gets WAL mode, foreign keys, and busy timeout pragmas.
- Runtime temp files use `APP_TEMP_DIR`, defaulting to `.runtime/tmp` inside the project.
- There is no test suite in the repository yet.
- No README is present yet.

## Encoding Note

Many Russian strings appear garbled in PowerShell output unless the console reads them as UTF-8. Before editing user-facing text, inspect files with UTF-8-aware tooling and avoid accidental re-encoding.

## Change Guidance

- Reuse existing layers: handler for Telegram event flow, service for business logic, repository for DB access, texts for output, keyboards for markup.
- Keep async SQLAlchemy sessions short and commit explicitly on writes.
- Preserve strict ownership checks by `owner_user_id` when reading or mutating accounts, created bots, and token batches.
- When adding a new callback flow, define constants and keyboard builders in `keyboards/`, text in `texts/`, and register handlers in the relevant router.
- When adding DB columns, update `models.py` and the SQLite migration block in `core.db._migrate_schema()`.
- Avoid blocking operations in handlers; use background tasks for imports, account checks, broadcasts, and batch creation.

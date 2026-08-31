from datetime import datetime, timedelta, timezone



from sqlalchemy import event

from sqlalchemy import text

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sqlalchemy.orm import DeclarativeBase



from core.config import DATABASE_URL



MSK = timezone(timedelta(hours=3))





def now_msk() -> datetime:

    return datetime.now(MSK).replace(tzinfo=None)





class Base(DeclarativeBase):

    pass





IS_SQLITE = DATABASE_URL.startswith("sqlite")



if IS_SQLITE:

    from sqlalchemy.dialects.sqlite import insert

else:

    from sqlalchemy.dialects.postgresql import insert



_engine_kwargs: dict = {"echo": False}

if not IS_SQLITE:

    _engine_kwargs.update(

        pool_size=10,

        max_overflow=10,

        pool_pre_ping=True,

        pool_recycle=1800,

    )



engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

Session = async_sessionmaker(engine, expire_on_commit=False)





if IS_SQLITE:



    @event.listens_for(engine.sync_engine, "connect")

    def _set_sqlite_pragma(dbapi_connection, _):

        cursor = dbapi_connection.cursor()

        cursor.execute("PRAGMA foreign_keys=ON")

        cursor.execute("PRAGMA journal_mode=WAL")

        cursor.execute("PRAGMA busy_timeout=10000")

        cursor.close()





async def init_db() -> None:

    import models              



    async with engine.begin() as conn:

        await conn.run_sync(Base.metadata.create_all)

        await _migrate_schema(conn)





async def _migrate_schema(conn) -> None:

    if not IS_SQLITE:

        return

    user_columns = await conn.execute(text("PRAGMA table_info(users)"))

    existing_user_columns = {row[1] for row in user_columns.fetchall()}

    if "access_granted_at" not in existing_user_columns:

        await conn.execute(text("ALTER TABLE users ADD COLUMN access_granted_at DATETIME"))



    columns = await conn.execute(text("PRAGMA table_info(token_create_batches)"))

    existing = {row[1] for row in columns.fetchall()}

    migrations = {

        "status": "ALTER TABLE token_create_batches ADD COLUMN status VARCHAR(32) DEFAULT 'completed' NOT NULL",

        "name": "ALTER TABLE token_create_batches ADD COLUMN name VARCHAR(64)",

        "base_username": "ALTER TABLE token_create_batches ADD COLUMN base_username VARCHAR(64)",

        "base_usernames": "ALTER TABLE token_create_batches ADD COLUMN base_usernames TEXT",

        "extra_usernames": "ALTER TABLE token_create_batches ADD COLUMN extra_usernames TEXT",

        "account_limit": "ALTER TABLE token_create_batches ADD COLUMN account_limit INTEGER",

        "set_avatars": "ALTER TABLE token_create_batches ADD COLUMN set_avatars BOOLEAN DEFAULT 0 NOT NULL",

        "chat_id": "ALTER TABLE token_create_batches ADD COLUMN chat_id BIGINT",

        "progress_message_id": "ALTER TABLE token_create_batches ADD COLUMN progress_message_id INTEGER",

        "updated_at": "ALTER TABLE token_create_batches ADD COLUMN updated_at DATETIME",

        "finished_at": "ALTER TABLE token_create_batches ADD COLUMN finished_at DATETIME",

    }

    for column, statement in migrations.items():

        if column not in existing:

            await conn.execute(text(statement))



    acc_cols = await conn.execute(text("PRAGMA table_info(telegram_accounts)"))

    acc_existing = {row[1] for row in acc_cols.fetchall()}

    if "proxy_url" not in acc_existing:

        await conn.execute(text("ALTER TABLE telegram_accounts ADD COLUMN proxy_url TEXT"))


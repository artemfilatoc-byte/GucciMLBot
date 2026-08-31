from datetime import datetime



from sqlalchemy import (

    BigInteger,

    Boolean,

    DateTime,

    ForeignKey,

    Integer,

    String,

    Text,

    UniqueConstraint,

)

from sqlalchemy.orm import Mapped, mapped_column



from core.db import Base, now_msk





class User(Base):

    __tablename__ = "users"



    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)

    username: Mapped[str | None] = mapped_column(String(64))

    full_name: Mapped[str | None] = mapped_column(String(256))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_msk)

    access_granted_at: Mapped[datetime | None] = mapped_column(DateTime)





class AccessKey(Base):

    __tablename__ = "access_keys"



    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    key_preview: Mapped[str] = mapped_column(String(32))

    created_by_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)

    activated_by_user_id: Mapped[int | None] = mapped_column(

        ForeignKey("users.id", ondelete="SET NULL"),

        index=True,

    )

    activated_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_msk)

    activated_at: Mapped[datetime | None] = mapped_column(DateTime)





class TelegramAccount(Base):

    __tablename__ = "telegram_accounts"

    __table_args__ = (

        UniqueConstraint(

            "owner_user_id",

            "telegram_id",

            name="uq_telegram_accounts_owner_telegram_id",

        ),

    )



    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    owner_user_id: Mapped[int] = mapped_column(

        ForeignKey("users.id", ondelete="CASCADE"), index=True

    )

    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)

    phone: Mapped[str | None] = mapped_column(String(32))

    username: Mapped[str | None] = mapped_column(String(64))

    first_name: Mapped[str | None] = mapped_column(String(128))

    last_name: Mapped[str | None] = mapped_column(String(128))

    session_string: Mapped[str] = mapped_column(Text)

    dc_id: Mapped[int | None] = mapped_column(Integer)

    proxy_url: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_msk)

    updated_at: Mapped[datetime] = mapped_column(

        DateTime,

        default=now_msk,

        onupdate=now_msk,

    )

    last_checked_at: Mapped[datetime] = mapped_column(DateTime, default=now_msk)





class CreatedBot(Base):

    __tablename__ = "created_bots"

    __table_args__ = (

        UniqueConstraint(

            "owner_user_id",

            "bot_telegram_id",

            name="uq_created_bots_owner_bot_telegram_id",

        ),

    )



    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    owner_user_id: Mapped[int] = mapped_column(

        ForeignKey("users.id", ondelete="CASCADE"),

        index=True,

    )

    account_id: Mapped[int | None] = mapped_column(

        ForeignKey("telegram_accounts.id", ondelete="SET NULL"),

        index=True,

    )

    bot_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)

    name: Mapped[str] = mapped_column(String(64))

    username: Mapped[str] = mapped_column(String(64), index=True)

    token: Mapped[str] = mapped_column(Text)

    manager_bot_id: Mapped[int | None] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_msk)

    updated_at: Mapped[datetime] = mapped_column(

        DateTime,

        default=now_msk,

        onupdate=now_msk,

    )





class TokenCreateBatch(Base):

    __tablename__ = "token_create_batches"



    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    owner_user_id: Mapped[int] = mapped_column(

        ForeignKey("users.id", ondelete="CASCADE"),

        index=True,

    )

    requested_count: Mapped[int] = mapped_column(Integer)

    created_count: Mapped[int] = mapped_column(Integer)

    failed_count: Mapped[int] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(String(32), default="completed")

    name: Mapped[str | None] = mapped_column(String(64))

    base_username: Mapped[str | None] = mapped_column(String(64))

    base_usernames: Mapped[str | None] = mapped_column(Text)

    extra_usernames: Mapped[str | None] = mapped_column(Text)

    account_limit: Mapped[int | None] = mapped_column(Integer)

    set_avatars: Mapped[bool] = mapped_column(Boolean, default=False)

    chat_id: Mapped[int | None] = mapped_column(BigInteger)

    progress_message_id: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_msk)

    updated_at: Mapped[datetime] = mapped_column(

        DateTime,

        default=now_msk,

        onupdate=now_msk,

    )

    finished_at: Mapped[datetime | None] = mapped_column(DateTime)





class TokenCreateBatchItem(Base):

    __tablename__ = "token_create_batch_items"

    __table_args__ = (

        UniqueConstraint(

            "batch_id",

            "position",

            name="uq_token_create_batch_items_batch_position",

        ),

    )



    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    batch_id: Mapped[int] = mapped_column(

        ForeignKey("token_create_batches.id", ondelete="CASCADE"),

        index=True,

    )

    created_bot_id: Mapped[int | None] = mapped_column(

        ForeignKey("created_bots.id", ondelete="SET NULL"),

        index=True,

    )

    account_id: Mapped[int | None] = mapped_column(

        ForeignKey("telegram_accounts.id", ondelete="SET NULL"),

        index=True,

    )

    position: Mapped[int] = mapped_column(Integer)

    ok: Mapped[bool] = mapped_column(Boolean)

    account_title: Mapped[str] = mapped_column(String(128))

    name: Mapped[str] = mapped_column(String(64))

    username: Mapped[str | None] = mapped_column(String(64))

    token: Mapped[str | None] = mapped_column(Text)

    error: Mapped[str | None] = mapped_column(Text)


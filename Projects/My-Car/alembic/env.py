from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

import asyncio
from alembic import context

# Add this block to allow the script to find the 'app' module
import os
import sys
from pathlib import Path

# Go up two levels from alembic/ to the project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import your Base and models
from app.database.base import Base
from app.models import user, car  # noqa
from app.config import settings # Import app settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Use the database URL from your application's settings
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Use the database URL from your application's settings
    # Get the sqlalchemy.url from the alembic.ini and override it with our settings
    connectable = create_async_engine(
        settings.DATABASE_URL, # Use the URL from app settings
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def do_run_migrations(connection):
    context.configure(
        connection=connection, target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

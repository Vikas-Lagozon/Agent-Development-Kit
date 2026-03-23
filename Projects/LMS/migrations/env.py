import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- START OF MODIFICATIONS ---

# Add the project root directory to the Python path
# This allows Alembic to find your 'lms' package and its models.
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

# Import the application settings
from lms.app.config import settings

# Import the declarative Base from your application
from lms.app.database.base import Base

# Import all models here so that Base.metadata is populated
from lms.app.models import user, course, enrollment  # noqa

# --- END OF MODIFICATIONS ---


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
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = str(settings.db_url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get the configuration section from alembic.ini
    configuration = config.get_section(config.config_ini_section, {})
    # Override the URL with the one from the application's settings
    
    # Use a synchronous driver for Alembic if an async one is configured
    if settings.DB_DRIVER == "sqlite+aiosqlite":
        configuration["sqlalchemy.url"] = f"sqlite:///{settings.DB_NAME}"
    else:
        configuration["sqlalchemy.url"] = str(settings.db_url)
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

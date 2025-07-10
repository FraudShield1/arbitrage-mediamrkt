"""
Alembic Environment Configuration

Configuration for auto-generating database migrations for the
Cross-Market Arbitrage Tool using SQLAlchemy models.
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import get_settings
from src.models import Base  # Import the base model

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get settings
settings = get_settings()

# Set the SQLAlchemy URL from settings
# Convert pydantic URL to string and replace async driver with sync for Alembic
database_url = str(settings.DATABASE_URL).replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", database_url)

# add your model's MetaData object here
# for 'autogenerate' support
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
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with database connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Include object comparison for better autogeneration
        compare_default=True,
        include_name=include_name,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def include_name(name, type_, parent_names):
    """Include specific names in migrations."""
    # Include all tables
    if type_ == "table":
        return True
    
    # Include all indexes
    if type_ == "index":
        return True
    
    # Include all foreign keys
    if type_ == "foreign_key":
        return True
    
    # Include all unique constraints
    if type_ == "unique_constraint":
        return True
    
    return True


def include_object(object, name, type_, reflected, compare_to):
    """Include specific objects in migrations."""
    # Skip Alembic version table
    if type_ == "table" and name == "alembic_version":
        return False
    
    # Include all other objects
    return True


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    # Create async engine for migrations
    connectable = create_async_engine(
        str(settings.DATABASE_URL),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Use asyncio to run async migrations
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 
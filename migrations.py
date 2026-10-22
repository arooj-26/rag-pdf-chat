"""Additive, versioned SQLite migration. Legacy ownership is intentionally NULL."""
from sqlalchemy import inspect, text
from database import Base


def migrate(engine) -> None:
    if engine.dialect.name != "sqlite":
        raise RuntimeError("This migration runner supports SQLite only.")
    # Create missing tables, then alter existing upstream tables without rebuilding them.
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"))
        if conn.execute(text("SELECT version FROM schema_migrations WHERE version=1")).first():
            return
        additions = {
            "documents": {"owner_id": "VARCHAR(36) REFERENCES users(id)", "source_type": "VARCHAR(16) NOT NULL DEFAULT 'pdf'", "content_hash": "VARCHAR(64)"},
            "conversations": {"owner_id": "VARCHAR(36) REFERENCES users(id)"},
        }
        for table, columns in additions.items():
            existing = {c["name"] for c in inspect(conn).get_columns(table)}
            for name, declaration in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table}_owner_id ON {table}(owner_id)"))
        conn.execute(text("INSERT INTO schema_migrations(version) VALUES (1)"))


if __name__ == "__main__":
    from database import init_db
    init_db()
    print("Additive migrations applied; legacy data retained.")

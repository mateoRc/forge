import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from scripts.database import backup, restore


def test_backup_and_restore_round_trip() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        database = root / "forge.db"
        backup_path = root / "backup.db"
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("CREATE TABLE values_table (value TEXT NOT NULL)")
            connection.execute("INSERT INTO values_table VALUES ('original')")
            connection.commit()

        backup(database, backup_path)
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("UPDATE values_table SET value = 'changed'")
            connection.commit()

        restore(database, backup_path)
        with closing(sqlite3.connect(database)) as connection:
            value = connection.execute(
                "SELECT value FROM values_table"
            ).fetchone()[0]

    assert value == "original"


def test_restore_checkpoints_existing_wal_before_replacement() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        database = root / "forge.db"
        backup_path = root / "backup.db"
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("CREATE TABLE values_table (value TEXT NOT NULL)")
            connection.execute("INSERT INTO values_table VALUES ('original')")
            connection.commit()
        backup(database, backup_path)

        with closing(sqlite3.connect(database)) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("UPDATE values_table SET value = 'changed'")
            connection.commit()

        restore(database, backup_path)

        assert not Path(f"{database}-wal").exists()
        assert not Path(f"{database}-shm").exists()
        with closing(sqlite3.connect(database)) as connection:
            value = connection.execute(
                "SELECT value FROM values_table"
            ).fetchone()[0]

    assert value == "original"

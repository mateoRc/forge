import argparse
import os
import sqlite3
from contextlib import closing
from pathlib import Path


def backup(database: Path, output: Path) -> None:
    if not database.is_file():
        raise ValueError(f"database does not exist: {database}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    _remove(temporary)
    try:
        _copy(database, temporary)
        _verify(temporary)
        os.replace(temporary, output)
    finally:
        _remove(temporary)


def restore(database: Path, source: Path) -> None:
    _verify(source)
    database.parent.mkdir(parents=True, exist_ok=True)
    temporary = database.with_suffix(database.suffix + ".restore")
    _remove(temporary)
    try:
        _copy(source, temporary)
        _verify(temporary)
        _remove(Path(f"{database}-wal"))
        _remove(Path(f"{database}-shm"))
        os.replace(temporary, database)
    finally:
        _remove(temporary)


def _copy(source: Path, target: Path) -> None:
    with closing(sqlite3.connect(source)) as source_connection:
        with closing(sqlite3.connect(target)) as target_connection:
            source_connection.backup(target_connection)


def _verify(database: Path) -> None:
    if not database.is_file():
        raise ValueError(f"database does not exist: {database}")
    with closing(
        sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    ) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise ValueError(f"database integrity check failed: {result}")


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("backup", "restore"):
        command = subparsers.add_parser(action)
        command.add_argument("--database", type=Path, required=True)
        command.add_argument(
            "--output" if action == "backup" else "--input",
            dest="transfer_path",
            type=Path,
            required=True,
        )
    arguments = parser.parse_args()
    if arguments.action == "backup":
        backup(arguments.database, arguments.transfer_path)
    else:
        restore(arguments.database, arguments.transfer_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

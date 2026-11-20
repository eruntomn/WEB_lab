import sqlite3
import sys

from app.config import Settings
from app.migrations import MigrationError, Migrator


def main():
    settings = Settings.from_env()
    migrator = Migrator(settings.db_path, settings.migrations_dir)
    command = sys.argv[1] if len(sys.argv) > 1 else 'status'
    try:
        if command == 'status':
            print(f'Database: {settings.db_path}')
            for version, name, applied in migrator.status():
                print(
                    f'  {version}  {name:<30} {"applied" if applied else "pending"}'
                )
        elif command == 'up':
            done = migrator.up()
            for item in done:
                print(f'Applied migration {item}')
            if not done:
                print('Nothing to apply: schema is up to date')
        elif command == 'down':
            item = migrator.down()
            print(
                f'Rolled back migration {item}'
                if item
                else 'Nothing to roll back'
            )
        else:
            print('Usage: python migrate.py [status|up|down]')
            sys.exit(2)
    except (MigrationError, sqlite3.Error) as exc:
        print(f'Migration error: {exc}')
        sys.exit(1)


if __name__ == '__main__':
    main()

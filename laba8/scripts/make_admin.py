import sys

from app.config import Settings
from app.db import Database
from app.repositories.user_repository import UserRepository


def main():
    if len(sys.argv) != 2:
        print('Usage: python -m scripts.make_admin <email>')
        sys.exit(2)
    repo = UserRepository(Database(Settings.from_env().db_path))
    if repo.set_role(sys.argv[1].lower(), 'admin'):
        print(f'{sys.argv[1]} is now an admin')
    else:
        print('User not found')
        sys.exit(1)


if __name__ == '__main__':
    main()

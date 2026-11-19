# tests/test_email_service.py
from unittest.mock import Mock

import pytest

from app.models import User
from app.services.email_service import EmailService

pytestmark = pytest.mark.unit


@pytest.mark.regression
def test_send_welcome_logs_only_user_id_not_email():
    log = Mock()
    user = User(
        id=7,
        name='Anna',
        email='anna@example.com',
        age=25,
        password_hash='h',
        created_at='x',
    )

    EmailService(log).send_welcome(user)

    log.info.assert_called_once()
    logged = ' '.join(str(arg) for arg in log.info.call_args.args)
    assert '7' in logged
    assert 'anna@example.com' not in logged

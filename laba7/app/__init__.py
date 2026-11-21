import logging

from flask import Flask

from app.config import Settings
from app.db import Database
from app.handlers import create_blueprint, register_common
from app.services import CourseService, RegistrationService, TransferService


def create_app(settings=None):
    settings = settings or Settings.from_env()
    logging.basicConfig(
        level=settings.log_level,
        format='%(asctime)s %(levelname)s %(message)s',
    )
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    log = logging.getLogger('api')

    db = Database(settings.database_url)
    transfer_service = TransferService(db, log)
    registration_service = RegistrationService(db, log)
    course_service = CourseService(db, log)

    app = Flask(__name__)
    app.json.sort_keys = False
    register_common(app, log, settings)
    app.register_blueprint(
        create_blueprint(
            transfer_service, registration_service, course_service
        )
    )
    log.info(
        'App created: port=%s, query warn threshold=%s',
        settings.port,
        settings.query_warn_threshold,
    )
    return app

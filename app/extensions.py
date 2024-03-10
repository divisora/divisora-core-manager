#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Extensions for Flask """

import logging

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from celery import Task, Celery

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

db = SQLAlchemy()
migrate = Migrate()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

def celery_init_app(app: Flask) -> Celery:
    """ Initialize Celery """

    # pylint: disable-next=W0223:abstract-method
    class FlaskTask(Task):
        """ Make celery use the correct Flask app context """
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app

    # # pylint: disable=C0415:import-outside-toplevel,W0611:unused-import
    # from app.tasks import schedule

    celery_app.autodiscover_tasks([
        # 'app.tasks.schedule.check_all_nodes',
        # 'app.tasks.schedule.check_responsetime_cubicles',
        # 'app.tasks.schedule.check_responsetime_nodes',
        'app.tasks.schedule.check_node_compliance',
    ])

    return celery_app

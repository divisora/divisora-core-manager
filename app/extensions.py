#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Extensions for Flask """

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from celery import Task, Celery

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

db = SQLAlchemy()

def celery_init_app(app: Flask) -> Celery:
    """ Initialize Celery """

    # pylint: disable=W0223:abstract-method
    class FlaskTask(Task):
        """ Make celery use the correct Flask app context """
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app

    # pylint: disable=C0415:import-outside-toplevel,W0611:unused-import
    from app.tasks import schedule

    return celery_app

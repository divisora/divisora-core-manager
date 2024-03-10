#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Configuration for Flask app, including extensions """

import os
import secrets
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

MIN_USERNAME_LENGTH = 2
MIN_PASSWORD_LENGTH = 5
CPU_LIMIT = 10

# pylint: disable-next=R0903:too-few-public-methods
class Config():
    """ Base config class """

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex()
    PERMANENT_SESSION_LIFETIME =  timedelta(minutes=60)

    # SQLAlchemy settings
    # pylint: disable-next=C0301:line-too-long
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or 'sqlite:///' + os.path.join(basedir, '../db/app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Celery settings
    CELERY = {
        "broker_url": "redis://redis:6379",
        "result_backend": "redis://redis:6379",
        "broker_connection_retry": False,
        "broker_connection_retry_on_startup": True,
        "task_track_started": True,
        "beat_schedule": {
            'check-node-compliance': {
                'task': 'app.tasks.schedule.check_node_compliance',
                'schedule': 10.0,
            },
        },
    }

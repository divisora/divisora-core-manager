#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Support file

- celery -A run worker --loglevel INFO
- celery -A run beat --loglevel INFO
"""

from app import create_app

flask_app = create_app()
celery = flask_app.extensions["celery"]

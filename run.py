#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Support file

- celery -A run worker --loglevel INFO
- celery -A run beat --loglevel INFO
"""

from waitress import serve

from app import create_app

app = create_app()
celery = app.extensions["celery"]

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000)

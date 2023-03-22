#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import secrets

basedir = os.path.abspath(os.path.dirname(__file__))

from datetime import timedelta

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex()
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME =  timedelta(minutes=60)

    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")    

class DevConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

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

# pylint: disable=R0903:too-few-public-methods
class Config():
    """ Base config class """
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex()
    # pylint: disable=C0301:line-too-long
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME =  timedelta(minutes=60)

# pylint: disable=R0903:too-few-public-methods
class DevConfig(Config):
    """ Development configuration """
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    DEBUG = True

# pylint: disable=R0903:too-few-public-methods
class ProdConfig(Config):
    """ Production configuration """
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    DEBUG = False

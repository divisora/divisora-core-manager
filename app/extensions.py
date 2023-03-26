#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

db = SQLAlchemy()
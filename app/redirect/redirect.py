#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint
from flask import render_template

redirect = Blueprint('redirect', __name__, template_folder='templates')

@redirect.route('/not_ready')
def not_ready():
    return render_template('redirect/not_ready.html')
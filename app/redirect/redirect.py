#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Redirects """

from flask import Blueprint
from flask import render_template
from flask_login import login_required

redirect = Blueprint('redirect', __name__, template_folder='templates')

@redirect.route('/not_ready')
@login_required
def not_ready():
    """ Temporary landing page until cubicle is running """
    return render_template('redirect/not_ready.html')

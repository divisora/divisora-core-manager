#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Blueprint for Auth """

from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from datetime import datetime

import time
import pyotp

from flask import Blueprint
from flask import render_template, redirect, url_for, request, flash, session
from flask import make_response
from flask_login import login_user, logout_user, login_required, current_user

from sqlalchemy import and_

from app.extensions import db
from app.extensions import login_manager
from app.extensions import logger

from app.models.user import User
#from app.models.node import Node
from app.models.cubicle import Cubicle

auth = Blueprint('auth', __name__, template_folder='templates')

@login_manager.user_loader
def load_user(user_id):
    """ Load user object """
    if user_id is not None:
        return User.query.get(user_id)
    return None

@auth.before_request
def update_last_activity():
    """ Update the last time a user were active """
    if not current_user.is_authenticated:
        return
    user = User.query.filter_by(id=current_user.id).first()
    user.last_activity = datetime.utcnow()
    db.session.commit()

# This method is obselete for measurements
# NoVNC have javacript calling this to not timeout sessions
@auth.route('/keepalive')
@login_required
def keep_alive():
    """ Keep alive function """
    now = time.time_ns() / 1000000 # Nano: 10^-9 ; Milli: 10^-3
    req_time = 0.0
    if 't' in request.args:
        req_time = request.args.get('t')
    else:
        url = urlparse(request.headers.get("Origin"))
        query = parse_qs(url.query)
        if 't' in query:
            req_time = query['t']
    try:
        if not isinstance(req_time, float):
            req_time = float(req_time)
    # pylint: disable=W0718:broad-exception-caught
    except Exception as _error:
        # pylint: disable=W0719:broad-exception-raised
        raise Exception("t-argument could not be converted to correct type") from _error

    if req_time <= 0.0:
        print("Could not parse time from client")
        return ""

    try:
        print(f"One-way delay: {now - req_time}ms")
    # pylint: disable=W0718:broad-exception-caught
    except Exception:
        print("t-value could not be parsed as Unix-time")
    return ""

@auth.route('/login', methods=['GET'])
def login():
    """ Default login page """
    return render_template('auth/login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    """ Check if login information is correct """
    username = request.form.get('username')
    password = request.form.get('password')
    option = request.form.get('option')

    user = User.query.filter_by(username=username).first()

    if user is None:
        flash("User do not exist")
        return redirect(url_for('auth.login'))

    totp = pyotp.TOTP(user.totp_key)

    if user.check_password(password) is False and totp.verify(password) is False:
        flash("Password is wrong")
        return redirect(url_for('auth.login'))

    remember = False
    login_user(user, remember=remember)

    session.permanent = True
    session.modified  = True

    match option:
        case 'vnc':
            return redirect(url_for('dashboard.main'))
            # Add cubicle to the logged in user
            # pylint: disable=C0301:line-too-long
            active_cubicle = Cubicle.query.filter(and_(Cubicle.user_id == user.id, Cubicle.active is True)).first()
            if not active_cubicle:
                # pylint: disable=W0511:fixme,C0301:line-too-long
                # TODO: Let the user choose Cubicle instead of assigning the first one in the database
                # pylint: disable=C0301:line-too-long
                cubicle = Cubicle.query.filter(Cubicle.user_id == user.id).order_by(Cubicle.id).first()
                if not cubicle:
                    print("Something really weird happened")
                    return redirect(url_for('auth.login'))
                cubicle.active = True
                try:
                    db.session.commit()
                # pylint: disable=W0718:broad-exception-caught
                except Exception:
                    db.session.rollback()
                else:
                    print(f"Activated cubicle {cubicle.name}")
            else:
                 # pylint: disable=C0301:line-too-long
                print(f"Already have cubicle activated: {active_cubicle.name} - {active_cubicle.active}")

            # pylint: disable=W0511:fixme
            # TODO: sanity check URL for 'next'
            referer = request.headers.get('Referer')
            referer_query = urlparse(referer).query
            next_parameter = parse_qs(referer_query).get('next')

            # Find the next_url path. Either from url or headers.
            if next_parameter is not None and len(next_parameter) > 0:
                next_url = urlparse(next_parameter[0])
            else:
                next_url = urlparse(request.headers.get("Origin"))

            # Add autoconnect argument if it is missing
            query = parse_qs(next_url.query)
            if 'autoconnect' not in query:
                query['autoconnect'] = 'true'
                next_url = next_url._replace(query=urlencode(query, doseq=True))
            if 'resize' not in query:
                query['resize'] = 'remote'
                next_url = next_url._replace(query=urlencode(query, doseq=True))

            logger.info(f"Redirecting to {next_url}")
            print(f"Redirecting to {next_url}")
            resp = make_response(redirect(urlunparse(next_url)))
        case 'admin':
            resp = redirect(url_for('admin.main'))
        case _:
            resp = redirect(url_for('auth.login'))

    return resp


@auth.route('/logout')
@login_required
def logout():
    """ Logout handler """

    # 'reset' timer by lowering it be 1 hour.
    # pylint: disable=W0511:fixme
    # TODO: Probably want a boolean field in model 'user' instead.
    # current_user.active = False
    #current_user.last_activity = datetime.utcnow() - timedelta(hours=1)

    # pylint: disable=C0301:line-too-long
    for cubicle in Cubicle.query.filter(and_(Cubicle.user_id == current_user.id, Cubicle.active is True)):
        cubicle.active = False
        logger.info(f"Removed cubicle '{cubicle.name}' from active state")

    try:
        db.session.commit()
    # pylint: disable=W0718:broad-exception-caught
    except Exception:
        db.session.rollback()

    # Logout the user
    logout_user()

    # Redirect back to login page
    return redirect(url_for('auth.login'))

@auth.route('/authenticate')
@login_required
def authenticate():
    """
    When the user is authenticated, this function returns a referense (X-URL) for Nginx.
    X-URL is used with proxy_pass to relay traffic to the correct NoVNC server and port.

    When the user is NOT authenticated, @login_required decorater will return a Error 401,
    which is what Nginx expects. This is only true if login_manager.login_view is not set.
    """

    resp = make_response("")
    resp.status_code = 200
    resp.headers['X-URL'] = ""

    # X-Auth-Request-Redirect is set by Nginx
    target = request.headers.get('X-Auth-Request-Redirect')
    path = (urlparse(target).path).split('/')

    if path[1] in ['admin', 'api', 'dashboard']:
        del resp.headers['X-URL']
    else:
        url = current_user.get_upstream_novnc()
        if url != "":
            resp.headers['X-URL'] = url
            logger.info(f"Redirecting {current_user.username} -> {resp.headers['X-URL']}")
        else:
            # If the URL is empty, return Error 401 so Nginx can redirect the client correctly.
            resp.status_code = 401
            del resp.headers['X-URL']

    return resp

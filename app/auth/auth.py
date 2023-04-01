#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint
from flask import render_template, redirect, url_for, request, flash, session
from flask import make_response
from flask_login import login_user, logout_user, login_required, current_user

from sqlalchemy import and_

from datetime import datetime
import time

from app.extensions import db

from app.models.user import User
from app.models.node import Node
from app.models.cubicle import Cubicle

from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

auth = Blueprint('auth', __name__, template_folder='templates')
from . import tasks

from app.extensions import login_manager
@login_manager.user_loader
def load_user(user_id):
    if user_id is not None:
        return User.query.get(user_id)
    return None

@auth.before_request
def update_last_activity():
     if not current_user.is_authenticated:
         return
     user = User.query.filter_by(id=current_user.id).first()
     user.last_activity = datetime.utcnow()
     db.session.commit()

@auth.route('/keepalive')
@login_required
def keep_alive():
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
    except Exception:
        raise Exception("t-argument could not be converted to correct type")       
    
    if req_time <= 0.0:
        print("Could not parse time from client")
        return ""

    try:
        print("One-way delay: {}ms".format(now - req_time))
    except Exception:
        print("t-value could not be parsed as Unix-time")
    return ""

@auth.route('/login', methods=['GET'])
def login():
    return render_template('auth/login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    option = request.form.get('option')

    user = User.query.filter_by(username=username).first()

    if user is None:
        flash("User do not exist")
        return redirect(url_for('auth.login'))

    if user.check_password(password) == False:
        flash("Password is wrong")
        return redirect(url_for('auth.login'))

    # TODO: implement remember
    remember = False
    login_user(user, remember=remember)

    session.permanent = True
    session.modified  = True

    match option:
        case 'vnc':
            # Add cubicle to the logged in user
            # TODO: make dynamic.
            # user.add_cubicle('divisora/cubicle-openbox:latest')
            # user.add_cubicle('openbox-latest')
            #print(user)
            active_cubicle = Cubicle.query.filter(and_(Cubicle.user_id == user.id, Cubicle.active == True)).first()
            print(active_cubicle)
            if not active_cubicle:
                # TODO: Let the user choose Cubicle instead of assigning the first one in the database
                cubicle = Cubicle.query.filter(Cubicle.user_id == user.id).order_by(Cubicle.id).first()
                if not cubicle:
                    print("Something really weird happened")
                    return redirect(url_for('auth.login'))
                cubicle.active = True
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                else:
                    print("Activated cubicle {}".format(cubicle.name))
            else:
                print("Already have cubicle activated: {} - {}".format(active_cubicle.name, active_cubicle.active))

            # TODO: sanity check URL for 'next'
            referer = request.headers.get('Referer')
            referer_query = urlparse(referer).query
            next_parameter = parse_qs(referer_query).get('next')

            # Find the next_url path. Either from url or headers.
            if next_parameter != None and len(next_parameter) > 0:
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

            next = urlunparse(next_url)

            resp = make_response(redirect(next))
        case 'admin':
            resp = redirect(url_for('admin.main'))
        case _:
            resp = redirect(url_for('auth.login'))

    return resp

@auth.route('/logout')
@login_required
def logout():
    # Remove all cubicles
    #current_user.remove_cubicles()

    # Logout the user
    logout_user()

    # Redirect back to login page
    return redirect(url_for('auth.login'))

@auth.route('/authenticate')
@login_required
def authenticate():
    # default response to @login_required without login_manager.login_view set is Error 401, same as what nginx wants
    resp = make_response("")
    resp.status_code = 200
    resp.headers['X-URL'] = ""

    target = request.headers.get('X-Auth-Request-Redirect')
    path = (urlparse(target).path).split('/')

    if path[1] == 'admin' or path[1] == 'api':
        pass
    else:
        resp.headers['X-URL'] = current_user.get_upstream_novnc()

    #print("Redirecting user to: {}\n".format(resp.headers['X-URL']))

    return resp


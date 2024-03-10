#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Dashboard """

from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

from flask import Blueprint
from flask import render_template, redirect, url_for, make_response, request
from flask_login import login_required, current_user

from app.extensions import db, logger

from app.models.cubicle import Cubicle

dashboard = Blueprint('dashboard', __name__, template_folder='templates')

@dashboard.route('/', methods=['GET'])
@login_required
def main():
    """ Main dashboard """
    db_cubicles = db.session.execute(db.select(Cubicle)
                                     .where(Cubicle.user_id == current_user.id)
                                     ).all()
    cubicles = []
    for cubicle, in db_cubicles:
        cubicles.append({
            "id": cubicle.id,
            "active": cubicle.active,
            "image": cubicle.image.name,
            "node": cubicle.node.name,
            "network": cubicle.node.network_range,
        })

    return render_template('dashboard/dashboard.html', cubicles=cubicles)

@dashboard.route('/', methods=['POST'])
@login_required
def main_post():
    """ Handle POST request """

    # Get and convert input to an integer
    requested_cubicle_id = request.form.get('cubicle_id')
    try:
        if not isinstance(requested_cubicle_id, int):
            requested_cubicle_id = int(requested_cubicle_id)
    except ValueError:
        return redirect(url_for('dashboard.main'))

    # Get all cubicles for user and verify that requested cubicle is actually own by the user
    cubicles = db.session.execute(db.select(Cubicle)
                                  .where(Cubicle.user_id == current_user.id)
                                  ).all()

    if requested_cubicle_id not in [c.id for c, in cubicles]:
        return redirect(url_for('dashboard.main'))

    cubicle = db.session.query(Cubicle).filter(Cubicle.id==requested_cubicle_id).first()
    cubicle.active = True
    db.session.commit()

    current_user.set_active_cubicle(requested_cubicle_id)

    # # Find the next_url path. Either from url or headers.
    # referer = request.headers.get('Referer')
    # referer_query = urlparse(referer).query
    # next_parameter = parse_qs(referer_query).get('next')

    # if next_parameter is not None and len(next_parameter) > 0:
    #     next_url = urlparse(next_parameter[0])
    # else:
    #     next_url = urlparse(request.headers.get("Origin"))

    next_url = urlparse(request.headers.get("Origin"))
    # Add autoconnect argument if it is missing
    query = parse_qs(next_url.query)
    if 'autoconnect' not in query:
        query['autoconnect'] = 'true'
        next_url = next_url._replace(query=urlencode(query, doseq=True))
    # Add resize argument if it is missing
    if 'resize' not in query:
        query['resize'] = 'remote'
        next_url = next_url._replace(query=urlencode(query, doseq=True))

    logger.info(f"Redirecting {current_user.username} -> {urlunparse(next_url)}")

    return make_response(redirect(urlunparse(next_url)))

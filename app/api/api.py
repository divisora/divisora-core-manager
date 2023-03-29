#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request
from flask_login import login_required

from datetime import datetime, timedelta

from app.models.network import Network
from app.models.cubicle import Cubicle
from app.models.node import Node

from app.extensions import db

api = Blueprint('api', __name__)

@api.route('/')
def api_main():
    return {}

@api.route('/cubicle')
def api_cubicle():
    ret = {
        'no': 0,
        'result': [],
    }

    # Only return values for those cubicles who have a active owner.
    for cubicle in Cubicle.query.filter(Cubicle.user_id != None).all():
        # Ignore cubicles where the user have been idle for more than 1 hour
        # TODO: Set this variable (hours=1) somewhere else.
        if cubicle.user.last_activity < datetime.utcnow() - timedelta(hours=1):
            continue

        network = None
        for n in cubicle.user.networks:
            if n.node.id != cubicle.node.id:
                continue
            network = n.name
            break

        ret['result'].append({
            'name': cubicle.name,
            'image': cubicle.image.image,
            'network': network,
            'node': cubicle.node.name,
            'novnc_port': cubicle.novnc_port,
            'owner': cubicle.user.username,
        })

    ret['no'] = len(ret['result'])
    return ret

@api.route('/network')
def api_network():
    ret = {
        'no': 0,
        'result': [],
    }
    for n in Network.query.all():
        ret['result'].append({
            'name': n.name,
            'range': str(n.ip_range),
            'node': n.node.name,
            'owner': n.user.name if n.user != None else '',
        })

    ret['no'] = len(ret['result'])
    return ret

@api.route('/node')
def api_node():
    ret = {
        'no': 0,
        'result': [],
    }
    for n in Node.query.all():
        ret['result'].append({
            'name': n.name,
            'cubicle_range': str(n.network_range),
            'ip_address': str(n.ip_address),
            'cubicles': [c.name for c in n.cubicles],
            'networks': [str(net.ip_range) for net in n.networks]
        })

    ret['no'] = len(ret['result'])
    return ret
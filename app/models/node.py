#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Node model """

import secrets
from datetime import datetime
from binascii import hexlify

from sqlalchemy_utils import IPAddressType

from app.types.ip_network import IPNetworkType

from app.extensions import db

from app.models.network import Network
from app.models.network import generate_networks

STATUS_UP = 1
STATUS_DOWN = 2
STATUS_ERROR = 3
STATUS_UNKNOWN = 4

StatusTranslation = {
    STATUS_UP: "up",
    STATUS_DOWN: "down",
    STATUS_ERROR: "error",
}

def get_status_string(status_code: int) -> str:
    """ Return string value for status_code """

    # pylint: disable=C0301:line-too-long
    return StatusTranslation[status_code] if status_code in StatusTranslation else StatusTranslation[STATUS_UNKNOWN]

class Node(db.Model):
    """ Base class for Node-model """
    __tablename__ = 'node'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    ip_address = db.Column(IPAddressType)
    domain_name = db.Column(db.String(128))
    port = db.Column(db.Integer)
    api_key = db.Column(db.String(64))
    status = db.Column(db.Integer)
    last_activity = db.Column(db.DateTime(timezone=True))
    response_time = db.Column(db.Float, default=0.0)
    measurements = db.relationship("ResponseTimeNode", backref="node", lazy="noload")
    network_range = db.Column(IPNetworkType)
    cubicles = db.relationship("Cubicle",
                               backref="node",
                               lazy="joined")
    networks = db.relationship("Network",
                               backref="node",
                               lazy="joined",
                               order_by=Network.__table__.columns.id)

    MIN_NOVNC_PORT = 30000
    MAX_NOVNC_PORT = 40000

    def get_available_novnc_port(self):
        """ Return next best available port """
        occupied = False
        for port in range(self.MIN_NOVNC_PORT, self.MAX_NOVNC_PORT):
            # Inefficient but makes the job
            for cubicle in self.cubicles:
                if cubicle.novnc_port != port:
                    continue
                occupied = True

            if occupied:
                occupied = False
                continue

            return port

        return None

    def assign_network(self):
        """ Assign a network """
        for network in self.networks:
            if network.user is not None:
                continue
            return network
        return None

    def __repr__(self):
        return f'<Name "{self.name}", IP "{self.ip_address}">'

def setup(session):
    """ Model setup """
    add_nodes = [
        {
            "name": "Node-1",
            "ip": "192.168.1.179",
            "domain_name": "",
            "port": "80",
            "range": "192.168.0.0/24",
            "api_key": hexlify(secrets.token_bytes(32)).decode("utf-8"),
        }, {
            "name": "Node-2",
            "ip": "192.168.10.183",
            "domain_name": "",
            "port": "10000",
            "range": "192.168.1.0/24",
            "api_key": hexlify(secrets.token_bytes(32)).decode("utf-8"),
        }, {
            "name": "Node-3",
            "ip": "192.168.10.204",
            "domain_name": "node-3",
            "port": "5001",
            "range": "192.168.2.0/24",
            "api_key": hexlify(secrets.token_bytes(32)).decode("utf-8"),
        },
    ]

    for add_node in add_nodes:
        node = Node()
        node.name = add_node["name"]
        node.ip_address = add_node["ip"]
        node.domain_name = add_node["domain_name"]
        node.port = add_node["port"]
        node.network_range = add_node["range"]
        node.api_key = add_node["api_key"]
        node.last_activity = datetime.fromtimestamp(0)
        node.status = STATUS_DOWN

        session.add(node)
        session.commit()

        generate_networks(node, add_node["range"])

    session.commit()

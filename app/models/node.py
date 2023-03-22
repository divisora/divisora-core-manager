#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.extensions import db

from sqlalchemy_utils import IPAddressType
from app.types.ip_network import IPNetworkType

from app.models.network import Network
from app.models.network import generate_networks

class Node(db.Model):
    __tablename__ = 'node'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    ip_address = db.Column(IPAddressType)
    network_range = db.Column(IPNetworkType)
    cubicles = db.relationship("Cubicle", backref="node", lazy="joined")
    networks = db.relationship("Network", backref="node", lazy="joined", order_by=Network.__table__.columns.id)

    MIN_NOVNC_PORT = 30000
    MAX_NOVNC_PORT = 40000

    def get_available_novnc_port(self):
        occupied = False
        for port in range(self.MIN_NOVNC_PORT, self.MAX_NOVNC_PORT):
            # TODO: Waaaay inefficient but will it ever be a problem?
            # Cubicle.query.filter(node_id = self.id).filter(novnc_port = port).first() might be better.
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
        for network in self.networks:
            if network.user != None:
                continue
            return network
        return None

    def __repr__(self):
        return f'<Name "{self.name}", IP "{self.ip_address}">'

def setup(session):
    nodes = [
        {
            "name": "Node-1",
            "ip": "10.0.10.117",
            "range": "192.168.0.0/24",
        }, {
            "name": "Node-2",
            "ip": "10.0.10.135",
            "range": "192.168.1.0/24",
        },        
    ]
    
    for node in nodes:
        n = Node()
        n.name = node["name"]
        n.ip_address = node["ip"]
        n.network_range = node["range"]

        generate_networks(n, node["range"])

        session.add(n)
        session.commit()

    session.commit()

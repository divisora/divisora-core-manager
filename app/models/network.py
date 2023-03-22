#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.extensions import db

from app.types.ip_network import IPNetworkType
from ipaddress import ip_network

class Network(db.Model):
    __tablename__ = 'network'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    ip_range = db.Column(IPNetworkType)
    node_id = db.Column(db.Integer, db.ForeignKey("node.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __repr__(self):
        return f'<Name "{self.name}", Network "{self.ip_range}", Node "{self.node_id}">'

def generate_networks(node, network, prefix=26):
    for subnet in list(ip_network(network).subnets(new_prefix=prefix)):
        n = Network()
        n.name = "Network_{}_{}".format(node.name, str(subnet).replace(".", "_").replace("/", "_"))
        n.ip_range = str(subnet)
        node.networks.append(n)
    db.session.commit()

def setup(session):
    ranges = {
        "Network-1": "192.168.0.0/24",
        "Network-2": "192.168.1.0/24",
        "Network-3": "192.168.2.0/24",
    }

    for name, range in ranges.items():
        n = Network()
        n.name = name
        n.range = range
        session.add(n)

    session.commit()

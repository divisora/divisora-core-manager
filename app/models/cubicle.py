#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.extensions import db

from app.models.node import Node

class Cubicle(db.Model):
    __tablename__ = 'cubicle'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    active = db.Column(db.Boolean, default=False, nullable=False)
    novnc_port = db.Column(db.Integer)
    image_id = db.Column(db.Integer, db.ForeignKey("image.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    node_id = db.Column(db.Integer, db.ForeignKey("node.id"))

    __table_args__ = (
        db.UniqueConstraint(name),
    )
    def __repr__(self):
        return f'<Name "{self.name}", Image "{self.image}", Node "{self.node_id}", Active "{self.active}">'

def setup(session):
    cubicles = [
        {
            "name": "Openbox-1",
            "image": "divisora/cubicle-openbox:latest",
            "network_id": 1,
            "node_id": 1,
        },
        {
            "name": "Openbox-2",
            "image": "divisora/cubicle-openbox:latest",
            "network_id": 2,
            "node_id": 1,
        },        
    ]
    
    for cubicle in cubicles:
        c = Cubicle()
        c.name = cubicle["name"]
        #c.image = cubicle["image"]
        c.node_id = cubicle["node_id"]

        node = Node.query.get(cubicle["node_id"])
        c.novnc_port = node.get_available_novnc_port()

        session.add(c)
        session.commit()

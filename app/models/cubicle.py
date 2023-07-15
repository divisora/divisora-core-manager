#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Cubicle model """

from app.extensions import db

class Cubicle(db.Model):
    """ Base class for Cubicle-model """
    __tablename__ = 'cubicle'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    active = db.Column(db.Boolean, default=False, nullable=False)
    novnc_port = db.Column(db.Integer)
    response_time = db.Column(db.Float, default=0.0)
    measurements = db.relationship("ResponseTimeCubicle", backref="cubicle", lazy="joined")
    image_id = db.Column(db.Integer, db.ForeignKey("image.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    node_id = db.Column(db.Integer, db.ForeignKey("node.id"))

    __table_args__ = (
        db.UniqueConstraint(name),
    )
    def __repr__(self):
        # pylint: disable=C0301:line-too-long
        return f'<Name "{self.name}", Image "{self.image}", Node "{self.node_id}", Active "{self.active}">'

# def setup(session):
#     """ Model setup """
#     cubicles = [
#         {
#             "name": "Openbox-1",
#             "image": "divisora/cubicle-openbox:latest",
#             "network_id": 1,
#             "node_id": 1,
#         },
#         {
#             "name": "Openbox-2",
#             "image": "divisora/cubicle-openbox:latest",
#             "network_id": 2,
#             "node_id": 1,
#         },
#     ]

#     for cubicle in cubicles:
#         c = Cubicle()
#         c.name = cubicle["name"]
#         #c.image = cubicle["image"]
#         c.node_id = cubicle["node_id"]

#         node = Node.query.get(cubicle["node_id"])
#         c.novnc_port = node.get_available_novnc_port()

#         session.add(c)
#         session.commit()

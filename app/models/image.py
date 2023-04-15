#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.extensions import db

class Image(db.Model):
    __tablename__ = 'image'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    image = db.Column(db.String(128))
    cpu_limit = db.Column(db.Integer) # CPU limit = integer, e.g 1
    mem_limit = db.Column(db.String(8)) # Mem limit = string, e.g 2g.       Note: b, k, m, g, to indicate bytes, kilobytes, megabytes, or gigabytes.
    cubicles = db.relationship("Cubicle", backref="image", lazy="joined")

    def __repr__(self):
        return f'<Name "{self.name}", Image "{self.image}">'

def setup(session):
    images = [
        {
            "name": "openbox-latest",
            "image": "divisora/cubicle-openbox:latest",
            "cpu_limit": 1,
            "mem_limit": "1g",
        }, {
            "name": "ubuntu-latest",
            "image": "divisora/cubicle-ubuntu:latest",
            "cpu_limit": 1,
            "mem_limit": "1g",
        },
    ]
    
    for image in images:
        i = Image()
        i.name = image["name"]
        i.image = image["image"]
        i.cpu_limit = image["cpu_limit"]
        i.mem_limit = image["mem_limit"]
       
        session.add(i)
        session.commit()

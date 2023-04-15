#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.extensions import db

from flask_login import UserMixin

from sqlalchemy_utils import PasswordType
from sqlalchemy_utils import force_auto_coercion
#from sqlalchemy.sql import func
from sqlalchemy import and_

from datetime import datetime, timedelta
import pyotp

from app.models.cubicle import Cubicle
from app.models.node import Node
from app.models.image import Image

force_auto_coercion()

class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    username = db.Column(db.String(64), nullable=False)
    password = db.Column(PasswordType(
        schemes=[
            'pbkdf2_sha512',
        ],
    ))
    totp_enforce = db.Column(db.Boolean, default=True, nullable=False)
    totp_key = db.Column(db.String(32))
    admin = db.Column(db.Boolean, default=False, nullable=False)
    last_activity = db.Column(db.DateTime(timezone=True))
    cubicles = db.relationship("Cubicle", backref="user", lazy="joined")
    networks = db.relationship("Network", backref="user", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint(username),
    )

    def check_password(self, password):
        return self.password == password

    def add_cubicle(self, image_name):
        image = Image.query.filter_by(name=image_name).order_by(Image.id).first()
        if image == None:
            print("Something went wrong while searching for the image. Maybe missing?")
            return

        # Check if image is already used.
        # for cubicle in self.cubicles:
        #     if image.id == cubicle.image_id:
        #         return

        c = Cubicle()
        c.name = "{}-{}".format(image.name, self.username)
        i = 1
        while Cubicle.query.filter_by(name=c.name).first() is not None:
            c.name = "{}-{}-duplicate-{}".format(image.name, self.username, i)
            i += 1
        c.image_id = image.id
        c.node_id = (Node.query.get(1)).id # TODO: Do not assume id == 1. Query health and dynamic allocate cubicle to most fitted node. Or use sticky settings. 
        if c.node_id is None:
            print("Something went wrong with the networks/nodes")
            return
        c.novnc_port = (Node.query.get(c.node_id)).get_available_novnc_port()
        self.cubicles.append(c)
        try:
            db.session.commit()
        except Exception as e:
            print(e)
            db.session.rollback()
        
        return True

    def remove_cubicle(self, id):
        # Return if not type 'int' or below 1
        if not isinstance(id, int) or id < 1:
            return

        cubicle = Cubicle.query.get(id)
        if cubicle is None:
            return

        self.cubicles.remove(cubicle)

        try:
            db.session.commit()
        except Exception as e:
            print(e)
            db.session.rollback()

    def remove_cubicles(self):
        cubicle_ids = []
        # Due to some race-condition we cannot remove while looping the same iterator.
        # Get the ids, add them to a list and then remove them.
        for cubicle in self.cubicles:
            cubicle_ids.append(cubicle.id)

        for id in cubicle_ids:
            self.remove_cubicle(id)

    def get_upstream_novnc(self):
        cubicle = Cubicle.query.filter(and_(Cubicle.user_id == self.id, Cubicle.active == True)).order_by(Cubicle.id).first()

        if not cubicle or not cubicle.node:
            return ""

        return "{}:{}".format(str(cubicle.node.ip_address), cubicle.novnc_port)

    def assign_network(self):
        for node in Node.query.all():
            node.assign_network(self)

    def __repr__(self):
        #return f'<Name "{self.name}", Username "{self.username}", Password: "{self.password}">, Cubicles "{\" \".join([c.name for c in self.cubicles])}"'
        return '<Name "{}", Username "{}", Cubicles "{}">'.format(self.name, self.username, ", ".join([c.name for c in self.cubicles]))

def setup(session):
    users = [
        {
            "name": "Admin",
            "username": "admin",
            "password": "admin",
            "admin": True,
            "image": "openbox-latest",        
        }, {
            "name": "Bob Bobsson",
            "username": "user1",
            "password": "test",
            "admin": False,
            "image": "openbox-latest",
        }, {
            "name": "Dave Davidsson",
            "username": "user2",
            "password": "test",
            "admin": True,
            "image": "ubuntu-latest",
        },        
    ]
    try:
        for user in users:
            u = User()
            u.name = user["name"]
            u.username = user["username"]
            u.password = user["password"]
            u.totp_key = pyotp.random_base32()
            u.admin = user["admin"]
            # TODO: set enforce for all but only after admin have logged in once and changed it.
            if u.username != "admin":
                u.totp_enforce = True
            u.last_activity = datetime.fromtimestamp(0)
            for node in Node.query.all():
                network = node.assign_network()
                if network == None:
                    print("Unable to assign network to user on {}. No subnets left?".format(node.name))
                    continue
                u.networks.append(network)
            session.add(u)
            session.commit()
            u.add_cubicle(user["image"])

    except Exception as e:
        print(e)

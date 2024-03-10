#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" User model """

from datetime import datetime
from urllib.parse import urlparse, urlunparse

from flask import session
from flask_login import UserMixin, current_user

from sqlalchemy_utils import PasswordType
from sqlalchemy_utils import force_auto_coercion
from sqlalchemy import and_
from sqlalchemy import event

import pyotp

from app.extensions import db
from app.models.cubicle import Cubicle
from app.models.events import EventLog
from app.models.node import Node
from app.models.image import Image

force_auto_coercion()

class User(UserMixin, db.Model):
    """ Base class for User-model """
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
    events = db.relationship("EventLog", backref="user", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint(username),
    )

    active_cubicle_id = None

    def check_password(self, password):
        """ Check if input password match """
        return self.password == password

    def add_cubicle(self, image_name, node_id: int = 1, insecure: bool = False, use_alt_novnc_name: bool = False):
        """ Add cubicle to user """
        image = Image.query.filter_by(name=image_name).order_by(Image.id).first()
        if image is None:
            print("Something went wrong while searching for the image. Maybe missing?")
            return False

        # Check if image is already used.
        # for cubicle in self.cubicles:
        #     if image.id == cubicle.image_id:
        #         return

        c = Cubicle()
        c.name = f"{image.name}-{self.username}"
        i = 1
        while Cubicle.query.filter_by(name=c.name).first() is not None:
            c.name = f"{image.name}-{self.username}-duplicate-{i}"
            i += 1
        c.image_id = image.id
        # TODO: Do not assume id == 1.
        # Query health and dynamic allocate cubicle to most fitted node. Or use sticky settings.
        c.node_id = (Node.query.get(node_id)).id
        if c.node_id is None:
            print("Something went wrong with the networks/nodes")
            return False
        
        # Insecure defines if the connection is using HTTP or HTTPS
        c.insecure = insecure

        # Local / Debug option
        if use_alt_novnc_name:
            c.novnc_name = c.name + "_novnc"
        c.novnc_port = (Node.query.get(c.node_id)).get_available_novnc_port()

        self.cubicles.append(c)
        try:
            db.session.commit()
        # pylint: disable=W0719:broad-exception-caught
        except Exception as _error:
            print(_error)
            db.session.rollback()

        return True

    def remove_cubicle(self, _id):
        """ Remove cubicle with '_id' from user """

        # Return if not type 'int' or below 1
        if not isinstance(_id, int) or _id < 1:
            return

        cubicle = Cubicle.query.get(_id)
        if cubicle is None:
            return

        self.cubicles.remove(cubicle)

        try:
            db.session.commit()
        # pylint: disable=W0719:broad-exception-caught
        except Exception as _error:
            print(_error)
            db.session.rollback()

    def remove_cubicles(self):
        """ Remove all cubicles from user"""

        cubicle_ids = []
        # Due to some race-condition we cannot remove while looping the same iterator.
        # Get the ids, add them to a list and then remove them.
        for cubicle in self.cubicles:
            cubicle_ids.append(cubicle.id)

        for _id in cubicle_ids:
            self.remove_cubicle(_id)

    def set_active_cubicle(self, cubicle_id: int = None) -> bool:
        """ Set id for the active cubicle """

        if cubicle_id not in [c.id for c in self.cubicles]:
            return False

        session["cubicle_id"] = cubicle_id
        return True

    def get_upstream_novnc(self) -> str:
        """ Get the upstream adress to the NoVNC """

        # # pylint: disable=C0121:singleton-comparison
        # cubicle = Cubicle.query.filter(
        #     and_(
        #         Cubicle.user_id == self.id,
        #         Cubicle.active == True,
        #     )).order_by(Cubicle.id).first()

        # if not cubicle or not cubicle.node:
        #     return ""

        upstream_url = urlparse('')

        for cubicle in self.cubicles:
            if cubicle.id != session["cubicle_id"]:
                continue

            scheme = "http" if cubicle.insecure else "https"

            if cubicle.novnc_name != "":
                netloc = cubicle.novnc_name
            else:
                netloc = cubicle.node.domain_name if cubicle.node.domain_name != "" else str(cubicle.node.ip_address)
            netloc += f":{cubicle.novnc_port}"
            
            upstream_url = upstream_url._replace(scheme=scheme, netloc=netloc)

            # Always break if cubicle is found
            break

        return urlunparse(upstream_url)

    def assign_network(self):
        """ Assign a network to user """

        for node in Node.query.all():
            node.assign_network(self)

    def __repr__(self):
        """ __repr__ for User """
        cubicles = ", ".join([c.name for c in self.cubicles])
        return f'<Name "{self.name}", Username "{self.username}", Cubicles "{cubicles}">'

def get_current_user_id() -> int|None:
    """ Get id from current_user """
    # Because of the wrapping of current_user, 'current_user is None' do not work
    # current_user = LocalProxy(lambda: _get_user())
    # pylint: disable=C0121:singleton-comparison
    if current_user == None:
        user = User.query.filter_by(username="system").first()
        return user.id

    if hasattr(current_user, "is_anonymous") and current_user.is_anonymous is True:
        anonymous = User.query.filter_by(username="anonymous").first()
        return anonymous.id

    if hasattr(current_user, "is_authenticated") and current_user.is_authenticated is True:
        return current_user.id

    return None

@event.listens_for(User, "after_insert")
def insert_user_log(_, connection, target):
    """ Add eventlog """

    # Get the ID from whom the event was created
    creator_id = get_current_user_id()
    if creator_id is None:
        print("Something bad happened")

    # Add an event to the event-log
    event_log_table = EventLog.__table__
    connection.execute(
        event_log_table.insert().values(
            user_id=creator_id,
            type="user",
            text=f"Adding user '{target.username}'"
        )
    )

# @event.listens_for(User, "after_update")
@event.listens_for(User, "after_delete")
def delete_user_log(_, connection, target):
    """ Add eventlog """

    # Get the ID from whom the event was created
    creator_id = get_current_user_id()
    if creator_id is None:
        print("Something bad happened")

    # Add an event to the event-log
    event_log_table = EventLog.__table__
    connection.execute(
        event_log_table.insert().values(
            user_id=creator_id,
            type="user",
            text=f"Deleted user '{target.username}'"
        )
    )

def setup(session):
    """ Model setup """
    users = [
        {
            "name": "Built-in system",
            "username": "system",
            "password": pyotp.random_base32(),
            "admin": True,
        }, {
            "name": "Built-in Anonymous",
            "username": "anonymous",
            "password": pyotp.random_base32(),
            "admin": False,
        }, {
            "name": "Built-in Admin",
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
            u.admin = user["admin"]
            u.last_activity = datetime.fromtimestamp(0)

            # Settings for all users but "system"
            if u.username not in ["system", "anonymous"]:
                u.totp_key = pyotp.random_base32()
                if u.username != "admin":
                    u.totp_enforce = True
                for node in Node.query.all():
                    network = node.assign_network()
                    if network is None:
                        print(f"Unable to assign network to user on {node.name}. No subnets left?")
                        continue
                    u.networks.append(network)
            session.add(u)
            session.commit()
            if u.username not in ["system", "anonymous"]:
                u.add_cubicle(user["image"], 1)
                u.add_cubicle(user["image"], 2)
                u.add_cubicle(user["image"], 3, insecure = True, use_alt_novnc_name = True)
    # pylint: disable=W0719:broad-exception-caught
    except Exception as _error:
        print(_error)

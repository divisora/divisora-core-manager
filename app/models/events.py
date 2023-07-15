#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" EventLog model """

from datetime import datetime

from app.extensions import db

class EventLog(db.Model):
    """ Base class for EventLog-model """
    __tablename__ = 'event_log'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(32))
    text = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __repr__(self):
        # pylint: disable=C0301:line-too-long
        return f'<User "{self.user.username}", Timestamp "{self.timestamp}", Text "{self.text}">'

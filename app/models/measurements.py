#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Measurement model """

import random

from datetime import datetime, timedelta

from app.extensions import db
from app.models.cubicle import Cubicle

# pylint: disable=R0903:too-few-public-methods
class Measurement(db.Model):
    """ Base class for Measurement-model """
    __tablename__ = 'measurement'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    __mapper_args__ = {
        "polymorphic_identity": "measurement",
    }

# pylint: disable=R0903:too-few-public-methods
class ResponseTimeCubicle(Measurement):
    """ Response time class, which inherits Measurement """
    __tablename__ = 'response_time_cubicle'
    id = db.Column(db.Integer, db.ForeignKey('measurement.id'), primary_key=True)
    rtt = db.Column(db.Float)
    method = db.Column(db.String(32))
    cubicle_id = db.Column(db.Integer, db.ForeignKey("cubicle.id"))

    __mapper_args__ = {
        "polymorphic_identity": "response_time_cubicle",
    }

def setup(session):
    """ Model setup """
    for cubicle in Cubicle.query.all():
        for i in range(50):
            response_time = ResponseTimeCubicle()
            response_time.rtt = random.randint(1, 100)
            response_time.method = "http"
            response_time.timestamp = datetime.utcnow() - timedelta(minutes=i)

            cubicle.measurements.append(response_time)
            session.add(response_time)

        session.commit()

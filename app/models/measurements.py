#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Measurement model """

import random
from io import BytesIO
from base64 import b64encode
from datetime import datetime, timedelta

from app.extensions import db
from app.models.cubicle import Cubicle
from app.models.node import Node

# Disable C0411:wrong-import-order due to the need of matplotlib.use('Agg')-fix
# Will otherwise cause all other imports to be "wrong"

# pylint: disable=C0411:wrong-import-order
import matplotlib
# https://stackoverflow.com/questions/49921721/runtimeerror-main-thread-is-not-in-main-loop-with-matplotlib-and-flask
matplotlib.use('Agg')
# pylint: disable=C0411:wrong-import-order,C0413:wrong-import-position
import matplotlib.dates as md
# pylint: disable=C0411:wrong-import-order,C0413:wrong-import-position
import matplotlib.pyplot as plt

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

# pylint: disable=R0903:too-few-public-methods
class ResponseTimeNode(Measurement):
    """ Response time class, which inherits Measurement """
    __tablename__ = 'response_time_node'
    id = db.Column(db.Integer, db.ForeignKey('measurement.id'), primary_key=True)
    rtt = db.Column(db.Float)
    method = db.Column(db.String(32))
    node_id = db.Column(db.Integer, db.ForeignKey("node.id"))

    __mapper_args__ = {
        "polymorphic_identity": "response_time_node",
    }

# pylint: disable=C0301:line-too-long
def create_timestamp_graph(x_axis: list, y_axis: list, x_axis_name: str, y_axis_name: str, title: str) -> str|None:
    """ Create a graph with timestamp on x-axis """
    graph = None

    figure, axes = plt.subplots(figsize=(8,3), dpi=300)

    # Set titles and make them white
    axes.set_title(title, color="#ffffff")
    axes.set_xlabel(x_axis_name, color="#ffffff")
    axes.set_ylabel(y_axis_name, color="#ffffff")

    # Set the x-values/y-values/border color to white
    axes.tick_params(color="#ffffff", labelcolor="#ffffff")
    for spine in axes.spines.values():
        spine.set_edgecolor("#ffffff")
    xfmt = md.DateFormatter("%H:%M")
    axes.xaxis.set_major_formatter(xfmt)
    axes.plot(x_axis, y_axis)

    figure.tight_layout()

    with BytesIO() as buffer:
        figure.savefig(buffer, format="png", transparent=True)
        graph = b64encode(buffer.getbuffer()).decode("ascii")

    return graph


def setup(session):
    """ Model setup """
    for cubicle in Cubicle.query.all():
        for i in range(1440):
            response_time = ResponseTimeCubicle()
            response_time.rtt = random.randint(1, 50)
            response_time.method = "http"
            response_time.timestamp = datetime.utcnow() - timedelta(minutes=i)

            cubicle.measurements.append(response_time)
            session.add(response_time)

        session.commit()

    for node in Node.query.all():
        for i in range(1440):
            response_time = ResponseTimeNode()
            response_time.rtt = random.randint(1, 50)
            response_time.method = "http"
            response_time.timestamp = datetime.utcnow() - timedelta(minutes=i)

            node.measurements.append(response_time)
            session.add(response_time)

        session.commit()

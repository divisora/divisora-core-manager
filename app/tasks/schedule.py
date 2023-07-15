#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Celery scheduled tasks """

import socket
import time
import urllib.request

from celery import current_app as current_celery_app

from app.extensions import db

from app.models.cubicle import Cubicle
from app.models.node import Node
from app.models.node import STATUS_UP, STATUS_ERROR, STATUS_DOWN

@current_celery_app.task()
def check_all_nodes():
    """ Check if all nodes are alive """
    for node in Node.query.all():
        try:
            with urllib.request.urlopen(f"http://{node.ip_address}", timeout=2) as response:
                if response.getcode() == 200:
                    node.status = STATUS_UP
                else:
                    node.status = STATUS_ERROR
        except (urllib.error.HTTPError, urllib.error.URLError):
            node.status = STATUS_DOWN
        except socket.timeout:
            node.status = STATUS_DOWN

    db.session.commit()

@current_celery_app.task()
def check_responsetime_cubicles():
    """ Check which response time a cubicle has """
    for cubicle in Cubicle.query.all():
        start = time.perf_counter()
        request_time = 0.0
        try:
            # pylint: disable=C0301:line-too-long
            print(f"Measure response time for {cubicle.name} ({cubicle.node.ip_address}:{cubicle.novnc_port})")
            # pylint: disable=C0301:line-too-long
            with urllib.request.urlopen(f"https://{cubicle.node.ip_address}:{cubicle.novnc_port}", timeout=2) as _:
                request_time = time.perf_counter() - start
        # pylint: disable=W0718:broad-exception-caught
        except Exception:
            request_time = 9999.0
        finally:
            print(f"Request time for {cubicle.name} is {request_time:0f}ms")

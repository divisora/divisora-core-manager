#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Celery scheduled tasks """

import json
import socket
import time
import urllib.request
from http.cookiejar import CookieJar
from datetime import datetime

from celery import shared_task
from celery import current_app as current_celery_app

from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.extensions import db, logger

from app.models.cubicle import Cubicle
from app.models.network import Network
from app.models.node import Node
from app.models.node import STATUS_UP, STATUS_ERROR, STATUS_DOWN
from app.models.measurements import ResponseTimeCubicle, ResponseTimeNode

def construct_node_url(node: Node) -> str:
    """ Construct the URL for a Node """
    if node.domain_name != "":
        url = f"http://{node.domain_name}:{node.port}"
    else:
        url = f"http://{node.ip_address}:{node.port}"
    return url

@shared_task(bind=True)
# pylint: disable-next=W0613:unused-argument
def check_all_nodes(self):
    """ Check if all nodes are alive """
    nodes = db.session.execute(select(Node)).scalars().all()
    for node in nodes:
        logger.info(f"Checking if {node.name} ({url}) is alive")
        url = construct_node_url(node)
        try:
            with urllib.request.urlopen(f"{url}", timeout=2) as response:
                if response.getcode() == 200:
                    node.status = STATUS_UP
                else:
                    node.status = STATUS_ERROR
        except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout):
            node.status = STATUS_DOWN

    db.session.commit()

# @current_celery_app.task()
# def check_responsetime_cubicles():
#     """ Check which response time a cubicle has """

#     for cubicle in Cubicle.query.all():
#         # pylint: disable=C0301:line-too-long
#         print(f"Measure response time for {cubicle.name} ({cubicle.node.ip_address}:{cubicle.novnc_port})")
#         measurement = 0.0

#         start = time.perf_counter()
#         try:
#             # pylint: disable=C0301:line-too-long
#             with urllib.request.urlopen(f"https://{cubicle.node.ip_address}:{cubicle.novnc_port}", timeout=2) as _:
#                 measurement = time.perf_counter() - start
#         # pylint: disable=W0718:broad-exception-caught
#         except Exception:
#             measurement = 9999.0
#         finally:
#             print(f"Request time for {cubicle.name} is {measurement:0f}ms")

#         response_time = ResponseTimeCubicle()
#         response_time.rtt = measurement
#         response_time.method = "http"
#         response_time.timestamp = datetime.utcnow()

#         cubicle.measurements.append(response_time)

#         db.session.add(response_time)
#         db.session.commit()

# @current_celery_app.task()
# def check_responsetime_nodes():
#     """ Check which response time a node has """

#     for node in Node.query.all():
#         # pylint: disable=C0301:line-too-long
#         print(f"Measure response time for {node.name} ({node.ip_address})")
#         measurement = 0.0

#         start = time.perf_counter()
#         try:
#             # pylint: disable=C0301:line-too-long
#             with urllib.request.urlopen(f"http://{node.ip_address}", timeout=2) as _:
#                 measurement = time.perf_counter() - start
#         # pylint: disable=W0718:broad-exception-caught
#         except Exception:
#             measurement = 9999.0
#         finally:
#             print(f"Request time for {node.name} is {measurement:0f}ms")

#         response_time = ResponseTimeNode()
#         response_time.rtt = measurement
#         response_time.method = "http"
#         response_time.timestamp = datetime.utcnow()

#         node.measurements.append(response_time)

#         db.session.add(response_time)
#         db.session.commit()

@shared_task(bind=True)
def check_node_compliance(self):
    """ Check if node is compliant """
    db.session.query(Node)
    for node in Node.query.all():
        if node.domain_name != "":
            url = f"http://{node.domain_name}:{node.port}"
        else:
            url = f"http://{node.ip_address}:{node.port}"

        logger.info(f"Checking status of {node.name} ({url})")
        # Compare running / expected cubicles
        body = None
        try:
            # pylint: disable=C0301:line-too-long
            with urllib.request.urlopen(f"{url}/api/v1/cubicle", timeout=2) as response:
                body = response.read().decode("utf-8")
                logger.info(f"{body}")
        except urllib.error.HTTPError as _err:
            error_body = _err.read().decode("utf-8")
            logger.info(f"{_err} - {error_body}")
            continue
        except urllib.error.URLError as _err:
            logger.info(f"{_err}")
            continue
        except socket.timeout:
            logger.info(f"Timed out while checking access to {node.name} ({node.ip_address}:{node.port})")
            continue

        json_data = json.loads(body)
        json_data = json_data["results"] if "results" in json_data else []
        running_cubicles = [cubicle.get("name") for cubicle in json_data]

        stmt = (
            select(Cubicle)
            .options(selectinload(Cubicle.node))
            .where(Cubicle.active is True, Cubicle.node_id == node.id)
        )
        active_cubicles = db.session.execute(stmt).scalars().all()

        # Check if all expecting cubicles are running. If not, start it.
        for cubicle in active_cubicles:
            if cubicle.name in running_cubicles:
                continue
            logger.info(f"{cubicle.name} is not running. lets start it!")

            # Check if network exist
            stmt = select(Network).where(
                Network.node_id == node.id,
                Network.user_id == cubicle.user_id
            )
            network = db.session.execute(stmt).scalars().first()
            try:
                network_exist = _check_network_exist(network, node, url)
            except Exception as _err:
                logger.info(_err)
                continue
            if not network_exist:
                # {
                #  "name": "net-1",
                #  "driver": "bridge",
                #  "ipam": {
                #     "driver": "default",
                #     "pool_configs": [{
                #         "subnet": "192.168.0.0/24",
                #         "gateway": "192.168.0.254"
                #     }],
                #     "options": {}
                #  }
                # }
                logger.info("Network do not exist. lets start it!")
                data = {
                    "name": network.name,
                    "driver": "bridge",
                    "ipam": {
                        "driver": "default",
                        "pool_configs": [{
                            "subnet": str(network.ip_range),
                            "gateway": str(network.ip_range[-2])
                        }],
                        "options": {}
                    }
                }
                try:
                    data = json.dumps(data).encode("utf-8")
                    req = urllib.request.Request(f"{url}/api/v1/network",
                                                headers={"Content-Type": "application/json"},
                                                data=data,
                                                method='PUT')
                    with urllib.request.urlopen(req, timeout=2) as response:
                        body = response.read().decode("utf-8")
                        logger.info(f"Network {network.name} started! {body}")
                except urllib.error.HTTPError as _err:
                    error_body = _err.read().decode("utf-8")
                    logger.info(f"{_err} - {error_body}")
                    continue
                except urllib.error.URLError as _err:
                    logger.info(f"{_err}")
                    continue
                except socket.timeout:
                    logger.info(f"Timed out while adding network ({network.name}) on {node.name} ({node.ip_address}:{node.port})")
                    continue
            # Start cubicle
            # {
            #  "hostname": "machine-1.domain.internal",
            #  "name": "machine-1",
            #  "owner": "user-1",
            #  "image": "divisora/cubicle-ubuntu:latest",
            #  "network": "net-1",
            #  "caps": [],
            #  "environments": {},
            #  "novnc_port": 30000,
            #  "ports": {},
            #  "volumes": []
            # }
            data = {
                "name": cubicle.name,
                "hostname": cubicle.name + ".domain.internal", # Make domain dynamic!
                "owner": cubicle.user.name,
                "image": cubicle.image.image,
                "network": network.name,
                "caps": [],
                "environments": {},
                "novnc_port": cubicle.novnc_port,
                "ports": {},
                "volumes": []
            }
            try:
                data = json.dumps(data).encode("utf-8")
                req = urllib.request.Request(f"{url}/api/v1/cubicle",
                                             headers={"Content-Type": "application/json"},
                                             data=data,
                                             method='PUT')
                # Are 10 seconds too much?
                with urllib.request.urlopen(req, timeout=10) as response:
                    body = response.read().decode("utf-8")
                    logger.info(f"Cubicle {cubicle.name} started! {body}")
            except urllib.error.HTTPError as _err:
                error_body = _err.read().decode("utf-8")
                logger.info(f"{_err} - {error_body}")
                continue
            except urllib.error.URLError as _err:
                logger.info(f"{_err}")
                continue
            except socket.timeout:
                logger.info(f"Timed out while adding cubicle ({cubicle.name}) on {node.name} ({node.ip_address}:{node.port})")
                continue

        # Check if any cubicle is still running when it should have been stopped / removed
        for cubicle in running_cubicles:
            if cubicle in active_cubicles:
                continue
            print(f"{cubicle} is still running. lets remove it!")

# Make node or url the main way of getting the address
def _check_network_exist(network: Network, node: Node, url: str) -> bool:
    try:
        # pylint: disable=C0301:line-too-long
        with urllib.request.urlopen(f"{url}/api/v1/network", timeout=2) as response:
            if response.getcode() != 200:
                raise Exception("Did not get a 200 return code")
            body = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as _err:
        raise _err
    except socket.timeout as _err:
        raise Exception(f"Timed out while check networks for {node.name} ({node.ip_address}:{node.port})") from _err

    json_data = json.loads(body)
    networks = json_data["results"] if "results" in json_data else []
    for name in [network.get("name") for network in networks]:
        if name == network.name:
            return True
    return False

def login(url: str) -> str|None:
    """ Login and return session cookie """

    cookie_jar = CookieJar()
    try:
        with urllib.request.urlopen(f"{url}/api/v1/login", timeout=2) as response:
            if response.getcode() != 200:
                return None
            cookies = cookie_jar.make_cookies(response, None)
    except (urllib.error.HTTPError, urllib.error.URLError):
        print("Got http error")
        return None
    except socket.timeout:
        print("Timed out")
        return None

    for cookie in cookies:
        if cookie.name != "session":
            continue
        print(f"Session key is: {cookie.value}")
        return cookie.value

    return None

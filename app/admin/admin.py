#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request
from flask import render_template
from flask_login import login_required

from app.models.user import User
from app.models.node import Node
from app.models.image import Image
from app.models.cubicle import Cubicle

import re

from app.extensions import db
from app.models.network import generate_networks

from ipaddress import ip_network, ip_address

admin = Blueprint('admin', __name__, template_folder='templates')

@admin.route('/admin')
#@login_required
def main():
    # Get information about users
    users = []
    for user in User.query.all():
        name = user.name if user.name is not None else ""
        username = user.username if user.username is not None else ""
        users.append({
            'id': user.id,
            'name': name,
            'username': username,
            'admin': user.admin,
        })

    # Get information about nodes
    nodes = []
    for node in Node.query.all():
        name = node.name if node.name is not None else ""
        nodes.append({
            'id': node.id,
            'name': name,
            'ip': node.ip_address,
            'network_range': node.network_range,
        })

    # Get information about images
    images = []
    for image in Image.query.all():
        name = image.name if image.name is not None else ""
        source = image.image if image.image is not None else ""
        cpu_limit = image.cpu_limit if image.cpu_limit is not None else "no limit"
        mem_limit = image.mem_limit if image.mem_limit is not None else "no limit"
        images.append({
            'id': image.id,
            'name': name,
            'source': source,
            'cpu_limit': cpu_limit,
            'mem_limit': mem_limit,
        })

    # Get information about cubicles
    cubicles = []
    for cubicle in Cubicle.query.all():
        name = cubicle.name if cubicle.name is not None else "Unknown"
        user = cubicle.user.name if cubicle.user is not None else "Unknown"
        image_name = cubicle.image.name if cubicle.image is not None else "Unknown"
        node_name = cubicle.node.name if cubicle.node is not None else "Unknown"
        novnc_port = cubicle.novnc_port
        network = "Unknown"
        last_activity = "Unknown"

        if cubicle.user is not None:
            for n in cubicle.user.networks:
                if n.node is None or cubicle.node is None:
                    continue
                if n.node.id != cubicle.node.id:
                    continue
                network = n.name
                break

            last_activity = cubicle.user.last_activity
        cubicles.append({
            'id': cubicle.id,
            'name': name,
            'user': user, 
            'image': image_name,
            'node': node_name,
            'novnc_port': novnc_port,
            'network': network,
            'last_activity': last_activity,
        })
        
    return render_template('admin/main.html', users=users, nodes=nodes, images=images, cubicles=cubicles)

@admin.route('/admin/modal/<type>', methods=['GET'])
def modal_get(type):
    try:
        if not isinstance(type, str):
            type = str(type)    
    except Exception as e:
        return render_template('admin/modal/error.html')

    obj = {}
    match type:
        case 'user':
            img = Image.query.all()
            obj['images'] = {i.name: False for i in img}
        case 'node':
            pass
        case 'image':
            pass
        case 'cubicle':
            users = User.query.all()
            obj['users'] = {u.name: False for u in users}

            images = Image.query.all()
            obj['images'] = {i.name: False for i in images}

            nodes = Node.query.all()
            obj['nodes'] = {n.name: False for n in nodes}

        case _:
            return _modal_status_message('error', 'Unknown type')

    return render_template('admin/modal/{}.html'.format(type), obj=obj)

@admin.route('/admin/modal/<type>', methods=['POST'])
def modal_add(type):
    # TODO: Double normalize, not optimal but fine for now
    # It is for 'match type' which could brake with bad values
    type, _ = _normalize_input_variables(type, 0)
    obj = _get_type(type)

    if obj is None:
        return render_template('admin/modal/error.html')
    
    return_msg = ""

    match type:
        case 'user':
            user = obj()
            # Get username, check if it exist, sanitiy check the string and then add it to user.
            username = request.form.get('username')
            if not username:
                return _modal_status_message('error', 'Username is missing')
            if not re.search("^[a-zA-Z0-9_-]+$", username):
                return _modal_status_message('error', 'Username includes bad characters')
            if obj.query.filter_by(username=username).first():
                return _modal_status_message('error', 'Username is already in use')
            user.username = username

            # Get full name, sanitiy check the string and then add it to user
            name = request.form.get('full_name')
            if not name:
                return _modal_status_message('error', 'Full name is missing')
            if not re.search("^[a-zA-Z0-9\s]+$", name):
                return _modal_status_message('error', 'Full name includes bad characters')
            user.name = name

            # Get password and then add it to user
            password = request.form.get('new_password')
            if not password:
                return _modal_status_message('error', 'Password is missing')
            if not re.search("^[a-zA-Z0-9\s]+$", name):
                return _modal_status_message('error', 'Password contains forbidded characters')
            user.password = password

            for node in Node.query.all():
                network = node.assign_network()
                if network == None:
                    print("Unable to assign network to user on {}. No subnets left?".format(node.name))
                    continue
                user.networks.append(network)

            # Must add/commit before add_cubicle()
            db.session.add(user)
            db.session.commit()

            # Add cubicle
            # TODO: Use an ID instead of name
            image_name = request.form.get('image')
            if image_name:
                user.add_cubicle(image_name)

            return_msg = "User {} added!".format(name)

        case 'node':
            node = obj()
            name = request.form.get('name')
            if not name:
                return _modal_status_message('error', 'Name is missing')
            if not re.search('^[a-zA-Z0-9\_\-]+$', name):
                return _modal_status_message('error', 'Name includes bad characters')
            node.name = name

            ip = request.form.get('ip_address')
            try:
                ip_address(ip)
            except:
                return _modal_status_message('error', 'IP address is in a bad format')
            else:
                node.ip_address = ip

            network_range = request.form.get('network_range')
            try:
                ip_network(network_range)
            except:
                return _modal_status_message('error', 'Network range is in a bad format')
            else:
                node.network_range = network_range
                generate_networks(node, network_range)

            db.session.add(node)
            db.session.commit()

            return_msg = "Node {} added!".format(name)

        case 'image':
            image = obj()
            name = request.form.get('name')
            if not name:
                return _modal_status_message('error', 'Name is missing')
            if not re.search('^[a-zA-Z0-9\_\-\.]+$', name):
                return _modal_status_message('error', 'Name includes bad characters')
            image.name = name
            
            source = request.form.get('source')
            if not source:
                return _modal_status_message('error', 'Source is missing')
            if not re.search('^[a-zA-Z0-9\_\-\/\:\.]+$', source):
                return _modal_status_message('error', 'Source includes bad characters')
            image.image = source

            cpu_limit = request.form.get('cpu-limit')
            if not cpu_limit:
                return _modal_status_message('error', 'CPU-limit is missing')
            if not re.search('^[0-9]+$', cpu_limit):
                return _modal_status_message('error', 'CPU-limit includes bad characters')
            if int(cpu_limit) > 10:
                return _modal_status_message('error', 'CPU-limit is to high. Use 0 for unlimited')
            image.cpu_limit = cpu_limit

            mem_limit = request.form.get('mem-limit')
            if not mem_limit:
                return _modal_status_message('error', 'Mem-limit is missing')
            if not re.search('^[0-9]+(b|k|m|g)$', mem_limit):
                return _modal_status_message('error', 'Mem-limit got bad format')
            image.mem_limit = mem_limit

            db.session.add(image)
            db.session.commit()

            return_msg = "Image {} added!".format(name)

        case _:
            return _modal_status_message('error', 'Unknown type')

    return _modal_status_message('ok', return_msg)

@admin.route('/admin/modal/<type>/<id>', methods=['GET'])
def modal_get_id(type, id):
    try:
        type, id = _normalize_input_variables(type, id)
    except Exception:
        return render_template('admin/modal/error.html')
            
    obj = _get_type(type)

    if obj is None:
        return render_template('admin/modal/error.html')
    
    val = {}
    match type:
        case 'user':
            user = obj.query.filter_by(id=id).first()
            val['id'] = user.id
            val['name'] = user.name
            val['username'] = user.username
        case 'node':
            node = obj.query.filter_by(id=id).first()
            val['id'] = node.id
            val['name'] = node.name
            val['ip_address'] = node.ip_address
            val['network_range'] = node.network_range
        case 'image':
            image = obj.query.filter_by(id=id).first()
            val['id'] = image.id
            val['name'] = image.name
            val['source'] = image.image
            val['cpu_limit'] = image.cpu_limit
            val['mem_limit'] = image.mem_limit
        case 'cubicle':
            cubicle = obj.query.filter_by(id=id).first()
            val['id'] = cubicle.id
            val['name'] = cubicle.name

            users = User.query.all()
            val['users'] = {}
            for user in users:
                if cubicle.user and cubicle.user.id == user.id:
                    val['users'][user.name] = True
                else:
                    val['users'][user.name] = False

            images = Image.query.all()
            val['images'] = {}
            for image in images:
                if cubicle.image and cubicle.image.id == image.id:
                    val['images'][image.name] = True
                else:
                    val['images'][image.name] = False

            nodes = Node.query.all()
            val['nodes'] = {}
            for node in nodes:
                if cubicle.node and cubicle.node.id == node.id:
                    val['nodes'][node.name] = True
                else:
                    val['nodes'][node.name] = False
        case _:
            return render_template('admin/modal/error.html')

    return render_template('admin/modal/{}.html'.format(type), obj=val)

@admin.route('/admin/modal/<type>/<id>', methods=['POST'])
def modal_update_id(type, id):
    try:
        type, id = _normalize_input_variables(type, id)
    except Exception:
        return render_template('admin/modal/error.html')
    
    obj = _get_type(type)

    if obj is None:
        return render_template('admin/modal/error.html')
    
    return_msg = ""

    match type:
        case 'user':
            user = obj.query.filter_by(id=id).first()
            if not user:
                return "Unknown user"

            # Get full name, sanitiy check the string and then add it to obj
            name = request.form.get('full_name')
            if not name:
                return "Full name is missing"
            if not re.search("^[a-zA-Z0-9\s]+$", name):
                return "Full name includes bad characters"
            user.name = name

            # Verify old password
            current_password = request.form.get('current_password')
            if current_password:
                # TODO: ignore this check if you are superadmin?
                if user.check_password(password) == False:
                    return "Current password is wrong"
                # Get password and then add it to obj
                password = request.form.get('new_password')
                if not password:
                    return "Password is missing"
                if not re.search("^[a-zA-Z0-9\s]+$", name):
                    return "Password contains forbidded characters"
                user.password = password

            # Add cubicle
            # TODO: Use an ID instead of name
            cubicle_name = request.form.get('cubicle')
            if cubicle_name:
                cubicle = Cubicle.query.filter_by(name=cubicle_name).first()
                user.cubicles.append(cubicle)
            db.session.commit()

            return_msg = "User {} updated!".format(name)

        case 'node':
            node = obj.query.filter_by(id=id).first()
            if not node:
                return _modal_status_message('error', 'Unknown node')
            
            name = request.form.get('name')
            if not name:
                return _modal_status_message('error', 'Name is missing')
            if not re.search('^[a-zA-Z0-9\_\-]+$', name):
                return _modal_status_message('error', 'Name includes bad characters')
            node.name = name

            ip = request.form.get('ip_address')
            try:
                ip_address(ip)
            except:
                return _modal_status_message('error', 'IP address is in a bad format')
            else:
                node.ip_address = ip

            network_range = request.form.get('network_range')
            try:
                ip_network(network_range)
            except:
                return _modal_status_message('error', 'Network range is in a bad format')
            else:
                node.network_range = network_range
                # TODO: Delete old networks if the range is changed
                generate_networks(node, network_range)

            db.session.commit()

            return_msg = "Node {} updated!".format(name)

        case 'image':
            image = obj.query.filter_by(id=id).first()
            if not image:
                return _modal_status_message('error', 'Unknown image')
            
            name = request.form.get('name')
            if not name:
                return _modal_status_message('error', 'Name is missing')
            if not re.search('^[a-zA-Z0-9\_\-\.]+$', name):
                return _modal_status_message('error', 'Name includes bad characters')
            image.name = name
            
            source = request.form.get('source')
            if not source:
                return _modal_status_message('error', 'Source is missing')
            if not re.search('^[a-zA-Z0-9\_\-\/\:\.]+$', source):
                return _modal_status_message('error', 'Source includes bad characters')
            image.image = source

            cpu_limit = request.form.get('cpu-limit')
            if not cpu_limit:
                return _modal_status_message('error', 'CPU-limit is missing')
            if not re.search('^[0-9]+$', cpu_limit):
                return _modal_status_message('error', 'CPU-limit includes bad characters')
            if int(cpu_limit) > 10:
                return _modal_status_message('error', 'CPU-limit is to high. Use 0 for unlimited')
            image.cpu_limit = cpu_limit

            mem_limit = request.form.get('mem-limit')
            if not mem_limit:
                return _modal_status_message('error', 'Mem-limit is missing')
            if not re.search('^[0-9]+(b|k|m|g)$', mem_limit):
                return _modal_status_message('error', 'Mem-limit got bad format')
            image.mem_limit = mem_limit

            db.session.commit()

            return_msg = "Image {} updated!".format(name)

        case _:
            return _modal_status_message('error', 'Unknown type')

    return _modal_status_message('ok', return_msg)

def _modal_status_message(status, text):
    return render_template('admin/modal/status.html', info={
        'status': status,
        'text': text,
    })

def _normalize_input_variables(type, id):
    try:
        if not isinstance(type, str):
            type = str(type)
        if not isinstance(id, int):
            id = int(id)
    except Exception:
        raise Exception("Type/ID could not be converted to correct type")        
    return type, id

def _get_type(type):
    type_list = {
        'user': User,
        'node': Node,
        'image': Image,
        'cubicle': Cubicle,
    }
    try:
        type, _ = _normalize_input_variables(type, 0)
    except Exception:
        return None
    
    if type not in type_list:
        return None
    
    return type_list[type]

@admin.route('/admin/modal/<type>/<id>', methods=['DELETE'])
def modal_delete_id(type, id):
    try:
        type, id = _normalize_input_variables(type, id)    
    except Exception:
        return render_template('admin/modal/error.html')
            
    obj = _get_type(type)

    if not obj:
        return "Could not delete {}:{}".format(type, id)
    
    db.session.delete(obj.query.filter_by(id=id).first())
    db.session.commit()

    return "Deleted {}:{}".format(type, id)
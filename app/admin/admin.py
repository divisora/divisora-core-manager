#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request
from flask import render_template
from flask_login import login_required, current_user

import re
import pyotp, qrcode
from ipaddress import ip_network, ip_address
from functools import wraps
from datetime import datetime, timedelta
from base64 import b64encode
from io import BytesIO

from app.models.user import User
from app.models.node import Node
from app.models.image import Image
from app.models.cubicle import Cubicle

from app.config import MIN_PASSWORD_LENGTH, MIN_USERNAME_LENGTH, CPU_LIMIT
from app.extensions import db, login_manager
from app.models.network import generate_networks

admin = Blueprint('admin', __name__, template_folder='templates')

def admin_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        print("Check if {} is an admin".format(current_user.name))
        if not current_user.admin:
            # TODO: Maybe not redirect to login-view?
            return login_manager.unauthorized()
        return func(*args, **kwargs)
    return inner

@admin.before_request
def update_last_activity():
    if not current_user.is_authenticated:
        return
    user = User.query.filter_by(id=current_user.id).first()
    user.last_activity = datetime.utcnow()
    db.session.commit()


@admin.route('/admin')
#@login_required
#@admin_required
def main():
    # Get information about users
    users = []
    for user in User.query.all():
        name = user.name if user.name is not None else ""
        username = user.username if user.username is not None else ""
        if user.last_activity < datetime.utcnow() - timedelta(hours=1):
            status_msg = "Offline"
            status_class = "status-normal"
        elif user.last_activity < datetime.utcnow() - timedelta(minutes=1):
            status_msg = "Idle"
            status_class = "status-warning"
        else:
            status_msg = "Online"
            status_class = "status-ok"
        
        users.append({
            'id': user.id,
            'name': name,
            'username': username,
            'admin': user.admin,
            'online_status': {
                'msg': status_msg,
                'class': status_class
            }
        })

    # Get information about nodes
    nodes = []
    for node in Node.query.all():
        name = node.name if node.name is not None else ""
        if node.last_activity < datetime.utcnow() - timedelta(minutes=3):
            status_msg = "Offline"
            status_class = "status-error"
        elif node.last_activity < datetime.utcnow() - timedelta(minutes=1):
            status_msg = "Idle"
            status_class = "status-warning"
        else:
            status_msg = "Online"
            status_class = "status-ok"

        nodes.append({
            'id': node.id,
            'name': name,
            'ip': node.ip_address,
            'network_range': node.network_range,
            'online_status': {
                'msg': status_msg,
                'class': status_class
            }            
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
        active = False

        if cubicle.user is not None:
            for n in cubicle.user.networks:
                if n.node is None or cubicle.node is None:
                    continue
                if n.node.id != cubicle.node.id:
                    continue
                network = n.name
                break

            active = cubicle.active

        cubicles.append({
            'id': cubicle.id,
            'name': name,
            'user': user, 
            'image': image_name,
            'node': node_name,
            'novnc_port': novnc_port,
            'network': network,
            'active': active,
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

            success, error_msg, full_name = _normalize_full_name(request.form.get('full_name'))
            if not success:
                return error_msg
            user.name = full_name

            success, error_msg, username = _normalize_username(request.form.get('username'))
            if not success:
                return error_msg
            user.username = username

            success, error_msg, password = _normalize_password(request.form.get('new_password'))
            if not success:
                return error_msg
            if password != request.form.get('new_password_confirm'):
                return _modal_status_message('error', 'Passwords does not match')
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

            return_msg = "User {} added!".format(full_name)

        case 'node':
            node = obj()

            success, error_msg, name = _normalize_object_name(request.form.get('name'))
            if not success:
                return error_msg
            node.name = name

            ip = request.form.get('ip_address')
            try:
                ip_address(ip)
            except ValueError:
                return _modal_status_message('error', 'IP address is in a bad format')
            else:
                node.ip_address = ip

            network_range = request.form.get('network_range')
            try:
                ip_network(network_range)
            except ValueError:
                return _modal_status_message('error', 'Network range is in a bad format')
            else:
                node.network_range = network_range
                generate_networks(node, network_range)

            node.last_activity = datetime.utcnow()

            db.session.add(node)
            db.session.commit()

            return_msg = "Node {} added!".format(name)

        case 'image':
            image = obj()

            success, error_msg, name = _normalize_object_name(request.form.get('name'))
            if not success:
                return error_msg            
            image.name = name
            
            success, error_msg, source = _normalize_source_name(request.form.get('source'))
            if not success:
                return error_msg
            image.image = source

            success, error_msg, cpu_limit = _normalize_cpu_limit(request.form.get('cpu-limit'))
            if not success:
                return error_msg            
            image.cpu_limit = cpu_limit

            success, error_msg, mem_limit = _normalize_mem_limit(request.form.get('mem-limit'))
            if not success:
                return error_msg            
            image.mem_limit = mem_limit

            db.session.add(image)
            db.session.commit()

            return_msg = "Image {} added!".format(name)

        case 'cubicle':
            cubicle = obj()

            success, error_msg, name = _normalize_object_name(request.form.get('name'))
            if not success:
                return error_msg            
            cubicle.name = name

            user = User.query.filter_by(name=request.form.get('user')).first()
            if not user:
                return _modal_status_message('error', 'User could not be found')
            cubicle.user_id = user.id

            image = Image.query.filter_by(name=request.form.get('image')).first()
            if not image:
                return _modal_status_message('error', 'Image could not be found')
            cubicle.image_id = image.id

            node = Node.query.filter_by(name=request.form.get('node')).first()
            if not node:
                return _modal_status_message('error', 'Node could not be found')
            cubicle.node_id = node.id

            cubicle.novnc_port = node.get_available_novnc_port()

            db.session.add(cubicle)
            db.session.commit()

            return_msg = "Cubicle {} added!".format(name)

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
            totp_uri = pyotp.totp.TOTP(user.totp_key).provisioning_uri(
                name = user.name,
                issuer_name = 'Divisora',
            )
            img = qrcode.make(totp_uri)
            image_io = BytesIO()
            img.save(image_io, 'PNG')
            dataurl = 'data:image/png;base64,' + b64encode(image_io.getvalue()).decode('ascii')
            val['totp'] = {
                'img': dataurl,
                'uri': totp_uri,
            }
            
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
                return _modal_status_message('error', 'Unknown user-id')

            if user.username != request.form.get('username'):
                return _modal_status_message('error', 'ID and username does not match')

            success, error_msg, full_name = _normalize_full_name(request.form.get('full_name'))
            if not success:
                return error_msg
            user.name = full_name

            # Verify old password
            current_password = request.form.get('current_password')
            if current_password:
                # TODO: ignore this check if you are superadmin?
                success, error_msg, password = _normalize_password(request.form.get('new_password'))
                if not success:
                    return error_msg
                if password != request.form.get('new_password_confirm'):
                    return _modal_status_message('error', 'Passwords does not match')
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
                return _modal_status_message('error', 'Unknown node-id')
            
            success, error_msg, name = _normalize_object_name(request.form.get('name'))
            if not success:
                return error_msg
            node.name = name

            ip = request.form.get('ip_address')
            try:
                ip_address(ip)
            except ValueError:
                return _modal_status_message('error', 'IP address is in a bad format')
            else:
                node.ip_address = ip

            network_range = request.form.get('network_range')
            try:
                ip_network(network_range)
            except ValueError:
                return _modal_status_message('error', 'Network range is in a bad format')
            else:
                node.network_range = network_range
                # TODO: Delete old networks if the range is changed
                generate_networks(node, network_range)

            node.last_activity = datetime.utcnow()

            db.session.commit()

            return_msg = "Node {} updated!".format(name)

        case 'image':
            image = obj.query.filter_by(id=id).first()

            if not image:
                return _modal_status_message('error', 'Unknown image-id')
            
            success, error_msg, name = _normalize_object_name(request.form.get('name'))
            if not success:
                return error_msg            
            image.name = name
            
            success, error_msg, source = _normalize_source_name(request.form.get('source'))
            if not success:
                return error_msg
            image.image = source

            success, error_msg, cpu_limit = _normalize_cpu_limit(request.form.get('cpu-limit'))
            if not success:
                return error_msg            
            image.cpu_limit = cpu_limit

            success, error_msg, mem_limit = _normalize_mem_limit(request.form.get('mem-limit'))
            if not success:
                return error_msg            
            image.mem_limit = mem_limit

            db.session.commit()

            return_msg = "Image {} updated!".format(name)

        case 'cubicle':
            cubicle = obj.query.filter_by(id=id).first()
            
            if not cubicle:
                return _modal_status_message('error', 'Unknown cubicle-id')

            success, error_msg, name = _normalize_object_name(request.form.get('name'))
            if not success:
                return error_msg            
            cubicle.name = name

            user = User.query.filter_by(name=request.form.get('user')).first()
            if not user:
                return _modal_status_message('error', 'User could not be found')
            cubicle.user_id = user.id

            image = Image.query.filter_by(name=request.form.get('image')).first()
            if not image:
                return _modal_status_message('error', 'Image could not be found')
            cubicle.image_id = image.id

            node = Node.query.filter_by(name=request.form.get('node')).first()
            if not node:
                return _modal_status_message('error', 'Node could not be found')
            cubicle.node_id = node.id

            cubicle.novnc_port = node.get_available_novnc_port()

            db.session.commit()

            return_msg = "Cubicle {} updated!".format(name)

        case _:
            return _modal_status_message('error', 'Unknown type')

    return _modal_status_message('ok', return_msg)

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
    
    return_msg = "Deleted {}:{}".format(type, id)

    return _modal_status_message('ok', return_msg)

@admin.route('/admin/generate-qr/<id>', methods=['GET'])
def generate_qr(id):
    try:
        _, id = _normalize_input_variables("", id)    
    except Exception:
        return _modal_status_message('error', 'Bad ID value'), 403
    
    # Check if the user is logged in and admin.
    if not current_user.is_authenticated or not current_user.admin:
        return _modal_status_message('error', 'QR Code could not be updated'), 403

    # Update the QR code for user <id>
    user = User.query.filter_by(id=id).first()

    if not user:
        return _modal_status_message('error', 'Unknown user-id')

    user.totp_key = pyotp.random_base32()
    db.session.commit()

    totp_uri = pyotp.totp.TOTP(user.totp_key).provisioning_uri(
        name = user.name,
        issuer_name = 'Divisora',
    )
    img = qrcode.make(totp_uri)
    image_io = BytesIO()
    img.save(image_io, 'PNG')
    dataurl = 'data:image/png;base64,' + b64encode(image_io.getvalue()).decode('ascii')
    return {
        'img': dataurl,
        'uri': totp_uri,
    }

def _modal_status_message(status, text):
    return render_template('admin/modal/status.html', info={
        'status': status,
        'text': text,
    })

# Normalization
# Returns a tuple where first part is the 'error-code'
# False = Could not normalize / Did not pass tests
# True = Everything is fine
# (error-code, error-msg, normalized-value)
def _normalize_source_name(name):
    if not name:
        return (False, _modal_status_message('error', 'Source name is missing'), '')
    # Format check. Example format:
    #   example/image-example:latest
    #   example/image-example:1.0
    if not re.search('^[a-zA-Z0-9]+/[a-zA-Z0-9\_\-]+:[a-zA-Z0-9\.]+$', name):
        return (False, _modal_status_message('error', 'Source name got bad format or includes forbidden characters'), '')
    return (True, '', name)

# Check for forbidden characters, limit the input to two names and finaly capitalize the names if needed.
def _normalize_full_name(full_name):
    if not full_name:
        return (False, _modal_status_message('error', 'Full name is missing'), '')

    names = full_name.split(" ")
    # Limit the name to only contain two names with space in between.
    if len(names) != 2:
        return (False, _modal_status_message('error', 'Full name must only include First- and Last-name'), '')

    # Loop the unique names, check for forbidden characters and then capitalize it.
    for i, name in enumerate(names):
        if not re.search('^[a-zA-Z0-9]+$', name):
            return (False, _modal_status_message('error', 'Full name includes forbidden characters'), '')
        names[i] = name.capitalize()

    return (True, '', ' '.join(names))

# Check for forbidden characters and collision with other usernames
def _normalize_username(username):
    if not username:
        return (False, _modal_status_message('error', 'Username is missing'), '')
    
    if len(username) < MIN_USERNAME_LENGTH:
        return (False, _modal_status_message('error', 'Username is too short'), '')
    
    if not re.search('^[a-zA-Z0-9_-]+$', username):
        return (False, _modal_status_message('error', 'Username includes forbidden characters'), '')
    
    if User.query.filter_by(username=username).first():
        return (False, _modal_status_message('error', 'Username is already in use'), '')
    
    return (True, '', username)

# Check for forbidden characters
def _normalize_object_name(name):
    if not name:
        return (False, _modal_status_message('error', 'Name is missing'), '')
    if not re.search('^[a-zA-Z0-9\_\-\.]+$', name):
        return (False, _modal_status_message('error', 'Name includes forbidden characters'), '')
    return (True, '', name)

# Check for length and forbidden characters
def _normalize_password(password):
    if not password:
        return (False, _modal_status_message('error', 'Password is missing'), '')
    
    # Inherit length from config.py
    if len(password) < MIN_PASSWORD_LENGTH:
        return (False, _modal_status_message('error', 'Password is too short'), '')
    
    if not re.search('^[a-zA-Z0-9\s]+$', password):
        return (False, _modal_status_message('error', 'Password includes forbidden characters'), '')
    
    return (True, '', password)

def _normalize_cpu_limit(cpu_limit):
    if not cpu_limit:
        return (False, _modal_status_message('error', 'CPU-limit is missing'), '')
    if not re.search('^[0-9]+$', cpu_limit):
        return (False, _modal_status_message('error', 'CPU-limit includes forbidden characters'), '')
    if int(cpu_limit) < 0 or int(cpu_limit) > CPU_LIMIT:
        return (False, _modal_status_message('error', 'CPU-limit is to high. Use 0 for unlimited'), '')
    return (True, '', cpu_limit)

def _normalize_mem_limit(mem_limit):
    if not mem_limit:
        return (False, _modal_status_message('error', 'Mem-limit is missing'), '')
    if not re.search('^[0-9]+(b|k|m|g)$', mem_limit):
        return (False, _modal_status_message('error', 'Mem-limit got bad format'), '')
    # TODO: Check if a higher limit is reached?
    return (True, '', mem_limit)

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
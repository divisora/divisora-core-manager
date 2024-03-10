#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Flask module """

from os import getenv

from flask import Flask
from flask import render_template

from app.config import Config
from app.extensions import db, login_manager, migrate, celery_init_app

from app.admin.admin import admin as admin_blueprint
from app.auth.auth import auth as auth_blueprint
from app.api.api import api as api_blueprint
from app.dashboard.dashboard import dashboard as dashboard_blueprint
from app.redirect.redirect import redirect as redirect_blueprint

def create_app():
    """ Initialize Flask """
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    ## Login Manager
    login_manager.init_app(app)

    ## Database
    db.init_app(app)
    migrate.init_app(app, db)
    
    if getenv('FLASK_DB') == "populate":
        # pylint: disable=C0415:import-outside-toplevel
        from app.models.node import Node
        # pylint: disable=C0415:import-outside-toplevel
        from app.models.image import Image
        # pylint: disable=C0415:import-outside-toplevel,W0611:unused-import
        from app.models.cubicle import Cubicle
        # pylint: disable=C0415:import-outside-toplevel
        from app.models.user import User
        # pylint: disable=C0415:import-outside-toplevel,W0611:unused-import
        from app.models.network import Network
        # pylint: disable=C0415:import-outside-toplevel
        from app.models.measurements import ResponseTimeCubicle, ResponseTimeNode

        with app.app_context():
            db.create_all()
            session = db.session()

            # Install default nodes if the database is empty
            if len(session.query(Node).all()) == 0:
                # pylint: disable=C0415:import-outside-toplevel
                from app.models.node import setup as node_setup
                node_setup(session)
            else:
                print(session.query(Node).all())

            # Install default images if the database is empty
            if len(session.query(Image).all()) == 0:
                # pylint: disable=C0415:import-outside-toplevel
                from app.models.image import setup as image_setup
                image_setup(session)
            else:
                print(session.query(Image).all())

            # Install default cubicles if the database is empty
            # if len(session.query(Cubicle).all()) == 0:
            #     # pylint: disable=C0415:import-outside-toplevel
            #     from app.models.cubicle import setup as cubicle_setup
            #     # cubicle_setup(session)
            # else:
            #     print(session.query(Cubicle).all())

            # Install default users if the database is empty
            if len(session.query(User).all()) == 0:
                # pylint: disable=C0415:import-outside-toplevel
                from app.models.user import setup as user_setup
                user_setup(session)
            else:
                print(session.query(User).all())

            # Install responsetime logs. Test-purpose
            if len(session.query(ResponseTimeCubicle).all()) == 0:
                from app.models.measurements import setup as measurement_setup
                measurement_setup(session)

    ## Celery
    celery_init_app(app)

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    app.register_blueprint(api_blueprint, url_prefix='/api')
    app.register_blueprint(dashboard_blueprint, url_prefix='/dashboard') 
    app.register_blueprint(redirect_blueprint)

    # Error handling. Present a more generic page than default
    @app.errorhandler(404)
    def _404(_):
        return render_template('404.html')

    return app

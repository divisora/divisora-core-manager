#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Flask module """

from flask import Flask
from flask import render_template

from app.config import DevConfig
from app.extensions import db, login_manager, celery_init_app

def create_app():
    """ Initialize Flask """
    app = Flask(__name__)
    app.config.from_mapping(
        CELERY={
            "broker_url": "redis://redis",
            "result_backend": "redis://redis",
            "task_ignore_result": True,
            "beat_schedule": {
                'check-all-nodes': {
                    'task': 'app.tasks.schedule.check_all_nodes',
                    'schedule': 5.0,
                },
                'check-reponsetime-cubicles': {
                    'task': 'app.tasks.schedule.check_responsetime_cubicles',
                    'schedule': 5.0,
                }
            },
        },
    )
    app.config.from_object(DevConfig)

    # Initialize extensions
    login_manager.init_app(app)
    db.init_app(app)
    #ext_celery.init_app(app)
    celery_init_app(app)

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
    from app.models.measurements import ResponseTimeCubicle

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

    # pylint: disable=C0415:import-outside-toplevel
    from app.auth.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # pylint: disable=C0415:import-outside-toplevel
    from app.admin.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    # pylint: disable=C0415:import-outside-toplevel
    from app.api.api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')

    # pylint: disable=C0415:import-outside-toplevel
    from app.redirect.redirect import redirect as redirect_blueprint
    app.register_blueprint(redirect_blueprint)

    # Error handling. Present a more generic page than default
    @app.errorhandler(404)
    def _404(_):
        return render_template('404.html')

    return app

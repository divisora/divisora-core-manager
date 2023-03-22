#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask
from flask import render_template

from celery import Celery
from celery import Task

from app.extensions import db, login_manager
from app.config import DevConfig

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        CELERY=dict(
            broker_url="redis://localhost",
            result_backend="redis://localhost",
            task_ignore_result=True,
        ),
    )    
    app.config.from_object(DevConfig)

    login_manager.init_app(app)

    db.init_app(app)
    celery_init_app(app)

    from app.models.node import Node
    from app.models.image import Image
    from app.models.cubicle import Cubicle
    from app.models.user import User
    from app.models.network import Network

    with app.app_context():
        db.create_all()
        session = db.session()

        # Install default nodes if the database is empty
        if len(session.query(Node).all()) == 0:
            from app.models.node import setup as node_setup
            node_setup(session)
        else:
            print(session.query(Node).all())

        # Install default images if the database is empty
        if len(session.query(Image).all()) == 0:
            from app.models.image import setup as image_setup
            image_setup(session)
        else:
            print(session.query(Image).all())

        # Install default cubicles if the database is empty
        if len(session.query(Cubicle).all()) == 0:
            from app.models.cubicle import setup as cubicle_setup
            # cubicle_setup(session)
        else:
            print(session.query(Cubicle).all())

        # Install default users if the database is empty
        if len(session.query(User).all()) == 0:
            from app.models.user import setup as user_setup
            user_setup(session)
        else:
            print(session.query(User).all())      

    from app.auth.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from app.admin.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    from app.api.api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')

    from app.redirect.redirect import redirect as redirect_blueprint
    app.register_blueprint(redirect_blueprint)

    # Error handling. Present a more generic page than default
    @app.errorhandler(404)
    def _404(e):
        return render_template('404.html')
    
    return app

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app
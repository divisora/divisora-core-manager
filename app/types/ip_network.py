#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ipaddress import ip_network

from sqlalchemy import types


class IPNetworkType(types.TypeDecorator):
    impl = types.Unicode(50)
    cache_ok = True

    def __init__(self, max_length=50, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.impl = types.Unicode(max_length)

    def process_bind_param(self, value, dialect):
        return str(value) if value else None

    def process_result_value(self, value, dialect):
        return ip_network(value) if value else None

    def _coerce(self, value):
        return ip_network(value) if value else None

    @property
    def python_type(self):
        return self.impl.type.python_type

# Copyright (C) 2015-2019, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is a free software; you can redistribute it and/or modify it under the terms of GPLv2

import json
import os
import re
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine

from wazuh.exception import WazuhError
from wazuh.rbac.tests.utils import init_db

test_path = os.path.dirname(os.path.realpath(__file__))
test_data_path = os.path.join(test_path, 'data/')


@pytest.fixture(scope='function')
def db_setup():
    with patch('wazuh.common.ossec_uid'), patch('wazuh.common.ossec_gid'):
        with patch('sqlalchemy.create_engine', return_value=create_engine("sqlite://")):
            with patch('shutil.chown'), patch('os.chmod'):
                with patch('api.constants.SECURITY_PATH', new=test_data_path):
                    import wazuh.rbac.decorators as decorator
    init_db('schema_security_test.sql', test_data_path)

    yield decorator


permissions = list()
results = list()
with open(test_data_path + 'RBAC_decorators_permissions_white.json') as f:
    configurations_white = [(config['decorator_params'],
                             config['function_params'],
                             config['rbac'],
                             config['fake_system_resources'],
                             config['allowed_resources'],
                             config.get('result', None),
                             'white') for config in json.load(f)]
with open(test_data_path + 'RBAC_decorators_permissions_black.json') as f:
    configurations_black = [(config['decorator_params'],
                             config['function_params'],
                             config['rbac'],
                             config['fake_system_resources'],
                             config['allowed_resources'],
                             config.get('result', None),
                             'black') for config in json.load(f)]

with open(test_data_path + 'RBAC_decorators_resourceless_white.json') as f:
    configurations_resourceless_white = [(config['decorator_params'],
                                          config['rbac'],
                                          config['allowed'],
                                          'white') for config in json.load(f)]
with open(test_data_path + 'RBAC_decorators_resourceless_black.json') as f:
    configurations_resourceless_black = [(config['decorator_params'],
                                          config['rbac'],
                                          config['allowed'],
                                          'black') for config in json.load(f)]


def get_identifier(resources):
    list_params = list()
    for resource in resources:
        resource = resource.split('&')
        for r in resource:
            try:
                list_params.append(re.search(r'^([a-z*]+:[a-z*]+:)(\*|{(\w+)})$', r).group(3))
            except AttributeError:
                pass

    return list_params


@pytest.mark.parametrize('decorator_params, function_params, rbac, '
                         'fake_system_resources, allowed_resources, result, mode',
                         configurations_black + configurations_white)
def test_expose_resources(db_setup, decorator_params, function_params, rbac, fake_system_resources, allowed_resources,
                          result, mode):
    db_setup.rbac_mode.set(mode)

    def mock_expand_resource(resource):
        fake_values = fake_system_resources.get(resource, resource.split(':')[-1])
        return {fake_values} if isinstance(fake_values, str) else set(fake_values)

    with patch('wazuh.rbac.decorators.rbac') as mock_rbac:
        mock_rbac.get.return_value = rbac
        with patch('wazuh.rbac.decorators._expand_resource', side_effect=mock_expand_resource):
            @db_setup.expose_resources(**decorator_params)
            def framework_dummy(*args, **kwargs):
                for target_param, allowed_resource in zip(get_identifier(decorator_params['resources']),
                                                          allowed_resources):
                    assert set(kwargs[target_param]) == set(allowed_resource)

            try:
                framework_dummy(rbac=rbac, **function_params)
                assert (result is None or result == "allow")
            except WazuhError as e:
                assert (result is None or result == "deny")
                for allowed_resource in allowed_resources:
                    assert (len(allowed_resource) == 0)
                assert (e.code == 4000)


@pytest.mark.parametrize('decorator_params, rbac, allowed, mode',
                         configurations_resourceless_white + configurations_resourceless_black)
def test_expose_resourcesless(db_setup, decorator_params, rbac, allowed, mode):
    db_setup.rbac_mode.set(mode)

    def mock_expand_resource(resource):
        return {'*'}

    with patch('wazuh.rbac.decorators.rbac') as mock_rbac:
        mock_rbac.get.return_value = rbac
        with patch('wazuh.rbac.decorators._expand_resource', side_effect=mock_expand_resource):
            @db_setup.expose_resources(**decorator_params)
            def framework_dummy(*args, **kwargs):
                pass

            try:
                framework_dummy(rbac=rbac)
                assert allowed
            except WazuhError as e:
                assert (not allowed)
                assert (e.code == 4000)

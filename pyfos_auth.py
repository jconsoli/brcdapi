# Copyright 2019, 2020, 2021 Jack Consoli.  All rights reserved.
#
# NOT BROADCOM SUPPORTED
#
# The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may also obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
:mod:`pyfos_auth` - Deprecated. This module started using the same object types in PyFOS. The approach to using the API
and the nature of those objects evolved into something very different in these libraries. This module is only here as an
interface to support older modules with calls to this module.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.x.x     | 03 Jul 2019   | Experimental                                                                      |
    | 2.x.x     |               |                                                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.0     | 19 Jul 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 02 Aug 2020   | PEP8 Clean up                                                                     |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.2     | 09 Jan 2021   | Removed unused unused method, _pyfos_logout(). Use connection established at      |
    |           |               | login time rather than create a new HTTP connection.                              |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.3     | 14 Nov 2021   | Fully deprecated this module.                                                     |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020, 2021 Jack Consoli'
__date__ = '14 Nov 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.3'

import brcdapi.fos_auth as brcdapi_auth

def basic_api_parse(obj):
    return brcdapi_auth.basic_api_parse(obj)


def create_error(status, reason, msg):
    return brcdapi_auth.create_error(status, reason, msg)


def obj_status(obj):
    return brcdapi_auth.obj_status(obj)


def is_error(obj):
    return brcdapi_auth.is_error(obj)


def obj_reason(obj):
    return brcdapi_auth.obj_reason(obj)


def obj_error_detail(obj):
    return brcdapi_auth.obj_error_detail(obj)


def formatted_error_msg(obj):
    return brcdapi_auth.formatted_error_msg(obj)


def login(user, password, ip_addr, is_https='none'):
    return brcdapi_auth.login(user, password, ip_addr, is_https='none')


def logout(session):
    return brcdapi_auth.logout(session)

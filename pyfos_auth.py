# Copyright 2019, 2020 Jack Consoli.  All rights reserved.
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
:mod:`brcdapi.pyfos_auth` - Login, logout, and error formatting. With the exception of error handling, typically, the
remaining methods contained herein are only used by brcdapi.brcdapi_rest. Consolidated modules from PyFOS and removed
pre FOS v8.2.1b relevant code from those PyFOS modules.

Primary Methods::

    +-----------------------------+----------------------------------------------------------------------------------+
    | Method                      | Description                                                                      |
    +=============================+==================================================================================+
    | is_error()                  | Determines if an object returned from api_request() is an error object           |
    +-----------------------------+----------------------------------------------------------------------------------+
    | formatted_error_msg()       | Formats the error message into a human readable format                           |
    +-----------------------------+----------------------------------------------------------------------------------+
    | is_not_supported()          | Determines if an error object returned from get_request() is a 'Not Supported'   |
    |                             | error                                                                            |
    +-----------------------------+----------------------------------------------------------------------------------+
    | login()                     | Establish a session to the FOS switch and return the session object              |
    +-----------------------------+----------------------------------------------------------------------------------+
    | logout()                    | Terminate a session to FOS                                                       |
    +-----------------------------+----------------------------------------------------------------------------------+

Support Methods::

    +-----------------------------+----------------------------------------------------------------------------------+
    | Method                      | Description                                                                      |
    +=============================+==================================================================================+
    | basic_api_parse()           | Performs a read and basic parse of the conn.getresponse().                       |
    +-----------------------------+----------------------------------------------------------------------------------+
    | create_error()              | Intended for use within this module and brcdbapi.brcdapi_rest only. Creates a    |
    |                             | standard error object                                                            |
    +-----------------------------+----------------------------------------------------------------------------------+
    | obj_status()                | Returns the status from API object.                                              |
    +-----------------------------+----------------------------------------------------------------------------------+
    | obj_reason()                | Returns the reason from API object                                               |
    +-----------------------------+----------------------------------------------------------------------------------+
    | obj_error_detail()          | Formats the error message detail into human readable format                      |
    +-----------------------------+----------------------------------------------------------------------------------+

Login Session::

    Not all parameters filled in by pyfos_auth.login

    +-------------------+-------------------------------------------------------------------------------------------+
    | Leaf              | Description                                                                               |
    +===================+===========================================================================================+
    | Authorization     | As returned from the RESTConf API login                                                   |
    +-------------------+-------------------------------------------------------------------------------------------+
    | content-type      | As returned from the RESTConf API login                                                   |
    +-------------------+-------------------------------------------------------------------------------------------+
    | content-version   | As returned from the RESTConf API login                                                   |
    +-------------------+-------------------------------------------------------------------------------------------+
    | credential        | As returned from the RESTConf API login                                                   |
    +-------------------+-------------------------------------------------------------------------------------------+
    | chassis_wwn       | str: Chassis WWN                                                                          |
    +-------------------+-------------------------------------------------------------------------------------------+
    | debug             | bool: True - brcdapi.brcdapi_rest does a pprint of all data structures to the log         |
    +-------------------+-------------------------------------------------------------------------------------------+
    | _debug_name       | Name of the debug file in brcdapi.brcdapi_rest if debug is enabled.                       |
    +-------------------+-------------------------------------------------------------------------------------------+
    | ip_addr           | str: IP address of switch                                                                 |
    +-------------------+-------------------------------------------------------------------------------------------+
    | ishttps           | bool: Connection type. True - HTTPS. False: HTTP                                          |
    +-------------------+-------------------------------------------------------------------------------------------+
    | supported_uris    | dict: See brcda.util.uri_map                                                              |
    +-------------------+-------------------------------------------------------------------------------------------+
    | ssh               | SSH login session from paramiko - CLI login                                               |
    +-------------------+-------------------------------------------------------------------------------------------+
    | shell             | shell from paramiko - CLI login                                                           |
    +-------------------+-------------------------------------------------------------------------------------------+

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.x.x     | 03 Jul 2019   | Experimental                                                                      |
    | 2.x.x     |               |                                                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.0     | 19 Jul 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020 Jack Consoli'
__date__ = '19 Jul 2020'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.0'

import errno
import time
import http.client as httplib
import base64
import ssl
import json
import brcdapi.util as brcdapi_util
import pprint  # Debug

LOGIN_RESTCONF = "/rest/login"
LOGOUT_RESTCONF = "/rest/logout"


def basic_api_parse(obj):
    """Performs a read and basic parse of the conn.getresponse()

    :param obj: Response from conn.getresponse()
    :type obj: dict
    :return: Standard object used in all brcdapi and brcddb libraries
    :rtype: dict
    """
    try:
        # I could have checked for obj.status = 200 - < 300 and obj.reason = 'No Content', but this covers everything
        json_data = json.loads(obj.read())
    except:
        json_data = {}
    try:
        d = {}
        json_data.update({'_raw_data': d})
        d.update({'status': obj.status})
        d.update({'reason': obj.reason})
    except:  # I think logout is the only request that does not return a status and reason
        pass
    return json_data


def _get_connection(ip_addr, isHttps):

    if isHttps == "self":
        return httplib.HTTPSConnection(ip_addr, context=ssl._create_unverified_context())
    elif isHttps == "CA":
        return httplib.HTTPSConnection(ip_addr)  # Don't I need the certificate here?
    else:
        return httplib.HTTPConnection(ip_addr)


def _pyfos_logout(credential, ip_addr, isHttps):
    conn = _get_connection(ip_addr, isHttps)
    conn.request("POST", LOGOUT_RESTCONF, "", credential)
    resp = conn.getresponse()
    return basic_api_parse(resp.read())


def create_error(status, reason, msg):
    """Creates a standard error object

    :param status: Rest API status code.
    :type status: int
    :param reason: Rest API reason
    :type reason: str
    :param msg: Formatted error message(s)
    :type msg: str, list
    :return: error_obj
    :rtype: dict
    """
    ml = msg if isinstance(msg, list) else list(msg)
    el = [{'error-message': buf} for buf in ml]
    ret_dict = {
        '_raw_data': {
            'status': status,
            'reason': reason,
        },
        'errors': {
            'error': el,
        },
    }
    return ret_dict


def obj_status(obj):
    """Returns the status from API object.

    :param obj: API object
    :type obj: dict
    :return: status
    :rtype: int
    """
    try:
        return obj.get('_raw_data').get('status')
    except:
        return brcdapi_util.HTTP_OK


def is_error(obj):
    """Determines if an object returned from api_request() is an error object

    :param obj: Object returned from api_request()
    :type obj: dict
    :return: True - there is an error in the object (obj). False - no errors
    :rtype: bool
    """
    if obj is None:
        return False
    if 'errors' in obj:
        return True
    status = obj_status(obj)
    if isinstance(status, int):
        if status < 200 or status >= 300:
            return True
        return False
    return False


def obj_reason(obj):
    """Returns the reason from API object

    :param obj: API object
    :type obj: dict
    :return: Reason
    :rtype: str
    """
    try:
        return obj.get('_raw_data').get('reason')
    except:
        return ''


def obj_error_detail(obj):
    """Formats the error message detail into human readable format

    :param obj: API object
    :type obj: dict
    :return: Formatted error detail
    :rtype: str
    """
    try:
        error_list = obj.get('errors').get('error')
        if isinstance(error_list, dict):
            error_list = [error_list]  # in 8.2.1a and below, a single error was returned as a dict
        i = 0
        buf = ''
        for error_obj in error_list:
            buf += 'Error Detail ' + str(i) + ':'
            for k in error_obj.keys():
                d = error_obj.get(k)
                if isinstance(d, str):
                    buf += '\n  ' + k + ': ' + d
                elif isinstance(d, dict):
                    buf += '\n  ' + k + ':'
                    for k1 in d:
                        d1 = d.get(k1)
                        if isinstance(d1, str):
                            buf += '\n    ' + k1 + ': ' + d1
                        elif isinstance(d1, (int, float)):
                            buf += '\n    ' + k1 + ': ' + str(d1)
            i += 1
            buf += '\n'
        return buf
    except:  # A formatted error message isn't always present so this may happen
        return ''


def formatted_error_msg(obj):
    """Formats the error message into a human readable format

    :param obj: Object returned from get_request()
    :type obj: dict
    :return: msg
    :rtype: str
    """
    return 'Status: ' + str(obj_status(obj)) + '\nReason: ' + obj_reason(obj) + '\n' + obj_error_detail(obj)


def login(user, password, ip_addr, is_https='none'):
    """Establish a session to the FOS switch and return the session object

    :param user: User name to establish a session.
    :type user: str
    :param password: Password to establish a session.
    :type password: str
    :param ip_addr: IP address of the FOS switch with which to establish a session.
    :type ip_addr: str
    :param is_https: 'none' - http. 'self' https with a self-signed certificate. 'CA' https CA-signed certificate.
    :type is_https: str
    :return: Session object as described in the method description
    :rtype: dict
    """
    # Get connectction token
    conn = _get_connection(ip_addr, is_https)
    auth = user + ":" + password
    auth_encoded = base64.b64encode(auth.encode())
    credential = {"Authorization": "Basic " + auth_encoded.decode(), "User-Agent": "Rest-Conf"}
    credential.update({'Accept': 'application/yang-data+json'})  # Default response is XML. This forces JSON
    credential.update({'Content-Type': 'application/yang-data+json'})  # Also needed for a JSON response

    try:
        conn.request("POST", LOGIN_RESTCONF, "", credential)
    except:
        # Usually, we get here if the IP address was inaccessible or HTTPS was used before a certifiate was generated
        obj = create_error(brcdapi_util.HTTP_NOT_FOUND, 'Not Found', '')
        obj.update({'ip_addr': ip_addr})
        return obj

    # Attempt login
    resp = conn.getresponse()
    json_data = basic_api_parse(resp)
    content = resp.getheader('content-type')
    contentlist = content.split(";")
    if len(contentlist) == 2:
        json_data.update({'content-type': contentlist[0]})
        json_data.update({'content-version': contentlist[1]})
    else:
        json_data.update({'content-type': content})
        json_data.update({'content-version': None})
    credential.pop('Authorization')
    credential.update({'Authorization': resp.getheader('authorization')})
    json_data.update({'credential': credential})
    json_data.update({'ip_addr': ip_addr})
    json_data.update({'ishttps': is_https})
    json_data.update({'debug': False})
    return json_data


def logout(session):
    """Terminate a session to FOS.

    :param session: Dictionary of the session returned by login.
    :type session: dict
    :rtype: None.
    """
    conn = _get_connection(session.get('ip_addr'), session.get('ishttps'))
    conn.request("POST", LOGOUT_RESTCONF, "", session.get('credential'))
    resp = conn.getresponse()
    obj = basic_api_parse(resp.read())
    return obj

"""
Copyright 2023, 2024, 2025 Consoli Solutions, LLC.  All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may also obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.

The license is free for single customer use (internal applications). Use of this module in the production,
redistribution, or service delivery for commerce requires an additional license. Contact jack_consoli@yahoo.com for
details.

**Description**

SANnav API Login, logout, and error formatting.

**Primary Methods**

+-----------------------------+--------------------------------------------------------------------------------------+
| Method                      | Description                                                                         |
+=============================+======================================================================================+
| is_error()                  | Determines if an object returned from the SANnav API is an error object             |
+-----------------------------+--------------------------------------------------------------------------------------+
| formatted_error_msg()       | Formats the error message into a human readable format                              |
+-----------------------------+--------------------------------------------------------------------------------------+
| login()                     | Establish a session to the FOS switch and return the session object                 |
+-----------------------------+--------------------------------------------------------------------------------------+
| logout()                    | Terminate a session to FOS                                                          |
+-----------------------------+--------------------------------------------------------------------------------------+

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Documentation updates only.                                                           |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 25 Aug 2025   | Updated email address in __email__ only.                                              |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 19 Oct 2025   | Updated comments only.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2024, 2025 Consoli Solutions, LLC'
__date__ = '19 Oct 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.3'

from pprint import pprint
import http.client as httplib
import base64
import ssl
import json
import brcdapi.util as brcdapi_util
import brcdapi.log as brcdapi_log


def basic_api_parse(obj):
    """Performs a read and basic parse of the conn.getresponse()

    :param obj: Response from conn.getresponse()
    :type obj: dict
    :return: Standard object used in all brcdapi and brcddb libraries
    :rtype: dict
    """
    try:
        # I could have checked for obj.status => 200 or < 300 and obj.reason = 'No Content', but this covers everything
        json_data = json.loads(obj.read())
    except:  # TODO Should this be a TypeError?
        json_data = dict()
    try:
        d = dict()
        json_data.update({'_raw_data': d})
        d.update({'status': obj.status})
        d.update({'reason': obj.reason})
    except:  # TODO Should this be a TypeError?
        pass  # Some requests do not return a status and reason when the request was completed successfully
    return json_data


def _get_connection(ip_addr, ca):

    if ca == 'self':
        return httplib.HTTPSConnection(ip_addr, context=ssl._create_unverified_context())
    else:
        return httplib.HTTPSConnection(ip_addr, ca)


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
    ret_dict = dict(
        _raw_data=dict(status=status, reason=reason),
        errors=dict(error=el),
    )
    return ret_dict


def obj_status(obj):
    """Returns the status from API object.

    :param obj: API object
    :type obj: dict
    :return: status
    :rtype: int
    """
    try:
        return obj['_raw_data']['status']
    except KeyError:
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
    if 'error' in obj:
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
        return obj['_raw_data']['reason']
    except KeyError:
        return ''


def obj_error_detail(obj):
    """Formats the error message detail into human-readable format

    :param obj: API object
    :type obj: dict
    :return: Formatted error detail
    :rtype: str
    """
    try:
        return 'Error: ' + obj['error'] + '\nError Description: ' + obj['error_description']
    except KeyError:  # A formatted error message isn't always present so this may happen
        return ''


def formatted_error_msg(obj):
    """Formats the error message into a human-readable format

    :param obj: Object returned from get_request()
    :type obj: dict
    :return: msg
    :rtype: str
    """
    return 'Status: ' + str(obj_status(obj)) + '\nReason: ' + obj_reason(obj) + '\n' + obj_error_detail(obj)


def login(userid, pw, ip_addr, ca='self'):
    """Establish a session to the FOS switch and return the session object

    :param userid: Username to establish a session.
    :type userid: str
    :param pw: Password to establish a session.
    :type pw: str
    :param ip_addr: IP address of the FOS switch with which to establish a session.
    :type ip_addr: str
    :param ca: 'self' https with a self-signed certificate. 'CA' https CA-signed certificate.
    :type ca: str
    :return: Session object as described in the method description
    :rtype: dict
    """
    # Set up the connection and connection header
    credential = {
        'username': userid,
        'password': pw,
        'User-Agent': 'Rest-Conf',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    conn = _get_connection(ip_addr, ca)

    try:
        conn.request('POST', '/external-api/v1/login/', '', credential)
    except:  # TODO Should this be a TypeError?
        # Usually, we get here if the IP address was inaccessible or HTTPS was used before a certifiate was generated
        obj = create_error(brcdapi_util.HTTP_NOT_FOUND, 'Not Found', '')
        obj.update({'ip_addr': ip_addr})
        return obj

    # Attempt login
    resp = conn.getresponse()
    json_data = basic_api_parse(resp)
    content = resp.getheader('content-type')
    content_l = content.split(';')
    if len(content_l) == 2:
        json_data.update({'content-type': content_l[0]})
        json_data.update({'content-version': content_l[1]})
    else:
        json_data.update({'content-type': content})
        json_data.update({'content-version': None})
    credential.update(dict(Authorization=json_data.get('sessionId')))
    json_data.update(dict(conn=conn))
    json_data.update(dict(credential=credential))
    json_data.update(dict(ip_addr=ip_addr))
    json_data.update(dict(ca=ca))
    json_data.update(dict(debug=False))
    return json_data


def logout(session):
    """Terminate a session to SANnav.

    :param session: Dictionary of the session returned by login().
    :type session: dict
    :rtype: None.
    """
    conn = session.get('conn')
    conn.request('POST', '/external-api/v1/logout/', '', session.get('credential'))
    resp = conn.getresponse()
    obj = basic_api_parse(resp.read())
    return obj

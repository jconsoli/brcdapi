"""
Copyright 2023, 2024 Consoli Solutions, LLC.  All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may also obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.

The license is free for single customer use (internal applications). Use of this module in the production,
redistribution, or service delivery for commerce requires an additional license. Contact jack@consoli-solutions.com for
details.

:mod:`brcdapi.fos_auth` - Login, logout, and error formatting. With the exception of error handling, typically, the
remaining methods contained herein are only used by brcdapi.brcdapi_rest.

Primary Methods::

    +-----------------------+---------------------------------------------------------------------------------------+
    | Method                | Description                                                                           |
    +=======================+=======================================================================================+
    | basic_api_parse       | Performs a read and basic parse of the conn.getresponse()                             |
    +-----------------------+---------------------------------------------------------------------------------------+
    | create_error          | Creates a standard error object                                                       |
    +-----------------------+---------------------------------------------------------------------------------------+
    | obj_status            | Returns the status from API object.                                                   |
    +-----------------------+---------------------------------------------------------------------------------------+
    | is_error()            | Determines if an object returned from api_request() is an error object                |
    +-----------------------+---------------------------------------------------------------------------------------+
    | obj_reason            | Returns the reason from API object                                                    |
    +-----------------------+---------------------------------------------------------------------------------------+
    | obj_error_detail      | Formats the error message detail into human readable format. Typically only called    |
    |                       | from formatted_error_msg().                                                           |
    +-----------------------+---------------------------------------------------------------------------------------+
    | formatted_error_msg   | Formats the error message into a human readable format                                |
    +-----------------------+---------------------------------------------------------------------------------------+
    | login()               | Establish a session to the FOS switch and return the session object                   |
    +-----------------------+---------------------------------------------------------------------------------------+
    | logout()              | Terminate a session to FOS                                                            |
    +-----------------------+---------------------------------------------------------------------------------------+

Public Methods::

    +-----------------------------+----------------------------------------------------------------------------------+
    | Method                      | Description                                                                      |
    +=============================+==================================================================================+
    | basic_api_parse()           | Performs a read and basic parse of the conn.getresponse().                       |
    +-----------------------------+----------------------------------------------------------------------------------+
    | create_error()              | Intended for use within this module and brcdapi.brcdapi_rest only. Creates a     |
    |                             | standard error object                                                            |
    +-----------------------------+----------------------------------------------------------------------------------+
    | obj_status()                | Returns the status from API object.                                              |
    +-----------------------------+----------------------------------------------------------------------------------+
    | obj_reason()                | Returns the reason from API object                                               |
    +-----------------------------+----------------------------------------------------------------------------------+
    | obj_error_detail()          | Formats the error message detail into human readable format                      |
    +-----------------------------+----------------------------------------------------------------------------------+

Login Session::

    Not all parameters filled in by fos_auth.login

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
    | supported_uris    | dict: See brcdapi.util.uri_map                                                            |
    +-------------------+-------------------------------------------------------------------------------------------+
    | ssh               | SSH login session from paramiko - CLI login                                               |
    +-------------------+-------------------------------------------------------------------------------------------+
    | shell             | shell from paramiko - CLI login                                                           |
    +-------------------+-------------------------------------------------------------------------------------------+
    | uri_map           | dict: See brcdapi.util.add_uri_map() for details.                                         |
    +-------------------+-------------------------------------------------------------------------------------------+

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 4.0.0     | 04 Aug 2023   | Re-Launch                                                                         |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 4.0.1     | 06 Mar 2024   | Added user_id and user_pw to dict returned from login()                           |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024 Consoli Solutions, LLC'
__date__ = '06 Mar 2024'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack@consoli-solutions.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.1'

import http.client as httplib
import base64
import ssl
import json
import pprint
import brcdapi.util as brcdapi_util
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util
import brcdapi.fos_cli as fos_cli

_LOGIN_RESTCONF = '/rest/login'
_LOGOUT_RESTCONF = '/rest/logout'
_HEADER = 'application/yang-data+json'


def basic_api_parse(obj):
    """Performs a read and basic parse of conn.getresponse()

    :param obj: Response from conn.getresponse()
    :type obj: HTTPResponse
    :return: Standard object used in all brcdapi and brcddb libraries
    :rtype: dict
    """
    http_response, json_data = None, dict()  # http_response is returned so initialize in case Control-C out
    try:
        http_response = obj.read()
        if isinstance(http_response, bytes) and len(http_response) > 0:
            try:
                json_data = json.loads(http_response)
            except UnicodeDecodeError:
                return create_error(brcdapi_util.HTTP_INT_SERVER_ERROR,
                                    'Invalid data returned from FOS',
                                    msg='UnicodeDecodeError')
            except BaseException as e:
                try:
                    http_buf = 'None' if http_response is None else \
                        http_response.decode(encoding=brcdapi_util.encoding_type, errors='ignore')
                except BaseException as e0:
                    http_buf = 'Could not decode http_response. Exception is: ' + str(type(e0)) + ': ' + str(e0)
                brcdapi_log.exception(['Invalid data returned from FOS. Error code:',
                                       str(type(e)) + ': ' + str(e),
                                       '',
                                       'http_response:',
                                       http_buf],
                                      echo=True)
                return create_error(brcdapi_util.HTTP_INT_SERVER_ERROR, 'Invalid data returned from FOS')
        try:
            json_data.update(_raw_data=dict(status=obj.status, reason=obj.reason))
        except AttributeError:
            pass  # Some responses don't contain anything (obj is an empty dict)
        except BaseException as e:
            http_buf = 'None' if http_response is None else \
                http_response.decode(encoding=brcdapi_util.encoding_type, errors='ignore')
            brcdapi_log.exception(['Invalid data returned from FOS. Error code:',
                                   str(type(e)) + ': ' + str(e),
                                   '',
                                   'http_response:',
                                   http_buf],
                                  echo=True)
    except AttributeError:
        pass  # I think logout is the only time I get here.
    except BaseException as e:
        buf = 'Undetermined error parsing response'
        brcdapi_log.exception([str(type(e)) + ': ' + str(e), buf], echo=True)
        return create_error(brcdapi_util.HTTP_INT_SERVER_ERROR, buf)

    return json_data


def _get_connection(ip_addr, ca):

    if ca == 'self':
        return httplib.HTTPSConnection(ip_addr, context=ssl._create_unverified_context())
    if ca == 'none':
        return httplib.HTTPConnection(ip_addr)
    # Assume it's a certificate
    brcdapi_log.exception('Only "none" (HTTP) and "self" (self signed HTTPS) are supported at this time.', echo=True)
    raise ConnectionRefusedError


def create_error(status, reason, msg=None):
    """Creates a standard error object

    :param status: Rest API status code.
    :type status: int
    :param reason: Rest API reason
    :type reason: str
    :param msg: Formatted error message(s)
    :type msg: None, str, list
    :return: error_obj
    :rtype: dict
    """
    return dict(_raw_data=dict(status=status, reason=reason),
                errors=dict(error=[{'error-message': buf} for buf in gen_util.convert_to_list(msg)]))


def obj_status(obj):
    """Returns the status from API object.

    :param obj: API object
    :type obj: dict
    :return: status
    :rtype: int
    """
    return obj['_raw_data'].get('status') if '_raw_data' in obj else brcdapi_util.HTTP_OK


def is_error(obj):
    """Determines if an object returned from api_request() is an error object

    :param obj: Object returned from api_request()
    :type obj: dict
    :return: True - there is an error in the object (obj). False - no errors
    :rtype: bool
    """
    if obj is None:
        return False
    if not isinstance(obj, dict):
        brcdapi_log.exception('Expected type dict. Received type: ' + str(type(obj)), echo=True)
        return True
    status = obj_status(obj)
    if isinstance(status, int):
        if status < 200 or status >= 300:
            return True
        if 'errors' in obj:
            brcdapi_log.exception(['', 'Response contains good status and errors:', pprint.pformat(obj), ''], echo=True)
        return False
    if 'errors' in obj:
        return True
    return False


def obj_reason(obj):
    """Returns the reason from API object

    :param obj: API object
    :type obj: dict
    :return: Reason
    :rtype: str
    """
    return obj['_raw_data'].get('reason') if '_raw_data' in obj else ''


def obj_error_detail(obj):
    """Formats the error message detail into human-readable format. Typically only called from formatted_error_msg().

    :param obj: API object
    :type obj: dict
    :return: Formatted error detail
    :rtype: str
    """
    error_d = obj.get('errors')
    if error_d is None:
        return ''

    error_list = error_d.get('error')
    if error_list is None:
        return ''

    if isinstance(error_list, dict):
        error_list = [error_list]  # in 8.2.1a and below, a single error was returned as a dict
    i, buf = 0, ''
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
        i, buf = i + 1, buf + '\n'
    return buf


def formatted_error_msg(obj):
    """Formats the FOS responses into a human-readable format. Typically only used for error messages

    :param obj: Object returned from get_request()
    :type obj: dict
    :return: msg
    :rtype: str
    """
    if isinstance(obj, dict):
        buf = 'Status: ' + str(obj_status(obj)) + '\nReason: ' + obj_reason(obj) + '\n' + obj_error_detail(obj)
    else:
        buf = 'Expected type dict. Received type: ', str(type(obj))
        brcdapi_log.exception(buf, echo=True)
    return buf


def login(user, password, ip_addr, in_http_access=None):
    """Establish a session to the FOS switch and return the session object

    :param user: Username to establish a session.
    :type user: str
    :param password: Password to establish a session.
    :type password: str
    :param ip_addr: Management IP address of chassis
    :type ip_addr: str
    :param in_http_access: 'none' or None for HTTP. For HTTPS, only 'self' is supported.
    :type in_http_access: str, None
    :return: Session object as described in the module header. See Login Session
    :rtype: dict
    """
    # Get and validate HTTP or HTTPS method
    http_access = 'none' if in_http_access is None else in_http_access
    if not isinstance(http_access, str) or http_access not in ('none', 'self'):
        buf = 'HTTP access other than "none" and "self" has not been implemented. Entered HTTPS method was: ' +\
              str(http_access)
        brcdapi_log.log(buf, echo=True)
        return create_error(brcdapi_util.HTTP_BAD_REQUEST,
                            'Unsupported login',
                            msg=[str(type(http_access)), str(http_access)])

    # Get connection token
    try:
        conn = _get_connection(ip_addr, http_access)
    except ConnectionRefusedError:
        return create_error(brcdapi_util.HTTP_NOT_FOUND, 'Connection refused').update(ip_addr=ip_addr)
    auth = user + ':' + password
    auth_encoded = base64.b64encode(auth.encode())
    credential = {
        'Authorization': "Basic " + auth_encoded.decode(),
        'User-Agent': 'Rest-Conf',
        'Accept': _HEADER,  # Default response is XML. This forces JSON
        'Content-Type': _HEADER  # Also needed for a JSON response
    }

    try:
        conn.request('POST', _LOGIN_RESTCONF, '', credential)
    except (TimeoutError, OSError):
        return create_error(brcdapi_util.HTTP_NOT_FOUND, 'Not Found').update(ip_addr=ip_addr)
    except BaseException as e:
        e_buf = str(type(e)) + ': ' + str(e)
        brcdapi_log.exception(['', 'Unknown exception: ', e_buf], echo=True)
        return create_error(brcdapi_util.HTTP_NOT_FOUND, 'Not Found', e_buf).update(ip_addr=ip_addr)

    # Attempt login
    resp = conn.getresponse()
    json_data = basic_api_parse(resp)
    content = resp.getheader('content-type')
    content_l = content.split(';')
    if len(content_l) == 2:
        json_data.update({'content-type': content_l[0], 'content-version': content_l[1]})
    else:
        json_data.update({'content-type': content, 'content-version': None})
    credential.update({'Authorization': resp.getheader('authorization')})
    json_data.update(conn=conn,
                     credential=credential,
                     ip_addr=ip_addr,
                     user_id=user,
                     user_pw=password,
                     ishttps=False if http_access == 'none' else True,
                     ssh_login=None,  # Used in fos_cli.py
                     ssh_fault=False)  # Used in fos_cli.py to indicate an SSH login was attempted but failed.

    return json_data


def logout(session):
    """Terminate a session to FOS.

    :param session: Dictionary of the session returned by login.
    :type session: dict
    :rtype: None.
    """
    # CLI logout
    fos_cli.logout(session)

    # API logout
    conn = session.get('conn')
    conn.request('POST', _LOGOUT_RESTCONF, '', session.get('credential'))
    return basic_api_parse(conn.getresponse().read())

# Copyright 2019, 2020, 2021, 2022 Jack Consoli.  All rights reserved.
#
# NOT BROADCOM SUPPORTED
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
:mod:`brcdapi_rest` - Provides a single interface to the RESTConf API in FOS.

Methods in this module are used to establish, modify, send requests, and terminate sessions. Also does the following:

    * Errors indicating zero length lists are converted to 0 length lists.
    * Errors for HA requests on fixed port switches are converted to 0 length lists.
    * Service unavailable - sleep 4 seconds and retry request up to 5 times
    * Fabric busy - wait 10 seconds and retry request up to 5 times
    * Service unavailable - wait 30 seconds and retry request
    * Debug mode allows for off line work. Used with GET only

This is a thin interface. Logging is only performed in debug mode. It is the responsibility of the next higher layer,
such as the brcddb libraries, to control what gets printed to the log.

Primary Methods::

    +-----------------------------+----------------------------------------------------------------------------------+
    | Method                      | Description                                                                      |
    +=============================+==================================================================================+
    | login()                     | Adds a wrapper around brcdapi.fos_auth.login()                                 |
    +-----------------------------+----------------------------------------------------------------------------------+
    | logout()                    | Adds a wrapper around brcdapi.pyfo_auth.logout()                                 |
    +-----------------------------+----------------------------------------------------------------------------------+
    | api_request()               | Single interface to the FOS REST API. Performs a Rest API request. Handles low   |
    |                             | levels protocol errors and retries when the switch is busy. Also cleans up empty |
    |                             | responses that are returned as errors when they are just empty lists.            |
    +-----------------------------+----------------------------------------------------------------------------------+
    | get_request()               | Fill out full URI and add debug wrapper around a GET before calling api_request()|
    +-----------------------------+----------------------------------------------------------------------------------+
    | send_request()              | Performs a Rest API request. Simplifies requests by pre-pending '/rest/running/' |
    +-----------------------------+----------------------------------------------------------------------------------+

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
    | 3.0.2     | 22 Aug 2020   | Added verbose debug when debug mode is to read file                               |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.3     | 09 Jan 2021   | Updated comments and some PEP8 cleanup                                            |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.4     | 13 Feb 2021   | Removed the shebang line                                                          |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.5     | 14 Nov 2021   | Deprecated pyfos_auth. Added set_debug()                                          |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.6     | 31 Dec 2021   | Improved error messages and comments. No functional changes                       |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.7     | 28 Apr 2022   | Automated build of brcdapi.uri_map                                                |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020, 2021, 2022 Jack Consoli'
__date__ = '28 Apr 2022'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.7'

import re
import http.client as httplib
import json
import ssl
import time
import pprint
import os
import brcdapi.fos_auth as fos_auth
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util
import brcdapi.gen_util as gen_util

_DISABLE_OPTIONS_CHECK = True  # When False, makes sure OPTIONS was requested for each URI
_MAX_RETRIES = 5  # Maximum number of times to retry a request
_SVC_UNAVAIL_WAIT = 4  # Time, in seconds, to wait before retrying a request that returned 503, service unavaliable
_FABRIC_BUSY_WAIT = 10  # Time, in seconds, to wait before retrying a request due to a fabric usy

_DEBUG = False
# _DEBUG_MODE is only used when _DEBUG == True as follows:
# 0 - Perform all requests normally. Write all responses to a file
# 1 - Do not perform any I/O. Read all responses from file into response and fake a successful login
_DEBUG_MODE = 0
# _DEBUG_PREFIX is only used when _DEBUG == True. Folder where all the json dumps of API requests are read/written.
_DEBUG_PREFIX = 'eng_raw_28_apr_2022/'
verbose_debug = False  # When True, prints data structures. Only useful for debugging. Can be set externally

# Programmer's Tip: If there is significant activity on the switch from other sources (AMP, BNA, SANNav, ...) it may
# take a long time for a response. Also, some operations, such as logical switch creation, can take 20-30 sec. If the
# timeout, _TIMEOUT, is too short, HTTP connect lib raises an exception but the session is not terminated on the switch.
_TIMEOUT = 60   # Number of seconds to wait for a response from the API.
_clean_debug_file = re.compile(r'[?=/]')


def login(user_id, pw, ip_addr, https='none'):
    """Performs a login to the device using fos_auth.login

    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param ip_addr: IP address
    :type ip_addr: str
    :param https: If 'CA' or 'self', uses https to login. Otherwise, http.
    :type https: str
    :return: Session object from brcdapi.fos_auth.login()
    :rtype: dict
    """
    global _DEBUG, _DEBUG_MODE

    # Login
    if _DEBUG and _DEBUG_MODE == 1:
        session = dict(_debug_name=ip_addr.replace('.', '_'), debug=True, uri_map=brcdapi_util.default_uri_map)
    else:
        session = fos_auth.login(user_id, pw, ip_addr, https)
        if fos_auth.is_error(session):
            return session
        if _DEBUG:
            session.update(_debug_name=ip_addr.replace('.', '_'))

    # Build the URI map
    obj = get_request(session, 'brocade-module-version')
    if fos_auth.is_error(obj):
        brcdapi_log.exception(brcdapi_util.mask_ip_addr(ip_addr) + ' ERROR: ' + fos_auth.formatted_error_msg(obj), True)
    else:
        try:
            brcdapi_util.add_uri_map(session, obj)
        except BaseException as e:
            logout(session)
            session = fos_auth.create_error(brcdapi_util.HTTP_INT_SERVER_ERROR,
                                            'Programming error encountered in brcdapi_util.add_uri_map.',
                                            [str(e)])

    return session


def logout(session):
    """Logout of a Rest API session using fos_auth.logout

    :param session: FOS session object
    :type session: dict
    """
    return fos_auth.logout(session) if not (_DEBUG and _DEBUG_MODE == 1) else dict()


def vfid_to_str(vfid):
    """Depracated. Use brcdapi.util.vfid_to_str

    :param vfid: FOS session object
    :type vfid: int
    :return: '?vf-id=x' where x is the vfid converted to a str. If vfid is None then just '' is returned
    :rtype: str
    """
    return brcdapi_util.vfid_to_str(vfid)


def _set_methods(session, uri, op):
    """Set the value in the uri_map['op'] for the uri. Intended for error handling only.

    :param session: FOS session object
    :type session: dict
    :param uri: full URI
    :type uri: str
    :param op: Value to set in uri_map['op'].
    """
    cntl_d = brcdapi_util.session_cntl(session, uri)
    if isinstance(cntl_d, dict):
        cntl_d.update(op=op)


def _add_methods(session, http_response, uri):
    """Adds supported methods to the session

    :param session: FOS session object
    :type session: dict
    :param http_response: HTTPConnection.getresponse()
    :type http_response: HTTPResponse
    :param uri: full URI
    :type uri: str
    """
    cntl_d = brcdapi_util.session_cntl(session, uri)
    if not isinstance(cntl_d, dict):
        return

    header_l = http_response.getheaders()
    if isinstance(header_l, (list, tuple)):
        for t in header_l:
            if len(t) >= 2:
                if isinstance(t[0], str) and t[0] == 'Allow':
                    cntl_d.update(op=brcdapi_util.op_yes, methods=t[1].replace(' ', '').split(','))
                    return
    cntl_d.update(op=brcdapi_util.op_not_supported)


def _check_methods(session, uri):
    """Checks to see if the supported methods for the uri have been added and if not, captures and adds them

    :param session: FOS session object
    :type session: dict
    :param uri: full URI
    :type uri: str
    :return: True if supported methods should be checked.
    :rtype: bool
    """
    global _DISABLE_OPTIONS_CHECK

    if _DISABLE_OPTIONS_CHECK:
        return False

    d = gen_util.get_key_val(session.get('uri_map'), uri)
    if d is None:
        d = gen_util.get_key_val(session.get('uri_map'), 'running/' + uri)  # The old way didn't include 'running/'
    if isinstance(d, dict):
        supported_methods = d.get('op')
        if isinstance(supported_methods, int):
            if supported_methods == brcdapi_util.op_no:
                return True
    else:
        brcdapi_log.log('UNKNOWN URI: ' + uri)

    return False


def _api_request(session, uri, http_method, content):
    """Single interface to the FOS REST API. Performs a Rest API request. Only tested with GET, PATCH, POST, and DELETE.

    :param session: FOS session object
    :type session: dict
    :param uri: full URI
    :type uri: str
    :param http_method: Method for HTTP connect. 'GET', 'PATCH', 'POST', etc.
    :type http_method: str
    :param content: The content, in Python dict, to be converted to JSON and sent to switch.
    :type content: dict
    :return: Response and status in fos_auth.is_error() and fos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    if _DEBUG and _DEBUG_MODE == 1 and http_method == 'OPTIONS':
        return dict(_raw_data=dict(status=brcdapi_util.HTTP_NO_CONTENT, reason='OK'))

    if http_method != 'OPTIONS' and _check_methods(session, uri.replace('/rest/', '')):
        _api_request(session, uri, 'OPTIONS', dict())

    if verbose_debug:
        buf = ['_api_request() - Send:', 'Method: ' + http_method, 'URI: ' + uri, 'content:', pprint.pformat(content)]
        brcdapi_log.log(buf, True)

    # Set up the headers and JSON data
    header = session.get('credential')
    if header is None:
        return fos_auth.create_error(brcdapi_util.HTTP_FORBIDDEN, 'No login session', list())
    header.update({'Accept': 'application/yang-data+json'})
    header.update({'Content-Type': 'application/yang-data+json'})
    conn = session.get('conn')

    # Send the request and get the response
    json_data = json.dumps(content) if content is not None and len(content) > 0 else None
    try:
        conn.request(http_method, uri, json_data, header)
    except BaseException as e:
        obj = fos_auth.create_error(brcdapi_util.HTTP_NOT_FOUND,
                                    'Not Found',
                                    ['Typical of switch going offline or pre-FOS 8.2.1c', str(e)])
        if 'ip_addr' in session:
            obj.update(ip_addr=session.get('ip_addr'))
        return obj
    try:
        http_response = conn.getresponse()
        json_data = fos_auth.basic_api_parse(http_response)
        if http_method == 'OPTIONS':
            if fos_auth.is_error(json_data):
                _set_methods(session, uri, brcdapi_util.op_not_supported)
            else:
                _add_methods(session, http_response, uri)
        if verbose_debug:
            brcdapi_log.log(['_api_request() - Response:', pprint.pformat(json_data)], True)
    except TimeoutError:
        buf = 'Time out processing ' + uri + '. Method: ' + http_method
        brcdapi_log.log(buf, True)
        obj = fos_auth.create_error(brcdapi_util.HTTP_REQUEST_TIMEOUT, buf, '')
        return obj
    except BaseException as e:
        brcdapi_log.exception('Unexpected error, ' + str(e), True)
        raise 'Fault'

    # Do some basic parsing of the response
    tl = uri.split('?')[0].split('/')
    cmd = tl[len(tl) - 1]
    if fos_auth.is_error(json_data):
        msg = ''
        try:
            msg = json_data['errors']['error']['error-message']
        except BaseException as e:
            if '_raw_data' not in json_data:  # Make sure it's not an error without any detail
                first_e = str(e)
                try:
                    # The purpose of capturing the message is to support the code below that works around a defect in
                    # FOS whereby empty lists or no change PATCH requests are returned as errors. In the case of
                    # multiple errors, I'm assuming the first error is the same for all errors. For any code I wrote,
                    # that will be true. Since I know this will be fixed in a future version of FOS, I took the easy way
                    msg = json_data['errors']['error'][0]['error-message']
                except BaseException as e:
                    brcdapi_log.exception(['Invalid data returned from FOS:', first_e, str(e)])
                    msg = ''
        try:
            if http_method == 'GET' and json_data['_raw_data']['status'] == brcdapi_util.HTTP_NOT_FOUND and \
                    json_data['_raw_data']['reason'] == 'Not Found':
                ret_obj = dict(cmd=list())  # It's really just an empty list
            elif http_method == 'GET' and json_data['_raw_data']['status'] == brcdapi_util.HTTP_BAD_REQUEST and \
                    msg == 'No entries in the FDMI database':
                ret_obj = dict(cmd=list())  # It's really just an empty list
            elif http_method == 'GET' and json_data['_raw_data']['status'] == brcdapi_util.HTTP_BAD_REQUEST and \
                    json_data['_raw_data']['reason'] == 'Bad Request' and 'Not supported on this platform' in msg:
                ret_obj = dict(cmd=list())  # It's really just an empty list
            elif http_method == 'PATCH' and json_data['_raw_data']['status'] == brcdapi_util.HTTP_BAD_REQUEST and \
                    json_data['_raw_data']['reason'] == 'Bad Request' and \
                    ('No Change in Configuration' in msg or 'Same configuration' in msg):
                # Sometimes FOS 8.2.1 returns no change as this error and sometimes it doesn't. Expected fix for no
                # change with PATCH is to always return good status (204). Note that according to RFC 5789, no change is
                # not considered an error.
                ret_obj = dict(cmd=list())
            else:
                ret_obj = json_data
        except (TypeError, KeyError):
            try:
                status = json_data['_raw_data']['status']
            except (TypeError, KeyError):
                status = 0
                msg = 'No status provided.'
            try:
                reason = json_data['_raw_data']['reason']
            except (TypeError, KeyError):
                reason = 'No reason provided'
            ret_obj = fos_auth.create_error(status, reason, msg)
    elif 'Response' in json_data:
        obj = json_data.get('Response')
        ret_obj = obj if bool(obj) else {cmd: list()}
    else:
        raw_data = json_data.get('_raw_data')
        if raw_data is not None:
            status = brcdapi_util.HTTP_BAD_REQUEST if raw_data.get('status') is None else raw_data.get('status')
            reason = '' if raw_data.get('reason') is None else raw_data.get('reason')
        else:
            status = brcdapi_util.HTTP_BAD_REQUEST
            reason = 'Invalid response from the API'
        if status < 200 or status >= 300:
            ret_obj = fos_auth.create_error(status, reason, '')
        else:
            ret_obj = dict()

    return ret_obj


def _retry(obj):
    """Determines if a request should be retried.

    :param obj: Object returned from _api_request()
    :type obj: dict
    :return retry_flag: True - request should be retried. False - request should not be retried.
    :rtype retry_flag: bool
    :return delay: Time, in seconds, to wait for retrying the request
    :rtype delay: int
    """
    status = fos_auth.obj_status(obj)
    reason = fos_auth.obj_reason(obj) if isinstance(fos_auth.obj_reason(obj), str) else ''
    if isinstance(status, int) and status == 503 and isinstance(reason, str) and 'Service Unavailable' in reason:
        brcdapi_log.log('FOS API services unavailable. Will retry in ' + str(_SVC_UNAVAIL_WAIT) + ' seconds.', True)
        return True, _SVC_UNAVAIL_WAIT
    if status == brcdapi_util.HTTP_BAD_REQUEST and 'The Fabric is busy' in fos_auth.formatted_error_msg(obj):
        brcdapi_log.log('Fabric is busy. Will retry in ' + str(_FABRIC_BUSY_WAIT) + ' seconds.')
        return True, _FABRIC_BUSY_WAIT
    return False, 0


def api_request(session, uri, http_method, content):
    """Interface in front of _api_request to handle retries when services are unavailable

    :param session: Session object returned from login()
    :type session: dict
    :param uri: full URI
    :type uri: str
    :param http_method: Method for HTTP connect.
    :param content: The content, in Python dict, to be converted to JSON and sent to switch.
    :type content: dict
    :return: Response and status in fos_auth.is_error() and fos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    global _MAX_RETRIES

    if uri is None:  # An error occurred in brcdapi_util.format_uri()
        buf = 'Missing URI'
        brcdapi_log.exception(buf, True)
        return fos_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'Missing URI', buf)
    obj = _api_request(session, uri, http_method, content)
    retry_count = _MAX_RETRIES
    retry_flag, wait_time = _retry(obj)
    while retry_flag and retry_count > 0:
        time.sleep(wait_time)
        obj = _api_request(session, uri, http_method, content)
        retry_count -= 1
        retry_flag, wait_time = _retry(obj)
    return obj


def get_request(session, ruri, fid=None):
    """Fill out full URI and add debug wrapper around a GET before calling api_request().

    :param session: Session object returned from login()
    :type session: dict
    :param ruri: URI. The prefix, such as '/rest/running/', is added so do not include.
    :type ruri: str
    :param fid: Fabric ID
    :type fid: int, None
    :return: Response and status in fos_auth.is_error() and fos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    if _DEBUG:
        buf = '' if fid is None else brcdapi_util.vfid_to_str(fid)
        file = _DEBUG_PREFIX + _clean_debug_file.sub('_', session.get('_debug_name') + '_' +
                                                     ruri.replace('running/', '') + buf + '.txt')

    if _DEBUG and _DEBUG_MODE == 1:
        try:
            f = open(file, "r")
            json_data = json.load(f)
            f.close()
            if verbose_debug:
                ml = ['api_request() - Send:',
                      'Method: GET', 'URI: ' + brcdapi_util.format_uri(session, ruri, fid),
                      'api_request() - Response:',
                      pprint.pformat(json_data)]
                brcdapi_log.log(ml, True)
        except FileNotFoundError:
            return fos_auth.create_error(brcdapi_util.HTTP_NOT_FOUND, 'File not found: ', [file])
        except BaseException as e:
            brcdapi_log.log('Unknown error, ' + str(e) + ' encountered opening ' + file, True)
            raise
    else:
        json_data = api_request(session, brcdapi_util.format_uri(session, ruri, fid), 'GET', dict())
    if _DEBUG and _DEBUG_MODE == 0:
        try:
            with open(file, 'w') as f:
                f.write(json.dumps(json_data))
            f.close()
        except FileNotFoundError:
            brcdapi_log.log('\nThe folder for ' + file + ' does not exist.', True)

    return json_data


def send_request(session, ruri, http_method, content, fid=None):
    """Performs a Rest API request. Simplifies requests by pre-pending '/rest/running/'

    :param session: Session object returned from login()
    :type session: dict
    :param ruri: URI less '/rest/running/'
    :type ruri: str
    :param http_method: Method (PATCH, POST, DELETE, PUT ...) for HTTP connect.
    :param content: The content, in Python dict, to be converted to JSON and sent to switch.
    :type content: dict
    :param fid: Fabric ID
    :type fid: int, None
    :return: Response and status in is_error() and fos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    return api_request(session, brcdapi_util.format_uri(session, ruri, fid), http_method, content)


def set_debug(debug, debug_mode=None, debug_folder=None):
    """Programmatically set _DEBUG, _DEBUG_MODE, _DEBUG_PREFIX

    :param debug: Set _DEBUG. If True, use debug_mode. If False, debug_mode and debug_folder are ignored.
    :type debug: bool
    :param debug_mode: If debug is True. 0: Process requests normally and write to debug_folder. 1: Do not perform any \
        requests. Read all requests from data stored when debug_mode was 0 and debug True.
    :type debug_mode: int, None
    :param debug_folder: Folder name where all the json dumps of API requests are read/written. If the folder does not \
        exist it is created with 777 access (that means all access rights).
    :type debug_folder: str, None
    :return: Status. If true, debug mode was successfully set.
    :rtype: bool
    """
    global _DEBUG, _DEBUG_MODE, _DEBUG_PREFIX

    _DEBUG = debug
    if debug:
        if isinstance(debug_mode, int) and 0 <= debug_mode <= 1:
            _DEBUG_MODE = debug_mode
            x = len(debug_folder) if isinstance(debug_folder, str) else 0
            if x > 0:
                _DEBUG_PREFIX = debug_folder[0:x-1] if debug_folder[x-1] == '/' or debug_folder[x-1] == '\\' \
                    else debug_folder
                try:
                    os.mkdir(_DEBUG_PREFIX)
                except FileExistsError:
                    pass
                _DEBUG_PREFIX += '/'
            else:
                buf = 'Invalid debug_folder type. debug_folder type must be str. Type is: ' + str(type(debug_folder))
                brcdapi_log.exception(buf, True)
                return False
        else:
            buf = 'Invalid debug_mode. debug_mode must be an integer of value 0 or 1. debug_mode type: ' + \
                  str(type(debug_mode)) + ', value: ' + str(debug_mode)
            brcdapi_log.exception(buf, True)
            return False

    return True

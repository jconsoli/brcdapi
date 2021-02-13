# Copyright 2019, 2020, 2021 Jack Consoli.  All rights reserved.
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
    | login()                     | Adds a wrapper around brcdapi.pyfos_auth.login()                                 |
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

Support Methods::

    +-----------------------------+----------------------------------------------------------------------------------+
    | Method                      | Description                                                                      |
    +=============================+==================================================================================+
    | vfid_to_str()               | Converts a FID to a string, '?vf-id=xx' to be appended to a URI                  |
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
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020, 2021 Jack Consoli'
__date__ = '13 Feb 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.4'

import http.client as httplib
import json
import ssl
import time
import pprint
import brcdapi.pyfos_auth as pyfos_auth
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util

_MAX_RETRIES = 5  # Maximum number of times to retry a request
_SVC_UNAVAIL_WAIT = 4  # Time, in seconds, to wait before retrying a request that returned 503, service unavaliable
_FABRIC_BUSY_WAIT = 10  # Time, in seconds, to wait before retrying a request due to a fabric busy

_DEBUG = False
_DEBUG_MODE = 1  # Only used when _DEBUG == True
                # 0 - Perform all requests normally. Write all responses to a file
                # 1 - Do not perform any I/O. Read all responses from file into response and fake a successful login
_DEBUG_PREFIX = 'SQA_97_Raw_1_Sep_2020/'  # Can be any valid folder name. The folder is not created. It must already
                    # exist. This is where all the json dumps of API requests are read/written.
verbose_debug = False  # When True, prints data structures. Only useful for debugging. Can be set externally

# Programmer's Tip: If there is significant activity on the switch from other sources (AMP, BNA, SANNav, ...) it may
# take a long time for a response. Also, some operations, such as logical switch creation, can take 20-30 sec. If the
# timeout, _TIMEOUT, is too short, HTTP connect lib raises an exception but the session is not terminated on the switch.
_TIMEOUT = 60   # Number of seconds to wait for a response from the API.
_VF_ID = '?vf-id='


def login(user_id, pw, ip_addr, https='none'):
    """Performs a login to the device using pyfos_auth.login

    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param ip_addr: IP address
    :type ip_addr: str
    :param https: If 'CA' or 'self', uses https to login. Otherwise, http.
    :type https: str
    :return: PyFOS session object
    :rtype: dict
    """
    if _DEBUG and _DEBUG_MODE == 1:
        return {'_debug_name': ip_addr.replace('.', '_'), 'debug': True}
    session = pyfos_auth.login(user_id, pw, ip_addr, https)
    if not pyfos_auth.is_error(session) and _DEBUG:
        session.update(dict(_debug_name=ip_addr.replace('.', '_')))
    return session


def logout(session):
    """Logout of a Rest API session using pyfos_auth.logout

    :param session: PyFOS session object
    :type session: dict
    """
    if not (_DEBUG and _DEBUG_MODE == 1):
        return pyfos_auth.logout(session)
    else:
        return dict()


def vfid_to_str(vfid):
    """Converts a FID to a string, '?vf-id=xx' to be appended to a URI that requires a FID

    :param vfid: PyFOS session object
    :type vfid: int
    :return: '?vf-id=x' where x is the vfid converted to a str. If vfid is None then just '' is returned
    :rtype: str
    """
    return '' if vfid is None else _VF_ID + str(vfid)


def _http_connection(session):
    """Builds the HTTP(S) connection header

    :param session: PyFOS session object
    :type session: dict
    :return: HTTP(S) connection header
    :rtype: dict
    """
    ip_addr = session.get("ip_addr")
    is_https = session.get("ishttps")

    if is_https == "self":
        conn = httplib.HTTPSConnection(
                ip_addr, timeout=_TIMEOUT, context=ssl._create_unverified_context())
    elif is_https == "CA":
        conn = httplib.HTTPSConnection(ip_addr, timeout=_TIMEOUT)
    else:
        conn = httplib.HTTPConnection(ip_addr, timeout=_TIMEOUT)

    return conn


def _api_request(session, uri, http_method, content):
    """Single interface to the FOS REST API. Performs a Rest API request. Only tested with GET, PATCH, POST, and DELETE.

    :param session: PyFOS session object
    :type session: dict
    :param uri: full URI
    :type uri: str
    :param http_method: Method for HTTP connect. Only tested with 'PATCH' and 'POST'.
    :type http_method: str
    :param content: The content, in Python dict, to be converted to JSON and sent to switch.
    :type content: dict
    :return: Response and status in pyfos_auth.is_error() and pyfos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    if verbose_debug:
        buf = ['api_request() - Send:', 'Method: ' + http_method, 'URI: ' + uri, 'content:', pprint.pformat(content)]
        brcdapi_log.log(buf, True)

    # Set up the headers and JSON data
    header = session.get('credential')
    header.update({'Accept': 'application/yang-data+json'})
    header.update({'Content-Type': 'application/yang-data+json'})
    conn = session.get('conn')

    # Send the request and get the response
    json_data = json.dumps(content) if content is not None and len(content) > 0 else None
    try:
        conn.request(http_method, uri, json_data, header)
    except:
        obj = pyfos_auth.create_error(brcdapi_util.HTTP_NOT_FOUND,
                                      'Not Found', 'Typical of switch going offline or pre-FOS 8.2.1c')
        if 'ip_addr' in session:
            obj.update(dict(ip_addr=session.get('ip_addr')))
        return obj
    try:
        json_data = pyfos_auth.basic_api_parse(conn.getresponse())
        if verbose_debug:
            brcdapi_log.log(['api_request() - Response:', pprint.pformat(json_data)], True)
    except:
        buf = 'Time out processing ' + uri + '. Method: ' + http_method
        brcdapi_log.log(buf, True)
        obj = pyfos_auth.create_error(brcdapi_util.HTTP_REQUEST_TIMEOUT, buf, '')
        return obj


    # Do some basic parsing of the response
    tl = uri.split('?')[0].split('/')
    cmd = tl[len(tl) - 1]
    if pyfos_auth.is_error(json_data):
        try:
            msg = json_data['errors']['error']['error-message']
        except:
            try:
                # The purpose of capturing the message is to support the code below that works around a defect in FOS
                # whereby empty lists or no change PATCH requests are returned as errors. In the case of multiple
                # errors, I'm assuming the first error is the same for all errors. For any code I wrote, that will be
                # true. Since I know this will be fixed in a future version of FOS, I took the easy way out.
                msg = json_data['errors']['error'][0]['error-message']
            except:
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
        except:
            try:
                status = json_data['_raw_data']['status']
            except:
                status = 0
                msg = 'No status provided.'
            try:
                reason = json_data['_raw_data']['reason']
            except:
                reason = 'No reason provided'
            ret_obj = pyfos_auth.create_error(status, reason, msg)
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
            ret_obj = pyfos_auth.create_error(status, reason, '')
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
    status = pyfos_auth.obj_status(obj)
    reason = pyfos_auth.obj_reason(obj) if isinstance(pyfos_auth.obj_reason(obj), str) else ''
    if isinstance(status, int) and status == 503 and isinstance(reason, str) and 'Service Unavailable' in reason:
        brcdapi_log.log('FOS API services unavailable. Will retry in ' + str(_SVC_UNAVAIL_WAIT) + ' seconds.', True)
        return True, _SVC_UNAVAIL_WAIT
    if status == brcdapi_util.HTTP_BAD_REQUEST and 'The Fabric is busy' in pyfos_auth.formatted_error_msg(obj):
        brcdapi_log.log('Fabric is busy. Will retry in ' + str(_FABRIC_BUSY_WAIT) + ' seconds.')
        return True, _FABRIC_BUSY_WAIT
    return False, 0


def _format_uri(kpi, fid):
    """Formats a full URI for a KPI.

    :param kpi: Rest KPI
    :type kpi: str
    :param fid: Fabric ID
    :type fid: int, None
    :return: Full URI
    :rtype: str
    """
    l = kpi.split('/')
    if len(l) > 2:
        lookup_kpi = '/'.join(l[0:2])
        remaining_l = l[2:]
    else:
        lookup_kpi = kpi
        remaining_l = list()
    try:
        buf = brcdapi_util.uri_map[lookup_kpi]['uri']
        if len(remaining_l) > 0:
            buf += '/' + '/'.join(remaining_l)
        if brcdapi_util.uri_map[lookup_kpi]['fid']:
            buf += vfid_to_str(fid)
        return buf
    except:
        buf = '/rest/running/' + kpi + vfid_to_str(fid)
        brcdapi_log.log('ERROR: Unknown KPI: ' + lookup_kpi + '. Using best guess: ' + buf, True)
        brcdapi_log.flush()
        return buf


def api_request(session, uri, http_method, content):
    """Interface in front of _api_request to handle retries when services are unavailable

    :param session: Session object returned from login()
    :type session: dict
    :param uri: full URI
    :type uri: str
    :param http_method: Method for HTTP connect.
    :param content: The content, in Python dict, to be converted to JSON and sent to switch.
    :type content: dict
    :return: Response and status in pyfos_auth.is_error() and pyfos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    global _MAX_RETRIES

    if uri is None:  # An error occurred in _format_uri()
        buf = 'Missing URI'
        brcdapi_log.exception(buf, True)
        return pyfos_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'Missing URI', buf)
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
    :return: Response and status in pyfos_auth.is_error() and pyfos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    if _DEBUG:
        buf = '' if fid is None else vfid_to_str(fid)
        file = session.get('_debug_name') + '_' + ruri + buf + '.txt'
        file = file.replace('?', '_')
        file = file.replace('=', '_')
        file = file.replace('/', '_')
        file = _DEBUG_PREFIX + file

    if _DEBUG and _DEBUG_MODE == 1:
        try:
            f = open(file, "r")
            json_data = json.load(f)
            f.close
            if verbose_debug:
                brcdapi_log.log(['api_request() - Send:', 'Method: GET', 'URI: ' + _format_uri(ruri, fid)], True)
                brcdapi_log.log(['api_request() - Response:', pprint.pformat(json_data)], True)
        except:
            brcdapi_log.log('Unable to open ' + file + '. All processing aborted', True)
            raise
    else:
        json_data = api_request(session, _format_uri(ruri, fid), 'GET', '')
    if _DEBUG and _DEBUG_MODE == 0:
        try:
            with open(file, 'w') as f:
                f.write(json.dumps(json_data))
            f.close()
        except:
            buf = '\nError writting to ' + file + '. This usually happens when _DEBUG is True '\
                  'and a folder is specified in the file name that doesn\'t exist'
            buf += ' but the folder does not exist.\n'
            brcdapi_log.log(buf, True)
            raise

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
    :return: Response and status in is_error() and pyfos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    return api_request(session, _format_uri(ruri, fid), http_method, content)

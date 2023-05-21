# Copyright 2019, 2020, 2021, 2022, 2023 Jack Consoli.  All rights reserved.
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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.bp
# See the License for the specific language governing permissions and
# limitations under the License.
"""
:mod:`brcdapi.utils` - Utility methods

Description::

    Used for:

    * Defining common HTTP status & messages
    * CLI to API conversion for MAPS rules
    * Action tables, see discussion below

    In FOS 8.2.1c, module-version was introduced but as of this writting, still contained scant information about each
    module. The table uri_map is a hard coded table to serve applications and other libraries that need to know how to
    build a full URI and define the behavior of each exposed in the API. The hope is that some day, this information
    will be available through the API allowing uri_map to be built dynamically.

    **WARNING**

    Only GET is valid in the 'methods' leaf of uti_map

Public Methods & Data::

    +-----------------------+---------------------------------------------------------------------------------------+
    | Method                | Description                                                                           |
    +=======================+=======================================================================================+
    | HTTP_xxx              | Several comon status codes and reasons for sythesizing API responses. Typically this  |
    |                       | used for logic that determines an issue whereby the request can't be sent to the      |
    |                       | switch API based on problems found with the input to the method.                      |
    +-----------------------+---------------------------------------------------------------------------------------+
    | mask_ip_addr          | Replaces IP address with xxx.xxx.xxx.123 or all x depending on keep_last              |
    +-----------------------+---------------------------------------------------------------------------------------+
    | vfid_to_str           | Converts a FID to a string, '?vf-id=xx' to be appended to a URI that requires a FID   |
    +-----------------------+---------------------------------------------------------------------------------------+
    | add_uri_map           | Builds out the URI map and adds it to the session. Intended to be called once         |
    |                       | immediately after login                                                               |
    +-----------------------+---------------------------------------------------------------------------------------+
    | split_uri             | Strips out leading '/rest/'. Optionally remover 'running' and 'operations'            |
    +-----------------------+---------------------------------------------------------------------------------------+
    | session_cntl          | Returns the control dictionary (uri map) for the uri                                  |
    +-----------------------+---------------------------------------------------------------------------------------+
    | format_uri            | Formats a full URI                                                                    |
    +-----------------------+---------------------------------------------------------------------------------------+
    | uri_d                 | Returns the dictionary in the URI map for a specified URI                             |
    +-----------------------+---------------------------------------------------------------------------------------+

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.x.x     | 03 Jul 2019   | Experimental                                                                      |
    | 2.x.x     |               |                                                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.0     | 19 Jul 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 29 Jul 2020   | Remove duplicate keys                                                             |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.2     | 13 Feb 2021   | Removed the shebang line                                                          |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.3     | 07 Aug 2021   | Clean up mask_ip_addr()                                                           |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.4     | 31 Dec 2021   | Added new branches and leaves for FOS 9.1                                         |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.5     | 28 Apr 2022   | Added KPIs for 9.1, dynamically build uri map, account for "operations" branch.   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.6     | 22 Jun 2022   | Set FID=True for operations/port                                                  |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.7     | 25 Jul 2022   | Added new branches and leaves for 9.1.0b                                          |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.8     | 04 Sep 2022   | Added new branches and leaves for 9.1.1                                           |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.9     | 24 Oct 2022   | Fixed area for brocade-fabric/access-gateway                                      |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.1.0     | 26 Mar 2023   | Added new branches and leaves for 9.2.x                                           |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.1.1     | 09 May 2023   | Fixed bug in show-status and missed 9.2.x branch                                  |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.1.2     | 21 May 2023   | Documentation updates.                                                            |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020, 2021, 2022, 2023 Jack Consoli'
__date__ = '21 May 2023'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.1.2'

import pprint
import copy
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util

# Common HTTP error codes and reason messages
HTTP_OK = 200
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_REQUEST_TIMEOUT = 408
HTTP_REQUEST_CONFLICT = 409
HTTP_PRECONDITION_REQUIRED = 428
HTTP_INT_SERVER_ERROR = 500
HTTP_INT_SERVER_UNAVAIL = 503
HTTP_REASON_MISSING_OPERAND = 'Missing operand'
HTTP_REASON_MAL_FORMED_CMD = 'Malformed command'
HTTP_REASON_MAL_FORMED_OBJ = 'Malformed object'
HTTP_REASON_NOT_FOUND = 'Referenced resource not found'
HTTP_REASON_MISSING_PARAM = 'Missing parameter'
HTTP_REASON_UNEXPECTED_RESP = 'Unexpected response'
HTTP_REASON_PENDING_UPDATES = 'Unsaved changes'
HTTP_REASON_USER_ABORT = 'User terminated session, ctl-C'

GOOD_STATUS_OBJ = dict(_raw_data=dict(status=HTTP_OK, reason='OK'))
encoding_type = 'utf-8'  # Unless running these scripts on a mainframe, this will always be utf-8.

_VF_ID = '?vf-id='
# sfp_rules.xlsx actions may have been entered using CLI syntax so this table converts the CLI syntax to API syntax.
# Note that only actions with different syntax are converted. Actions not in this table are assumed to be correct API
# syntax.
_cli_to_api_convert = dict(
    fence='port-fence',
    snmp='snmp-trap',
    unquar='un-quarantine',
    decom='decommission',
    toggle='port-toggle',
    email='e-mail',
    uninstall_vtap='vtap-uninstall',
    sw_marginal='sw-marginal',
    sw_critical='sw-critical',
    sfp_marginal='sfp-marginal',
)
# Used in area in default_uri_map
NULL_OBJ = 0  # Actions on this KPI are either not supported or I didn't know what to do with them yet.
SESSION_OBJ = NULL_OBJ + 1
CHASSIS_OBJ = SESSION_OBJ + 1  # URI is associated with a physical chassis
CHASSIS_SWITCH_OBJ = CHASSIS_OBJ + 1   # URI is associated with a physical chassis containing switch objects
SWITCH_OBJ = CHASSIS_SWITCH_OBJ + 1  # URI is associated with a logical switch
SWITCH_PORT_OBJ = SWITCH_OBJ + 1  # URI is associated with a logical switch containing port objects
FABRIC_OBJ = SWITCH_PORT_OBJ + 1  # URI is associated with a fabric
FABRIC_SWITCH_OBJ = FABRIC_OBJ + 1  # URI is associated with a fabric containing switch objects
FABRIC_ZONE_OBJ = FABRIC_SWITCH_OBJ + 1  # URI is associated with a fabric containing zoning objects

op_no = 0  # Used in the op field in session
op_not_supported = 1
op_yes = 2

"""Below is the default URI map. It was built against FOS 9.1. It is necessary because there is not way to retrieve the
FID or area from the FOS API. An # RFE was submitted to get this information. This information is used to build
default_uri_map. Up to the time this was written, all keys (branches) were unique regardless of the URL type. In
FOS 9.1, a new URL type, "operations" was introduced. Although it appears that all keys are still unique, seperate keys
for each type were added because it does not appear that anyone in engineering is thinking they need to be unique.

+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
| Key 0         | Branch    |Key 1      | Type  | Description                                                       |
+===============+===========+===========+=======+===================================================================+
|               |           |           | dict  | URI prefix is just "/rest/"                                       |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
|               |           | area      | int   | Used to indicate what type of object this request is associted    |
|               |           |           |       | with. Search for "Used in area in default_uri_map" above for      |
|               |           |           |       | details.                                                          |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
|               |           | fid       | bool  | If True, this is a fabric level request and the VF ID (?vf-id=xx) |
|               |           |           |       | should be appended to the uri                                     |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
|               |           | methods   | list  | List of supported methods. Currently, only checked for GET.       |
|               |           |           |       | Intended for future use.                                          |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
|               |           | op        | int   | "Options Polled". 0: No, 1: OPTIONS not supported, 2: Yes         |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
| running       |           |           | dict  | URI prefix is "/rest/running/". Sub dictionaries are area, fid,   |
|               |           |           |       | and methods as with "root".                                       |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
| operations    |           |           | dict  | URI prefix is "/rest/operations/". Sub dictionaries are area, fid,|
|               |           |           |       | and methods as with "root".                                       |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
"""
default_uri_map = {
    'auth-token': dict(area=NULL_OBJ, fid=True, methods=('OPTIONS', 'GET')),
    'brocade-module-version': dict(area=NULL_OBJ, fid=False, methods=()),
    'brocade-module-version/module': dict(area=NULL_OBJ, fid=False, methods=('GET', 'HEAD', 'OPTIONS')),
    'login': dict(area=SESSION_OBJ, fid=False, methods=('POST',)),
    'logout': dict(area=SESSION_OBJ, fid=False, methods=('POST',)),
    'running': {
        'brocade-fibrechannel-switch': {
            'fibrechannel-switch': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'switch-fabric-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'topology-domain': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'topology-route': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'topology-error': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-application-server': {
           'application-server-device': dict(area=CHASSIS_OBJ, id=False, methods=('GET', 'HEAD', 'OPTIONS')),
        },
        'brocade-fibrechannel-logical-switch': {
            'fibrechannel-logical-switch': dict(area=CHASSIS_SWITCH_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-interface': {
            'fibrechannel': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fibrechannel-statistics': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fibrechannel-performance': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fibrechannel-statistics-db': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'extension-ip-interface': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('GET', 'DELETE')),
            'fibrechannel-lag': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'gigabitethernet': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'gigabitethernet-statistics': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'logical-e-port': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'portchannel': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'portchannel-statistics': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fibrechannel-router-statistics': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-media': {
            'media-rdp': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fabric': {
            'access-gateway': dict(area=FABRIC_SWITCH_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'fabric-switch': dict(area=FABRIC_SWITCH_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-fibrechannel-routing': {
            'routing-configuration': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lsan-zone': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lsan-device': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'edge-fabric-alias': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fibrechannel-router': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'router-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'proxy-config': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'translate-domain-config': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'stale-translate-domain': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
         },
        'brocade-zone': {
            'defined-configuration': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'effective-configuration': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fabric-lock': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fibrechannel-diagnostics': {
            'fibrechannel-diagnostics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fdmi': {
            'hba': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'port': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-name-server': {
            'fibrechannel-name-server': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fabric-traffic-controller': {
            'fabric-traffic-controller-device': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fibrechannel-configuration': {
            'switch-configuration': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'f-port-login-settings': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'port-configuration': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'zone-configuration': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fabric': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'chassis-config-settings': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fos-settings': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-logging': {
            'audit': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'syslog-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'log-setting': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'log-quiet-control': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'raslog': dict(area=CHASSIS_OBJ, fid=False,  methods=('OPTIONS', 'GET')),
            'raslog-module': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'supportftp': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'error-log': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'audit-log': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-session-login-information': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-fibrechannel-trunk': {
            'trunk': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'performance': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'trunk-area': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-ficon': {
            'cup': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'logical-path': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'rnid': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'switch-rnid': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lirr': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'rlir': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fru': {
            'power-supply': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'fan': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'blade': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'history-log': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sensor': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'wwn': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-chassis': {
            'chassis': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ha-status': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'credit-recovery': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-interface-configuration': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-ethernet-interface': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-port-track-configuration':  dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-port-connection-statistics': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sn-chassis': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'version': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-maps': {
            'maps-config': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'rule': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'maps-policy': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'group': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'dashboard-rule': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'dashboard-history': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'dashboard-misc': dict(area=SWITCH_OBJ, fid=True, methods=('GET', 'PUT')),
            'credit-stall-dashboard': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'oversubscription-dashboard': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'system-resources': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'paused-cfg': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'monitoring-system-matrix': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'switch-status-policy-report': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fpi-profile': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'maps-violation': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'backend-ports-history': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'gigabit-ethernet-ports-history': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'maps-device-login': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'maps-violation': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'quarantined-devices': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-time': {
            'clock-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'time-zone': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ntp-clock-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ntp-clock-server-key': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-security': {
            'sec-crypto-cfg': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sec-crypto-cfg-template': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sec-crypto-cfg-template-action': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS',)),
            'password-cfg': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'user-specific-password-cfg': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'user-config': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ldap-role-map': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sshutil': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sshutil-key': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sshutil-known-host': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sshutil-public-key': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sshutil-public-key-action': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS',)),
            'password': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS',)),
            'security-certificate-generate': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS',)),
            'security-certificate-action': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'DELETE')),
            'security-certificate': dict(area=CHASSIS_OBJ, fid=False,  methods=('OPTIONS', 'GET')),
            'radius-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'tacacs-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ldap-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'auth-spec': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ipfilter-policy': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ipfilter-rule': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'security-certificate-extension': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'role-config': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'rbac-class': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-rbac-map': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'security-violation-statistics': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'acl-policy': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'defined-fcs-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'active-fcs-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'defined-scc-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'active-scc-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'defined-dcc-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'active-dcc-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'security-policy-size': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'authentication-configuration': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'dh-chap-authentication-secret': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'policy-distribution-config': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-license': {
            'license': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ports-on-demand-license-info': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'end-user-license-agreement': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-snmp': {
            'system': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'mib-capability': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'trap-capability': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'v1-account': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'v1-trap': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'v3-account': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'v3-trap': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'access-control': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-management-ip-interface': {
            'management-ip-interface': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-interface-lldp-neighbor': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-interface-lldp-statistics': dict(area=CHASSIS_OBJ, fid=False,  methods=('OPTIONS', 'GET')),
        },
        'brocade-firmware': {
            'firmware-history': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'firmware-config': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-dynamic-feature-tracking': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        'brocade-usb': {
            'usb-file': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-extension-ip-route': {
            'extension-ip-route': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-extension-ipsec-policy': {
            'extension-ipsec-policy': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-extension-tunnel': {  # I think some of these should be SWITCH_PORT_OBJ
            'extension-tunnel': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'extension-tunnel-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'extension-circuit': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'extension-circuit-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'circuit-qos-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'circuit-interval-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'wan-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'wan-statistics-v1': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-extension': {
            'traffic-control-list': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'dp-hcl-status': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'global-lan-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lan-flow-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-lldp': {
            'lldp-neighbor': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lldp-profile': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lldp-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lldp-global': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-supportlink': {
            'supportlink-profile': dict(area=CHASSIS_OBJ, fid=False, methods=('GET', 'PATCH', 'HEAD', 'OPTIONS')),
            'supportlink-history': dict(area=CHASSIS_OBJ, fid=False, methods=('GET', 'PATCH', 'HEAD', 'OPTIONS')),
        },
        'brocade-traffic-optimizer': {
            'performance-group-profile': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'performance-group-flows': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'performance-group': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
    },
    'operations': {
        'brocade-diagnostics': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'configdownload': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'configupload': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'date': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'extension': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'factory-reset': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'fibrechannel-fabric': dict(area=NULL_OBJ, fid=True,  methods=('POST', 'OPTIONS')),
        'fibrechannel-zone': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'firmwaredownload': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'lldp': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'management-ethernet-interface': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'ntp-clock-server': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'port': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'port-decommission': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'reboot': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'restart': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'sdd-quarantine': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'security-acl-policy': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'security-ipfilter': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'security-reset-violation-statistics': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'security-policy-distribute': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'security-policy-chassis-distribute': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'security-fabric-wide-policy-distribute': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'security-authentication-secret': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'security-authentication-configuration': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'security-role-clone': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'security-certificate': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'show-status': {'area': NULL_OBJ, 'fid': False, 'methods': ('POST',),
                        'message-id': dict(area=NULL_OBJ, fid=False, methods=('POST',))},
        'supportsave': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'traffic-optimizer': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'device-management': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'license': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'pcie-health': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'pcie-health-test': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'fabric': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'supportlink': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'usb-delete-file': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'portchannel': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'device-login-rebalance': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
    },
}


def mask_ip_addr(addr, keep_last=True):
    """Replaces IP address with xxx.xxx.xxx.123 or all x depending on keep_last

    :param addr: IP address
    :type addr: str
    :param keep_last: If true, preserves the last octet. If false, replace all octets with xxx
    :type keep_last: bool
    :return: Masked IP
    :rtype: str
    """
    tip = ''
    if isinstance(addr, str):
        tl = addr.split('.')
        for i in range(0, len(tl) - 1):
            tip += 'xxx.'
        tip += tl[len(tl) - 1] if keep_last else 'xxx'
    return tip


def vfid_to_str(vfid):
    """Converts a FID to a string, '?vf-id=xx' to be appended to a URI that requires a FID

    :param vfid: FOS session object
    :type vfid: int
    :return: '?vf-id=x' where x is the vfid converted to a str. If vfid is None then just '' is returned
    :rtype: str
    """
    return '' if vfid is None else _VF_ID + str(vfid)


def add_uri_map(session, rest_d):
    """Builds out the URI map and adds it to the session. Intended to be called once immediately after login

    :param session: Session dictionary returned from brcdapi.brcdapi_rest.login()
    :type session: dict
    :param rest_d: Object returned from FOS for 'brocade-module-version'
    :type rest_d: dict
    """
    global default_uri_map

    ml = list()
    try:
        mod_l = rest_d['brocade-module-version']['module']
    except KeyError:
        brcdapi_log.exception('ERROR: Invalid data in rest_d parameter.', echo=True)
        return

    # Add each item to the session uri_map
    uri_map_d = dict()
    session.update(uri_map=uri_map_d)
    for mod_d in mod_l:
        to_process_l = list()

        # Create a list of individual modules that need to be parsed
        try:
            uri = mod_d['uri']
            # The running leaves all have individual requests while all else are 1:1 requests.
            if '/rest/running/' in uri:
                add_l = mod_d['objects'].get('object')
                if isinstance(add_l, list):
                    base_l = uri.split('/')[2:]
                    for buf_l in [[buf] for buf in add_l]:
                        to_process_l.append(base_l + buf_l)
            else:
                to_process_l.append(uri.split('/')[2:])
        except (IndexError, KeyError):
            brcdapi_log.exception(['', 'ERROR: Unexpected value in: ' + pprint.pformat(mod_d), ''], echo=True)
            continue

        # Parse each module
        for uri_l in to_process_l:

            # Find the dictionary in the default URI map
            default_d, last_d = default_uri_map, uri_map_d
            for k in uri_l:
                if default_d is not None:
                    default_d = default_d.get(k)
                d = last_d.get(k)
                if d is None:
                    d = dict()
                    last_d.update({k: d})
                last_d = d

            # Add this module (API request) to the URI map, uri_map, in the session object.
            if isinstance(d, dict):
                new_mod_d = copy.deepcopy(mod_d)
                new_uri = uri + '/' + k if '/rest/running/' in uri else uri
                if isinstance(default_d, dict):
                    new_mod_d.update(area=default_d.get('area'),
                                     fid=default_d.get('fid'),
                                     methods=gen_util.convert_to_list(default_d.get('methods')),
                                     op=op_no)
                    new_mod_d['uri'] = new_uri
                    last_d.update(new_mod_d)
                else:
                    ml.append('UNKNOWN URI: ' + new_uri)
            else:
                brcdapi_log.exception(['', 'ERROR: Unexpected value in: ' + pprint.pformat(mod_d), ''], echo=True)

    if len(ml) > 0:
        brcdapi_log.log(ml, echo=True)

    return


def split_uri(uri, run_op_out=False):
    """From a URI: Removes '/rest/'. Optionally removes 'running' and 'operations'. Returns a list of elements

    :param uri: URI
    :type uri: str
    :param run_op_out: If True, also remove 'running' and 'operations'
    :type run_op_out: bool
    :return: URI split into a list with leading '/rest/' stipped out
    :rtype: list
    """
    l = uri.split('/')
    if len(l) > 0 and l[0] == '':
        l.pop(0)
    if len(l) > 0 and l[0] == 'rest':
        l.pop(0)
    if run_op_out and len(l) > 0 and l[0] in ('running', 'operations'):
        l.pop(0)

    return l


def session_cntl(session, in_uri):
    """Returns the control dictionary (uri map) for the uri

    :param session: Dictionary of the session returned by login.
    :type session: dict
    :param in_uri: URI
    :type in_uri: str
    :return: Control dicstionary associated with uri. None if not found
    :rtype: dict, None
    """
    if 'operations/show-status/message-id/' in in_uri:
        return None

    uri = '/'.join(split_uri(in_uri))
    d = gen_util.get_key_val(session.get('uri_map'), uri)
    if d is None:
        d = gen_util.get_key_val(session.get('uri_map'), 'running/' + uri)  # The old way didn't include 'running/'

    return d


def format_uri(session, uri, fid):
    """Formats a full URI.

    :param session: Session object returned from login()
    :type session: dict
    :param uri: Rest URI. Must not include IP address or '/rest/'
    :type uri: str
    :param fid: Fabric ID
    :type fid: int, None
    :return: Full URI
    :rtype: str
    """
    d = session_cntl(session, uri)

    return '/rest/' + uri if d is None else d['uri'] if d['fid'] is None else d['uri'] + vfid_to_str(fid)


def uri_d(session, uri):
    """Returns the dictionary in the URI map for a specified URI

    :param session: Session object returned from login()
    :type session: dict
    :param uri: URI in slash notation
    :type uri: str
    """
    d = gen_util.get_struct_from_obj(session.get('uri_map'), uri)
    if not isinstance(d, dict) and gen_util.get_key_val(default_uri_map, uri) is None:
        brcdapi_log.log('UNKNOWN URI: ' + uri)
    return d


def _get_uri(map_d):
    rl = list()
    if isinstance(map_d, dict):
        for d in map_d.values():
            if isinstance(d, dict):
                uri = d.get('uri')
                if uri is not None:
                    rl.append('/'.join(split_uri(uri)))
                    continue
                else:
                    rl.extend(_get_uri(d))

    return rl


def uris_for_method(session, http_method, uri_d_flag=False):
    """Returns the dictionaries or URIs supporting a certain HTTP method.

    :param session: Session object returned from login()
    :type session: dict
    :param http_method: The HTTP method to look for
    :type http_method: str, None
    :param uri_d_flag: If True, return a list of the URI dictionaries. If False, just return a list of the URIs
    :type uri_d_flag: bool
    :return: List of URIs or URI dictionaries depending on uri_d_flag
    :rtype: list
    """
    rl, uri_map_d = list(), session.get('uri_map')
    if not isinstance(uri_map_d, dict):
        return rl  # Just in case someone calls this method before logging in.

    for uri in _get_uri(uri_map_d.get('running')) + _get_uri(uri_map_d.get('operations')):
        d = uri_d(session, uri)
        if http_method in gen_util.convert_to_list(d.get('methods')):
            if uri_d_flag:
                rl.append(d)
            else:
                rl.append(uri)

    return rl


def _int_dict_to_uri(convert_dict):
    """Converts a dictionary to a list of '/' separated strings. Assumes the first non-dict is the end

    :param convert_dict: Dictionary to convert
    :type convert_dict: None, str, list, tuple, int, float, dict
    :return: List of str
    :rtype: list
    """
    rl = list()
    if isinstance(convert_dict, dict):
        for k, v in convert_dict.items():
            if isinstance(v, dict):
                for l in dict_to_uri(v):
                    rl.append(str(k) + '/' + '/'.join(l))
            else:
                rl.append('/' + str(k))

    return rl


def dict_to_uri(convert_dict):
    """Converts a dictionary to a list of '/' separated strings. Assumes the first non-dict is the end

    :param convert_dict: Dictionary to convert
    :type convert_dict: None, str, list, tuple, int, float, dict
    :return: List of str
    :rtype: list
    """
    rl = list()
    if isinstance(convert_dict, dict):
        for k, v in convert_dict.items():
            if isinstance(v, dict):
                for buf in dict_to_uri(v):
                    rl.append(str(k) + '/' + buf)
            else:
                rl.append(str(k))

    return rl

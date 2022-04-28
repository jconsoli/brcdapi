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
    | format_uri            | Formats a full URI for a KPI.                                                         |
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
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020, 2021, 2022 Jack Consoli'
__date__ = '28 Apr 2022'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.5'

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
HTTP_REASON_MISSING_OPERAND = 'Missing operand'
HTTP_REASON_MAL_FORMED_CMD = 'Malformed command'
HTTP_REASON_MAL_FORMED_OBJ = 'Malformed object'
HTTP_REASON_NOT_FOUND = 'Referenced resource not found'
HTTP_REASON_MISSING_PARAM = 'Missing parameter'
HTTP_REASON_UNEXPECTED_RESP = 'Unexpected response'
HTTP_REASON_PENDING_UPDATES = 'Unsaved changes'

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
    'auth-token': {
        'area': NULL_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-module-version': {
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),
    },
    'brocade-module-version/module': {
        'area': NULL_OBJ,
        'fid': False,
        'methods': ('GET', 'HEAD', 'OPTIONS'),
    },
    'login': {
        'area': SESSION_OBJ,
        'fid': False,
        'methods': ('POST',),
    },
    'logout': {
        'area': SESSION_OBJ,
        'fid': False,
        'methods': ('POST',),
    },
    'running': {
        'brocade-fibrechannel-switch': {
            'fibrechannel-switch': {
                    'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'topology-domain': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'topology-route': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'topology-error': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-application-server': {
           'application-server-device': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET', 'HEAD', 'OPTIONS'),
            },
        },
        'brocade-fibrechannel-logical-switch': {
            'fibrechannel-logical-switch': {
                'area': CHASSIS_SWITCH_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-interface': {
            'fibrechannel': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'fibrechannel-statistics': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'fibrechannel-performance': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'fibrechannel-statistics-db': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'extension-ip-interface': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET', 'DELETE'),
            },
            'fibrechannel-lag': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'gigabitethernet': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'gigabitethernet-statistics': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'logical-e-port': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'portchannel': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'fibrechannel-router-statistics': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-media': {
            'media-rdp': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-fabric': {
            'access-gateway': {
                'area': FABRIC_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'fabric-switch': {
                'area': FABRIC_SWITCH_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-fibrechannel-routing': {
            'routing-configuration': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'lsan-zone': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'lsan-device': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'edge-fabric-alias': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'fibrechannel-router': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'router-statistics': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'proxy-config': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'translate-domain-config': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'stale-translate-domain': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-zone': {
            'defined-configuration': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'effective-configuration': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'fabric-lock': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-fibrechannel-diagnostics': {
            'fibrechannel-diagnostics': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-fdmi': {
            'hba': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'port': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-name-server': {
            'fibrechannel-name-server': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-fabric-traffic-controller': {
            'fabric-traffic-controller-device': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-fibrechannel-configuration': {
            'switch-configuration': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'f-port-login-settings': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'port-configuration': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'zone-configuration': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'fabric': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'chassis-config-settings': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'fos-settings': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-logging': {
            'audit': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'syslog-server': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'log-setting': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'log-quiet-control': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'raslog': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'raslog-module': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'supportftp': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'error-log': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'audit-log': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'management-session-login-information': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-fibrechannel-trunk': {
            'trunk': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'performance': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'trunk-area': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-ficon': {
            'cup': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'logical-path': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'rnid': {
                'area': SWITCH_PORT_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'switch-rnid': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'lirr': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'rlir': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-fru': {
            'power-supply': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'fan': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'blade': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'history-log': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'sensor': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'wwn': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-chassis': {
            'chassis': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'ha-status': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'credit-recovery': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'management-interface-configuration': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'management-ethernet-interface': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'management-port-track-configuration': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'management-port-connection-statistics': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'sn-chassis': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-maps': {
            'maps-config': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'rule': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'maps-policy': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'group': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'dashboard-rule': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'dashboard-history': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'dashboard-misc': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET', 'PUT'),
            },
            'credit-stall-dashboard': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'oversubscription-dashboard': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'system-resources': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'paused-cfg': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'monitoring-system-matrix': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'switch-status-policy-report': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'fpi-profile': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'maps-violation': {
                'area': SWITCH_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-time': {
            'clock-server': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'time-zone': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'ntp-clock-server': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'ntp-clock-server-key': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-security': {
            'sec-crypto-cfg': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'sec-crypto-cfg-template': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'sec-crypto-cfg-template-action': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'password-cfg': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'user-specific-password-cfg': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'user-config': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'ldap-role-map': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'sshutil': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'sshutil-key': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'sshutil-known-host': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'sshutil-public-key': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'sshutil-public-key-action': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'password': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'security-certificate-generate': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'security-certificate-action': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET', 'DELETE'),
            },
            'security-certificate': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'radius-server': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'tacacs-server': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'ldap-server': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'auth-spec': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'ipfilter-policy': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'ipfilter-rule': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'security-certificate-extension': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'role-config': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'rbac-class': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'management-rbac-map': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'security-violation-statistics': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'acl-policy': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'defined-fcs-policy-member-list': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'active-fcs-policy-member-list': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'defined-scc-policy-member-list': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'active-scc-policy-member-list': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'defined-dcc-policy-member-list': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'active-dcc-policy-member-list': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'security-policy-size': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'authentication-configuration': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'dh-chap-authentication-secret': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'policy-distribution-config': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-license': {
            'license': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'ports-on-demand-license-info': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'end-user-license-agreement': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-snmp': {
            'system': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'mib-capability': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'trap-capability': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'v1-account': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'v1-trap': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'v3-account': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'v3-trap': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'access-control': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-management-ip-interface': {
            'management-ip-interface': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'management-interface-lldp-neighbor': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'management-interface-lldp-statistics': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-firmware': {
            'firmware-history': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
            'firmware-config': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-dynamic-feature-tracking': {
            'area': CHASSIS_OBJ,
            'fid': False,
            'methods': ('GET',),
        },
        'brocade-usb': {
            'usb-file': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET',),
            },
        },
        'brocade-extension-ip-route': {
            'extension-ip-route': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-extension-ipsec-policy': {
            'extension-ipsec-policy': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-extension-tunnel': {
            'extension-tunnel': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'extension-tunnel-statistics': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'extension-circuit': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'extension-circuit-statistics': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'circuit-qos-statistics': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'wan-statistics': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-extension': {
            'traffic-control-list': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'dp-hcl-status': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'global-lan-statistics': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'lan-flow-statistics': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-lldp': {
            'lldp-neighbor': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'lldp-profile': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'lldp-statistics': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'lldp-global': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
        'brocade-supportlink': {
            'supportlink-profile': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET', 'PATCH', 'HEAD', 'OPTIONS'),
            },
            'supportlink-history': {
                'area': CHASSIS_OBJ,
                'fid': False,
                'methods': ('GET', 'PATCH', 'HEAD', 'OPTIONS'),
            },
        },
        'brocade-traffic-optimizer': {
            'performance-group-profile': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'performance-group-flows': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
            'performance-group': {
                'area': FABRIC_OBJ,
                'fid': True,
                'methods': ('GET',),
            },
        },
    },
    'operations': {
        'configdownload': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'configupload': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'date': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'extension': {
            'area': NULL_OBJ,
            'fid': True,
            'methods': ('POST', 'OPTIONS'),
        },
        'factory-reset': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'fibrechannel-fabric': {
            'area': NULL_OBJ,
            'fid': True,
            'methods': ('POST', 'OPTIONS'),
        },
        'fibrechannel-zone': {
            'area': NULL_OBJ,
            'fid': True,
            'methods': ('POST', 'OPTIONS'),
        },
        'firmwaredownload': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'lldp': {
            'area': NULL_OBJ,
            'fid': True,
            'methods': ('POST', 'OPTIONS'),
        },
        'management-ethernet-interface': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'ntp-clock-server': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'port': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'port-decommission': {
            'area': NULL_OBJ,
            'fid': True,
            'methods': ('POST', 'OPTIONS'),
        },
        'reboot': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'security-acl-policy': {
            'area': NULL_OBJ,
            'fid': True,
            'methods': ('POST', 'OPTIONS'),
        },
        'security-reset-violation-statistics': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'security-policy-distribute': {
            'area': NULL_OBJ,
            'fid': True,
            'methods': ('POST', 'OPTIONS'),
        },
        'security-policy-chassis-distribute': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'security-fabric-wide-policy-distribute': {
            'area': NULL_OBJ,
            'fid': True,
            'methods': ('POST', 'OPTIONS'),
        },
        'security-authentication-secret': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'security-authentication-configuration': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'security-role-clone': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'security-certificate': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'show-status': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST',),
        },
        'supportsave': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'traffic-optimizer': {
            'area': NULL_OBJ,
            'fid': True,
            'methods': ('POST', 'OPTIONS'),
        },
        'device-management': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'license': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'pcie-health': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'pcie-health-test': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'fabric': {
            'area': NULL_OBJ,
            'fid': True,
            'methods': ('POST', 'OPTIONS'),
        },
        'supportlink': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
        'usb-delete-file': {
            'area': NULL_OBJ,
            'fid': False,
            'methods': ('POST', 'OPTIONS'),
        },
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
        brcdapi_log.exception('ERROR: Invalid data in rest_d parameter.', True)
        return

    # Add each item to the session uri_map
    uri_map_d = dict()
    session.update(uri_map=uri_map_d)
    for mod_d in mod_l:
        to_process_l = list()

        # Create a list of individual moduels that need to be parsed
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
            brcdapi_log.exception(['', 'ERROR: Unexpected value in: ' + pprint.pformat(mod_d), ''], True)
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
                                     methods=list(default_d.get('methods')),
                                     op=op_no)
                    new_mod_d['uri'] = new_uri
                    last_d.update(new_mod_d)
                else:
                    ml.append('UNKNOWN URI: ' + new_uri)
            else:
                brcdapi_log.exception(['', 'ERROR: Unexpected value in: ' + pprint.pformat(mod_d), ''], True)

    if len(ml) > 0:
        brcdapi_log.log(ml, True)

    return


def split_uri(uri, run_op_out=False):
    """From a URI: Removes '/rest/'. Optionally removes 'running' and 'operations'. Returns a list of elements

    :param uri: URI
    :type uri: str
    :param run_op_out: If True, also remove 'running' and 'operations'
    :type run_op_out: bool
    :return: URI with leading '/rest/' stipped out
    :rtype: str
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
    uri = '/'.join(split_uri(in_uri))
    d = gen_util.get_key_val(session.get('uri_map'), uri)
    if d is None:
        d = gen_util.get_key_val(session.get('uri_map'), 'running/' + uri)  # The old way didn't include 'running/'

    return d


def format_uri(session, uri, fid):
    """Formats a full URI for a KPI.

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

    return '/rest/'+uri if d is None else d['uri'] if d['fid'] is None else d['uri'] + vfid_to_str(fid)


def uri_d(session, uri):
    """Returns the dictionary in the URI map for a specified URI

    :param session: Session object returned from login()
    :type session: dict
    :param uri: URI in slash notation
    :type uri: str
    """
    return gen_util.get_struct_from_obj(session.get('uri_map'), uri)


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
    :type uri_d_flag: str
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

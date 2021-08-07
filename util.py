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
    will be available through the API allowing uri_map to be built dynmaically.

    **WARNING**

    Only GET is valid in the 'methods' leaf of uti_map

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
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020, 2021 Jack Consoli'
__date__ = '07 Aug 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.3'

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

# sfp_rules.xlsx actions may have been entered using CLI syntax so this table converts the CLI syntax to API syntax.
# Note that only actions with different syntax are converted. Actions not in this table are assumed to be correct API
# syntax.
_cli_to_api_convert = dict(
    fence='port-fence',
    snmp='snmp-trap',
    unquar='un-quarantine',
    decom='decomission',
    toggle='port-toggle',
    email='e-mail',
    uninstall_vtap='vtap-uninstall',
    sw_marginal='sw-marginal',
    sw_critical='sw-critical',
    sfp_marginal='sfp-marginal',
)
# Used in area in uri_map
NULL_OBJ = 0  # Actions on this KPI are either not supported or I didn't know what to do with them yet.
SESSION_OBJ = NULL_OBJ + 1
CHASSIS_OBJ = SESSION_OBJ + 1  # URI is associated with a physical chassis
CHASSIS_SWITCH_OBJ = CHASSIS_OBJ + 1   # URI is associated with a physical chassis containing switch objects
SWITCH_OBJ = CHASSIS_SWITCH_OBJ + 1  # URI is associated with a logical switch
SWITCH_PORT_OBJ = SWITCH_OBJ + 1  # URI is associated with a logical switch containing port objects
FABRIC_OBJ = SWITCH_PORT_OBJ + 1  # URI is associated with a fabric
FABRIC_SWITCH_OBJ = FABRIC_OBJ + 1  # URI is associated with a fabric containing switch objects
FABRIC_ZONE_OBJ = FABRIC_SWITCH_OBJ + 1  # URI is associated with a fabric containing zoning objects

# Below is the default URI map it was built against a beta build of FOS 9.0. An # RFE was submitted to get additional
# (fid & uri) information back from brocade-module-version so that this can be modified dynamically. Note that the only
# time I ever make a request with a KPI deeper than the first level is when performing some specific function that does
# not require automation. The tables are used for automating the processing of requests. For example, I automate GET
# requests on 'brocade-interface/fibrechannel' but not 'brocade-interface/fibrechannel/name'.
# Leaves are as follows
# key   The KPI
#   uri         The full URI less the IP address for the request
#   area        An integer indicating what type of URI this is. Search for "Used in area in uri_map" above
#   fid         True - the VF ID (?vf-id=xx) should be appended to the uri
#               False - do not append the VF ID (chassis level request) to the uri
#   methods     List of supported methods. Currently, only checked for GET methods. Intended for future use.
uri_map = {
    'login': {
        'uri': '/rest/login',
        'area': SESSION_OBJ,
        'fid': False,
        'methods': ('POST',),
    },
    'logout': {
        'uri': '/rest/logout',
        'area': SESSION_OBJ,
        'fid': False,
        'methods': ('POST',),
    },
    'brocade-module-version': {
        'uri': '/rest/brocade-module-version',
        'area': NULL_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-module-version/module': {
        'uri': '/rest/brocade-module-version/module',
        'area': NULL_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'auth-token': {
        'uri': '/rest/auth-token',
        'area': NULL_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-switch': {
        'uri': '/rest/running/brocade-fibrechannel-switch',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-fibrechannel-switch/fibrechannel-switch': {
        'uri': '/rest/running/brocade-fibrechannel-switch/fibrechannel-switch',
        'area': CHASSIS_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-switch/topology-domain': {
        'uri': '/rest/running/brocade-fibrechannel-switch/topology-domain',
        'area': CHASSIS_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-switch/topology-route': {
        'uri': '/rest/running/brocade-fibrechannel-switch/topology-route',
        'area': CHASSIS_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-logical-switch': {
        'uri': '/rest/running/brocade-fibrechannel-logical-switch',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch': {
        'uri': '/rest/running/brocade-fibrechannel-logical-switch/fibrechannel-logical-switch',
        'area': CHASSIS_SWITCH_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-interface': {
        'uri': '/rest/running/brocade-interface',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-interface/fibrechannel': {
        'uri': '/rest/running/brocade-interface/fibrechannel',
        'area': SWITCH_PORT_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-interface/fibrechannel-statistics': {
        'uri': '/rest/running/brocade-interface/fibrechannel-statistics',
        'area': SWITCH_PORT_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-interface/fibrechannel-performance': {
        'uri': '/rest/running/brocade-interface/fibrechannel-performance',
        'area': SWITCH_PORT_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-interface/fibrechannel-statistics-db': {
        'uri': '/rest/running/brocade-interface/fibrechannel-statistics-db',
        'area': SWITCH_PORT_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-interface/extension-ip-interface': {
        'uri': '/rest/running/brocade-interface/extension-ip-interface',
        'area': SWITCH_PORT_OBJ,
        'fid': True,
        'methods': ('GET', 'DELETE'),
    },
    'brocade-interface/gigabitethernet': {
        'uri': '/rest/running/brocade-interface/gigabitethernet',
        'area': SWITCH_PORT_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-interface/gigabitethernet-statistics': {
        'uri': '/rest/running/brocade-interface/gigabitethernet-statistics',
        'area': SWITCH_PORT_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-interface/logical-e-port': {
        'uri': '/rest/running/brocade-interface/logical-e-port',
        'area': SWITCH_PORT_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-interface/portchannel': {
        'uri': '/rest/running/brocade-interface/portchannel',
        'area': SWITCH_PORT_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-media': {
        'uri': '/rest/running/brocade-media',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-media/media-rdp': {
        'uri': '/rest/running/brocade-media/media-rdp',
        'area': SWITCH_PORT_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fabric': {
        'uri': '/rest/running/brocade-fabric',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-fabric/access-gateway': {
        'uri': '/rest/running/brocade-fabric/access-gateway',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fabric/fabric-switch': {
        'uri': '/rest/running/brocade-fabric/fabric-switch',
        'area': FABRIC_SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-routing': {
        'uri': '/rest/running/brocade-fibrechannel-routing',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-fibrechannel-routing/routing-configuration': {
        'uri': '/rest/running/brocade-fibrechannel-routing/routing-configuration',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-routing/lsan-zone': {
        'uri': '/rest/running/brocade-fibrechannel-routing/lsan-zone',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-routing/lsan-device': {
        'uri': '/rest/running/brocade-fibrechannel-routing/lsan-device',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-routing/edge-fabric-alias': {
        'uri': '/rest/running/brocade-fibrechannel-routing/edge-fabric-alias',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-zone': {
        'uri': '/rest/running/brocade-zone',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-zone/defined-configuration': {
        'uri': '/rest/running/brocade-zone/defined-configuration',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-zone/effective-configuration': {
        'uri': '/rest/running/brocade-zone/effective-configuration',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-zone/fabric-lock': {
        'uri': '/rest/running/brocade-zone/fabric-lock',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-diagnostics': {
        'uri': '/rest/running/brocade-fibrechannel-diagnostics',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-fibrechannel-diagnostics/fibrechannel-diagnostics': {
        'uri': '/rest/running/brocade-fibrechannel-diagnostics/fibrechannel-diagnostics',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fdmi': {
        'uri': '/rest/running/brocade-fdmi',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-fdmi/hba': {
        'uri': '/rest/running/brocade-fdmi/hba',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fdmi/port': {
        'uri': '/rest/running/brocade-fdmi/port',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-name-server': {
        'uri': '/rest/running/brocade-name-server',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-name-server/fibrechannel-name-server': {
        'uri': '/rest/running/brocade-name-server/fibrechannel-name-server',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fabric-traffic-controller': {
        'uri': '/rest/running/brocade-fabric-traffic-controller',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-fabric-traffic-controller/fabric-traffic-controller-device': {
        'uri': '/rest/running/brocade-fabric-traffic-controller/fabric-traffic-controller-device',
        'area': NULL_OBJ,  # FABRIC_OBJ
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-configuration': {
        'uri': '/rest/running/brocade-fibrechannel-configuration',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-fibrechannel-configuration/switch-configuration': {
        'uri': '/rest/running/brocade-fibrechannel-configuration/switch-configuration',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-configuration/f-port-login-settings': {
        'uri': '/rest/running/brocade-fibrechannel-configuration/f-port-login-settings',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-configuration/port-configuration': {
        'uri': '/rest/running/brocade-fibrechannel-configuration/port-configuration',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-configuration/zone-configuration': {
        'uri': '/rest/running/brocade-fibrechannel-configuration/zone-configuration',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-configuration/fabric': {
        'uri': '/rest/running/brocade-fibrechannel-configuration/fabric',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-configuration/chassis-config-settings': {
        'uri': '/rest/running/brocade-fibrechannel-configuration/chassis-config-settings',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-configuration/fos-settings': {
        'uri': '/rest/running/brocade-fibrechannel-configuration/fos-settings',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-logging': {
        'uri': '/rest/running/brocade-logging',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-logging/audit': {
        'uri': '/rest/running/brocade-logging/audit',
        'area': CHASSIS_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-logging/syslog-server': {
        'uri': '/rest/running/brocade-logging/syslog-server',
        'area': CHASSIS_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-logging/log-setting': {
        'uri': '/rest/running/brocade-logging/log-setting',
        'area': CHASSIS_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-logging/log-quiet-control': {
        'uri': '/rest/running/brocade-logging/log-quiet-control',
        'area': CHASSIS_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-logging/raslog': {
        'uri': '/rest/running/brocade-logging/raslog',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-logging/raslog-module': {
        'uri': '/rest/running/brocade-logging/raslog-module',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-logging/supportftp': {
        'uri': '/rest/running/brocade-logging/supportftp',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-logging/error-log': {
        'uri': '/rest/running/brocade-logging/error-log',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-logging/audit-log': {
        'uri': '/rest/running/brocade-logging/audit-log',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-trunk': {
        'uri': '/rest/running/brocade-fibrechannel-trunk',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-fibrechannel-trunk/trunk': {
        'uri': '/rest/running/brocade-fibrechannel-trunk/trunk',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-trunk/performance': {
        'uri': '/rest/running/brocade-fibrechannel-trunk/performance',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fibrechannel-trunk/trunk-area': {
        'uri': '/rest/running/brocade-fibrechannel-trunk/trunk-area',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-ficon': {
        'uri': '/rest/running/brocade-ficon',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-ficon/cup': {
        'uri': '/rest/running/brocade-ficon/cup',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-ficon/logical-path': {
        'uri': '/rest/running/brocade-ficon/logical-path',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-ficon/rnid': {
        'uri': '/rest/running/brocade-ficon/rnid',
        'area': SWITCH_PORT_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-ficon/switch-rnid': {
        'uri': '/rest/running/brocade-ficon/switch-rnid',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-ficon/lirr': {
        'uri': '/rest/running/brocade-ficon/lirr',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-ficon/rlir': {
        'uri': '/rest/running/brocade-ficon/rlir',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-fru': {
        'uri': '/rest/running/brocade-fru',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-fru/power-supply': {
        'uri': '/rest/running/brocade-fru/power-supply',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-fru/fan': {
        'uri': '/rest/running/brocade-fru/fan',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-fru/blade': {
        'uri': '/rest/running/brocade-fru/blade',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-fru/history-log': {
        'uri': '/rest/running/brocade-fru/history-log',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-fru/sensor': {
        'uri': '/rest/running/brocade-fru/sensor',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-fru/wwn': {
        'uri': '/rest/running/brocade-fru/wwn',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-chassis': {
        'uri': '/rest/running/brocade-chassis',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-chassis/chassis': {
        'uri': '/rest/running/brocade-chassis/chassis',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-chassis/ha-status': {
        'uri': '/rest/running/brocade-chassis/ha-status',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-maps': {
        'uri': '/rest/running/brocade-maps',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-maps/maps-config': {
        'uri': '/rest/running/brocade-maps/maps-config',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/rule': {
        'uri': '/rest/running/brocade-maps/rule',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/maps-policy': {
        'uri': '/rest/running/brocade-maps/maps-policy',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/group': {
        'uri': '/rest/running/brocade-maps/group',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/dashboard-rule': {
        'uri': '/rest/running/brocade-maps/dashboard-rule',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/dashboard-history': {
        'uri': '/rest/running/brocade-maps/dashboard-history',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/dashboard-misc': {
        'uri': '/rest/running/brocade-maps/dashboard-misc',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET', 'PUT'),
    },
    'brocade-maps/credit-stall-dashboard': {
        'uri': '/rest/running/brocade-maps/credit-stall-dashboard',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/oversubscription-dashboard': {
        'uri': '/rest/running/brocade-maps/oversubscription-dashboard',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/system-resources': {
        'uri': '/rest/running/brocade-maps/system-resources',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/paused-cfg': {
        'uri': '/rest/running/brocade-maps/paused-cfg',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/monitoring-system-matrix': {
        'uri': '/rest/running/brocade-maps/monitoring-system-matrix',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/switch-status-policy-report': {
        'uri': '/rest/running/brocade-maps/switch-status-policy-report',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-maps/fpi-profile': {
        'uri': '/rest/running/brocade-maps/fpi-profile',
        'area': SWITCH_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-time': {
        'uri': '/rest/running/brocade-time',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-time/clock-server': {
        'uri': '/rest/running/brocade-time/clock-server',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-time/time-zone': {
        'uri': '/rest/running/brocade-time/time-zone',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security': {
        'uri': '/rest/running/brocade-security',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-security/sec-crypto-cfg': {
        'uri': '/rest/running/brocade-security/sec-crypto-cfg',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/sec-crypto-cfg-template': {
        'uri': '/rest/running/brocade-security/sec-crypto-cfg-template',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/sec-crypto-cfg-template-action': {
        'uri': '/rest/running/brocade-security/sec-crypto-cfg-template-action',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/password-cfg': {
        'uri': '/rest/running/brocade-security/password-cfg',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/user-specific-password-cfg': {
        'uri': '/rest/running/brocade-security/user-specific-password-cfg',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/user-config': {
        'uri': '/rest/running/brocade-security/user-config',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/ldap-role-map': {
        'uri': '/rest/running/brocade-security/ldap-role-map',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/sshutil': {
        'uri': '/rest/running/brocade-security/sshutil',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/sshutil-key': {
        'uri': '/rest/running/brocade-security/sshutil-key',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/sshutil-known-host': {
        'uri': '/rest/running/brocade-security/sshutil-known-host',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/sshutil-public-key': {
        'uri': '/rest/running/brocade-security/sshutil-public-key',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/sshutil-public-key-action': {
        'uri': '/rest/running/brocade-security/sshutil-public-key-action',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/password': {
        'uri': '/rest/running/brocade-security/password',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/security-certificate-generate': {
        'uri': '/rest/running/brocade-security/security-certificate-generate',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/security-certificate-action': {
        'uri': '/rest/running/brocade-security/security-certificate-action',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/security-certificate': {
        'uri': '/rest/running/brocade-security/security-certificate',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/radius-server': {
        'uri': '/rest/running/brocade-security/radius-server',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/tacacs-server': {
        'uri': '/rest/running/brocade-security/tacacs-server',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/ldap-server': {
        'uri': '/rest/running/brocade-security/ldap-server',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/auth-spec': {
        'uri': '/rest/running/brocade-security/auth-spec',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/ipfilter-policy': {
        'uri': '/rest/running/brocade-security/ipfilter-policy',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/ipfilter-rule': {
        'uri': '/rest/running/brocade-security/ipfilter-rule',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-security/security-certificate-extension': {
        'uri': '/rest/running/brocade-security/security-certificate-extension',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-license': {
        'uri': '/rest/running/brocade-license',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-license/license': {
        'uri': '/rest/running/brocade-license/license',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-license/ports-on-demand-license-info': {
        'uri': '/rest/running/brocade-license/ports-on-demand-license-info',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-snmp': {
        'uri': '/rest/running/brocade-snmp',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-snmp/system': {
        'uri': '/rest/running/brocade-snmp/system',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-snmp/mib-capability': {
        'uri': '/rest/running/brocade-snmp/mib-capability',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-snmp/trap-capability': {
        'uri': '/rest/running/brocade-snmp/trap-capability',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-snmp/v1-account': {
        'uri': '/rest/running/brocade-snmp/v1-account',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-snmp/v1-trap': {
        'uri': '/rest/running/brocade-snmp/v1-trap',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-snmp/v3-account': {
        'uri': '/rest/running/brocade-snmp/v3-account',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-snmp/v3-trap': {
        'uri': '/rest/running/brocade-snmp/v3-trap',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-snmp/access-control': {
        'uri': '/rest/running/brocade-snmp/access-control',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-supportlink': {
        'uri': '/rest/operations/supportlink',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),
    },
    'brocade-supportlink/supportlink-profile': {
        'uri': '/rest/operations/supportlink/supportlink-profile',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-operation-supportsave': {
        'uri': '/rest/operations/supportsave',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-operation-supportsave/connection': {
        'uri': '/rest/operations/supportsave/connection',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': (),  # ???
    },
    'brocade-operation-firmwaredownload': {
        'uri': '/rest/operations/firmwaredownload',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # ???
    },
    'brocade-operation-firmwaredownload/firmwaredownload-parameters': {
        'uri': '/rest/operations/firmwaredownload/firmwaredownload-parameters',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': (),  # ???
    },
    'brocade-operation-show-status': {
        'uri': '/rest/operations/show-status',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # ???
    },
    'brocade-operation-show-status/show-status': {
        'uri': '/rest/operations/show-status/show-status',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': ('GET',),
    },
    'brocade-operation-device-management': {
        'uri': '/rest/operations/device-management',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-operation-device-management/device': {
        'uri': '/rest/operations/device-management/device',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': (),  # ???
    },
    'brocade-operation-license': {
        'uri': '/rest/operations/license',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # ???
    },
    'brocade-operation-license/license-parameters': {
        'uri': '/rest/operations/license/license-parameters',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': (),  # ???
    },
    'brocade-operation-pcie-health': {
        'uri': '/rest/operations/pcie-health-test',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),
    },
    'brocade-operation-pcie-health/slot-test': {
        'uri': '/rest/operations/pcie-health-test/slot-test',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': (),  # ???
    },
    'brocade-operation-fabric': {
        'uri': '/rest/operations/fibrechannel-fabric',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-operation-fabric/fabric-operation-parameters': {
        'uri': '/rest/operations/fibrechannel-fabric/fabric-operation-parameters',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': (),  # ???
    },
    'brocade-operation-supportlink': {
        'uri': '/rest/operations/supportlink',
        'area': NULL_OBJ,
        'fid': False,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-operation-supportlink/supportlink': {
        'uri': '/rest/operations/supportlink/supportlink',
        'area': CHASSIS_OBJ,
        'fid': False,
        'methods': (),  # ???
    },
    'brocade-extension-ip-route': {
        'uri': '/rest/running/brocade-extension-ip-route',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-extension-ip-route/extension-ip-route': {
        'uri': '/rest/running/brocade-extension-ip-route/extension-ip-route',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-extension-ipsec-policy': {
        'uri': '/rest/running/brocade-extension-ipsec-policy',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-extension-ipsec-policy/extension-ipsec-policy': {
        'uri': '/rest/running/brocade-extension-ipsec-policy/extension-ipsec-policy',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-extension-tunnel': {
        'uri': '/rest/running/brocade-extension-tunnel',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-extension-tunnel/extension-tunnel': {
        'uri': '/rest/running/brocade-extension-tunnel/extension-tunnel',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-extension-tunnel/extension-tunnel-statistics': {
        'uri': '/rest/running/brocade-extension-tunnel/extension-tunnel-statistics',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-extension-tunnel/extension-circuit': {
        'uri': '/rest/running/brocade-extension-tunnel/extension-circuit',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-extension-tunnel/extension-circuit-statistics': {
        'uri': '/rest/running/brocade-extension-tunnel/extension-circuit-statistics',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-extension-tunnel/circuit-qos-statistics': {
        'uri': '/rest/running/brocade-extension-tunnel/circuit-qos-statistics',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-extension-tunnel/wan-statistics': {
        'uri': '/rest/running/brocade-extension-tunnel/wan-statistics',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-extension': {
        'uri': '/rest/running/brocade-extension',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-extension/traffic-control-list': {
        'uri': '/rest/running/brocade-extension/traffic-control-list',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-extension/dp-hcl-status': {
        'uri': '/rest/running/brocade-extension/dp-hcl-status',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-extension/global-lan-statistics': {
        'uri': '/rest/running/brocade-extension/global-lan-statistics',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-extension/lan-flow-statistics': {
        'uri': '/rest/running/brocade-extension/lan-flow-statistics',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-lldp': {
        'uri': '/rest/running/brocade-lldp',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-lldp/lldp-neighbor': {
        'uri': '/rest/running/brocade-lldp/lldp-neighbor',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-lldp/lldp-profile': {
        'uri': '/rest/running/brocade-lldp/lldp-profile',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-lldp/lldp-statistics': {
        'uri': '/rest/running/brocade-lldp/lldp-statistics',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-lldp/lldp-global': {
        'uri': '/rest/running/brocade-lldp/lldp-global',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': ('GET',),
    },
    'brocade-operation-zone': {
        'uri': '/rest/running/brocade-operation-zone',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-operation-zone/zone-operation-parameters': {
        'uri': '/rest/running/brocade-operation-zone/zone-operation-parameters',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': (),  # ???
    },
    'brocade-operation-extension': {
        'uri': '/rest/operations/extension',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-operation-extension/extension-operation-parameters': {
        'uri': '/rest/operations/extension/extension-operation-parameters',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': (),  # ???
    },

    'brocade-operation-lldp': {
        'uri': '/rest/operations/lldp',
        'area': NULL_OBJ,
        'fid': True,
        'methods': (),  # Only the sub-leaves can be acted on
    },
    'brocade-operation-lldp/lldp-operations': {
        'uri': '/rest/operations/lldp/lldp-operations',
        'area': FABRIC_OBJ,
        'fid': True,
        'methods': (),
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

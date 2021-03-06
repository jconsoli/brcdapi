#!/usr/bin/python
# Copyright 2020 Jack Consoli.  All rights reserved.
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
:mod:`switch.py` - Methods to create, delete, and modify logical switches.

**Description**

    A collection of methods to perform common switch functions. For example on how to use these functions, see
    api_examples/switch_delete.py and api_examples/switch_create.py. While most of the API requests are pretty
    straight forward and don't need a driver, there are a few things that need special attention and therefore have a
    library method:

    +-----------------------+---------------------------------------------------------------------------------------+
    | Method                | Description                                                                           |
    +=======================+=======================================================================================+
    | switch_wwn            | Reads and returns the logical switch WWN from the API. I needed this method for       |
    |                       | fibrechannel_switch() so I figured I may as well make it public.                      |
    +-----------------------+---------------------------------------------------------------------------------------+
    | logical_switches      | Returns a list of logical switches with the default switch first. It's fairly common  |
    |                       | to need a list of logical switches with the ability to discern which one is the       |
    |                       | default so this method is provided as a conienence.                                   |
    +-----------------------+---------------------------------------------------------------------------------------+
    | add_ports             | Move ports to a logical switch. Ports cannot be moved if they have any special        |
    |                       | configurations so this method automatically sets all ports to be moved back to the    |
    |                       | factory default setting. Furthermore, moving ports takes a long time. So as not to    |
    |                       | incur an HTTP session timeout, this method breaks up port moves into smaller chunks.  |
    +-----------------------+---------------------------------------------------------------------------------------+
    | fibrechannel_switch   | Set switch configuration parameters for                                               |
    |                       | brocade-fibrechannel-switch/fibrechannel-switch. Some requests require the WWN and    |
    |                       | some require an ordered dictionary. This method automitically finds the switch WWN if |
    |                       | it's not already known and handles the ordered dictionary. I'm sure I went over board |
    |                       | with the ordered list but rather than figure out what needed the ordered list and     |
    |                       | needed a WWN, since I have this method I use it for everything except enabling and    |
    |                       | disabling switches.                                                                   |
    +-----------------------+---------------------------------------------------------------------------------------+
    | create_switch         | Create a logical switch. Creating a logical switch requires that the chassis be VF    |
    |                       | enabled and it's easier to set the switch type at switch creation time. This method   |
    |                       | is a little more convienent to use.                                                   |
    +-----------------------+---------------------------------------------------------------------------------------+
    | delete_switch         | Sets all ports to their default configuration, moves those ports to the default       |
    |                       | switchm and then deletes the switch.                                                  |
    +-----------------------+---------------------------------------------------------------------------------------+

**WARNING**
    * Circuits and tunnels are not automatically removed from GE ports when moving them to another logical switch
      Testing with GE ports was minimal
    * When enabling or disabling a switch, brocade-fibrechannel-switch/fibrechannel-switch/is-enabled-state, other
      actions may not take effect. The methods herein take this into account but programmers hacking this script cannot
      improve on effeciency by combining these operations. I think that if you put the enable action last, it will get
      processed last but I stopped experimenting with ordered dictionaries and just broke the two operations out. I left
      all the ordered dictionaries in because once I got everything working, I did not want to change anything.
    * The address of a port in a FICON logical switch must be bound. As of FOS 9.0.b, there was no ability to bind the
      port addresses. This module can be used to create a FICON switch but if you attempt to enable the ports, you an
      error is returned stating "Port enabl failed because port not bound in FICON LS".

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 3.0.0     | 27 Nov 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 31 Dec 2020   | Only report number of ports to move in add_ports if there are ports to add.       |
    |           |               | Try to delete the switch anyway, even if there is an error setting ports to the   |
    |           |               | default.
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020 Jack Consoli'
__date__ = '31 Dec 2020'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.1'

import pprint
import collections
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.pyfos_auth as pyfos_auth
import brcdapi.log as brcdapi_log
import brcdapi.port as brcdapi_port
import brcdapi.util as brcdapi_util

MAX_PORTS_TO_MOVE = 32  # It takes about 10 sec + 500 msec per port to move per API request. This variable defines the
    # number of ports that can be moved in any single Rest request so as not to encounter an HTTP connection timeout.

def switch_wwn(session, fid, echo=False):
    """Returns the switch WWN from the logical switch matching the specified FID.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: Switch WWN or return from first error encountered
    :rtype: str, dict
    """
    brcdapi_log.log('Getting switch data from brcdapi.switch.switch_wwn() for FID ' + str(fid), echo)
    uri = 'brocade-fibrechannel-switch/fibrechannel-switch'
    obj = brcdapi_rest.get_request(session, uri, fid)
    if pyfos_auth.is_error(obj):
        brcdapi_log.exception('Failed to get switch data for FID ' + str(fid), echo)
        return obj
    try:
        return obj.get('fibrechannel-switch')[0].get('name')
    except:
        buf = 'Unexpected data returned from ' + uri
        brcdapi_log.exception(buf, echo)
        return pyfos_auth.create_error(brcdapi_util.HTTP_INT_SERVER_ERROR, buf)


def logical_switches(session, echo=False):
    """Returns a list of logical switches with the default switch first

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :return: If type dict, brcdapi_rest error status object. Otherwise, list of the FIDs in the chassis. Empty if not VF
        enabled. The default switch FID is first, [0].
    :rtype: dict, list
    """
    # Get the chassis information
    obj = brcdapi_rest.get_request(session, 'brocade-chassis/chassis', None)
    if pyfos_auth.is_error(obj):
        return obj
    rl = list()
    try:
        if obj['chassis']['vf-enabled']:
            # Get all the switches in this chassis
            uri = 'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch'
            obj = brcdapi_rest.get_request(session, uri, None)
            if pyfos_auth.is_error(obj):
                return obj
            for ls in obj['fibrechannel-logical-switch']:
                if bool(ls['default-switch-status']):
                    rl.append(ls)
                    break
            rl.extend([ls for ls in obj['fibrechannel-logical-switch'] if not bool(ls['default-switch-status'])])
    except:
        ml = ['Unexpected data returned from ' + uri]
        if isinstance(obj, dict):
            ml.append(pprint.pformat(obj) if isinstance(obj, dict) else 'Unknown programming error')
        brcdapi_log.exception(ml, echo)
        return pyfos_auth.create_error(brcdapi_util.HTTP_INT_SERVER_ERROR, 'Unknown error', ml)

    return rl


def fibrechannel_switch(session, fid, parms, wwn=None, echo=False):
    """Set parameters for brocade-fibrechannel-switch/fibrechannel-switch.

    Note: The intent of this method was to alleviate the need for programmers to have to build an ordered dictionary
    and look up the WWN of the switch.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param parms: Content for brocade-fibrechannel-switch/fibrechannel-switch
    :type parms: dict
    :param wwn: WWN of switch. If None, the WWN for the fid is read from the API.
    :type wwn: str, None
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: Return from last request or first error encountered
    :rtype: dict
    """
    brcdapi_log.log('brocade-fibrechannel-switch/fibrechannel-switch FID ' + str(fid) + ' with parms:\n' +
                    pprint.pformat(parms), echo)
    if len(parms.keys()) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    if wwn is None:
        # I don't know why, but sometimes I need the WWN for brocade-fibrechannel-switch/fibrechannel-switch
        wwn = switch_wwn(session, fid, echo)
        if pyfos_auth.is_error(wwn):
            return wwn

    # Configure the switch
    sub_content = collections.OrderedDict()  # I think 'name' must be first
    sub_content['name'] = wwn
    for k, v in parms.items():
        sub_content[k] = v
    return brcdapi_rest.send_request(session,
                                    'brocade-fibrechannel-switch/fibrechannel-switch',
                                    'PATCH',
                                    {'fibrechannel-switch': sub_content},
                                    fid)


def fibrechannel_configuration(session, fid, parms, echo=False):
    """Sets the fabric parameters for 'brocade-fibrechannel-configuration'.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param parms: Content for brocade-fibrechannel-configuration/fabric
    :type parms: dict
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: Return from last request or first error encountered
    :rtype: dict
    """
    brcdapi_log.log('brocade-fibrechannel-configuration/fabric FID ' + str(fid) + ' with parms: ' +
                    ', '.join([str(buf) for buf in parms.keys()]), echo)
    if len(parms.keys()) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    # Configure the switch
    return brcdapi_rest.send_request(session,
                                    'brocade-fibrechannel-configuration/fabric',
                                    'PATCH',
                                    dict(fabric=parms),
                                    fid)


def add_ports(session, to_fid, from_fid, i_ports=None, i_ge_ports=None, echo=False):
    """Move ports to a logical switch. Ports are set to the default configuration and disabled before moving them

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param to_fid: Logical FID number where ports are being moved to.
    :type to_fid: int
    :param from_fid: Logical FID number where ports are being moved from.
    :type from_fid: int
    :param i_ports: Ports to be moved to the switch specified by to_fid
    :type i_ports: int, str, list, tuple
    :param i_ge_ports: GE Ports to be moved to the switch specified by to_fid
    :type i_ge_ports: int, str, list, tuple
    :param echo: If True, the list of ports for each move is echoed to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object for the first error encountered of the last request
    :rtype: dict
    """
    ports = brcdapi_port.ports_to_list(i_ports)
    ge_ports = brcdapi_port.ports_to_list(i_ge_ports)
    if len(ports) + len(ge_ports) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ
    buf = 'Attempting to move ' + str(len(ports)) + ' ports and ' + str(len(ge_ports)) + ' GE ports from FID ' + \
          str(from_fid) + ' to FID ' + str(to_fid)
    brcdapi_log.log(buf, echo)

    # Set all ports to the default configuration and disable before moving.
    obj = brcdapi_port.default_port_config(session, from_fid, ports + ge_ports)
    if pyfos_auth.is_error(obj):
        brcdapi_log.exception('Failed to set all ports to the default configuration', echo)
        return obj

    # Move the ports, FOS returns an error if ports is an empty list in:
    # 'port-member-list': {'port-member': ports}
    # so I have to custom build the content. Furthermore, it takes about 400 msec per port to move so to avoid an HTTP
    # connection timeout, the port moves are done in batches.
    while len(ports) > 0:
        sub_content = {'fabric-id': to_fid}
        pl = ports[0: MAX_PORTS_TO_MOVE] if len(ports) > MAX_PORTS_TO_MOVE else ports
        ports = ports[MAX_PORTS_TO_MOVE:]
        sub_content.update({'port-member-list': {'port-member': pl}})
        ml = ['Start moving ports:'] + ['  ' + buf for buf in pl]
        brcdapi_log.log(ml, echo)
        obj = brcdapi_rest.send_request(session,
                                        'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch',
                                        'POST',
                                        {'fibrechannel-logical-switch': sub_content})
        if pyfos_auth.is_error(obj):
            brcdapi_log.exception('Encoutered errors moving ports.', echo)
            return obj
        else:
            brcdapi_log.log('Successfully moved ports.', echo)

    # Do the same for the GE ports
    while len(ge_ports) > 0:
        sub_content = {'fabric-id': to_fid}
        pl = ge_ports[0: MAX_PORTS_TO_MOVE] if len(ge_ports) > MAX_PORTS_TO_MOVE else ge_ports
        ge_ports = ports[MAX_PORTS_TO_MOVE:]
        sub_content.update({'ge-port-member-list': {'port-member': pl}})
        ml = ['Start moving GE ports:'] + ['  ' + buf for buf in pl]
        brcdapi_log.log(ml, echo)
        obj = brcdapi_rest.send_request(session,
                                        'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch',
                                        'POST',
                                        {'fibrechannel-logical-switch': sub_content})
        if pyfos_auth.is_error(obj):
            brcdapi_log.exception('Encoutered errors moving ports.', echo)
            return obj
        else:
            brcdapi_log.log('Successfully moved ports.', echo)


def create_switch(session, fid, base, ficon, echo=False):
    """Create a logical switch with some basic configuration then disables the switch

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param base: If Ture - set switch as base switch
    :type base: bool
    :param ficon: If True - set switch as a FICON switch
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: Return from create switch operation or first error encountered
    :rtype: dict
    """
    # Make sure the chassis configuration supports the logical switch to create.
    switch_list = logical_switches(session)
    if isinstance(switch_list, dict):
        # The only time brcdapi_switch.logical_switches() returns a dict is when an error is encountered
        brcdapi_log.log(pyfos_auth.formatted_error_msg(switch_list), True)
        return switch_list
    if not isinstance(switch_list, list):
        return pyfos_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'Chassis not VF enabled', '')
    if fid in switch_list:
        return pyfos_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'FID already present in chassis', str(fid))
    if base and ficon:
        return pyfos_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'Switch type cannot be both base and ficon',
                                       str(fid))

    # Create the logical switch
    sub_content = collections.OrderedDict()  # I'm not certain it needs to be ordered. Once bitten twice shy.
    sub_content['fabric-id'] = fid
    sub_content['base-switch-enabled'] = 0 if base is None else 1 if base else 0
    sub_content['ficon-mode-enabled'] = 0 if ficon is None else 1 if ficon else 0
    brcdapi_log.log('Creating logical switch ' + str(fid), echo)
    obj = brcdapi_rest.send_request(session,
                                    'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch',
                                    'POST',
                                    {'fibrechannel-logical-switch': sub_content})
    if pyfos_auth.is_error(obj):
        return obj

    # Disable the switch
    fibrechannel_switch(session, fid, {'is-enabled-state': False}, None, echo)


def delete_switch(session, fid, echo=False):
    """Sets all ports to their default configuration, moves those ports to the default switch, and deletes the switch

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number to be deleted.
    :type fid: int
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object for the first error encountered of the last request
    :rtype: dict
    """
    switch_list = logical_switches(session)
    if isinstance(switch_list, dict):
        # The only time brcdapi_switch.logical_switches() returns a dict is when an error is encountered
        brcdapi_log.log(pyfos_auth.formatted_error_msg(switch_list), True)
        return switch_list
    if not isinstance(switch_list, list):
        return pyfos_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'Chassis not VF enabled', '')

    default_fid = switch_list[0]['fabric-id']
    brcdapi_log.log('brcdapi.switch.delete_switch(): Attempting to delete FID ' + str(fid), echo)
    # Find this logical switch
    for i in range(0, len(switch_list)):
        if switch_list[i]['fabric-id'] == fid:
            if i == 0:
                return pyfos_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST,
                                               'Cannot delete the default logical switch',
                                               str(fid))

            # Move all the ports to the default logical switch.
            d = switch_list[i].get('port-member-list')
            port_l = None if d is None else d.get('port-member')
            d = switch_list[i].get('ge-port-member-list')
            ge_port_l = None if d is None else d.get('port-member')
            obj = add_ports(session, default_fid, fid, port_l, ge_port_l, echo)
            if pyfos_auth.is_error(obj):
                brcdapi_log.exception('Error moving ports from FID ' + str(fid) + ' to FID ' + str(default_fid), echo)
                # return obj

            # Delete the switch
            obj =  brcdapi_rest.send_request(session,
                                             'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch',
                                             'DELETE',
                                             {'fibrechannel-logical-switch': {'fabric-id': fid}})
            brcdapi_log.log('Error' if pyfos_auth.is_error(obj) else 'Success' + ' deleting FID ' + str(fid), echo)
            return obj

    return pyfos_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'FID not found', str(fid))

# Copyright 2020, 2021, 2022 Jack Consoli.  All rights reserved.
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
:mod:`port.py` - Methods to configure ports.

Description::

    A collection of methods to perform common port functions. For examples on how to use these functions, see
    brocade-rest-api-examples/port_config.py. While most of the API requests are pretty straight forward and don't need,
    a driver there are a few things that need special attention and therefore have a library method.

Public Methods & Data::

    +-----------------------+---------------------------------------------------------------------------------------+
    | Method                | Description                                                                           |
    +=======================+=======================================================================================+
    | ports_to_list         | Converts ports to a list of ports. Many sources for ports return None, a single port, |
    |                       | or just the port (no slot on fixed port switches) and sometimes the port is an        |
    |                       | integer. The API always wants to see ports in 's/p' notation.                         |
    +-----------------------+---------------------------------------------------------------------------------------+
    | sort_ports            | Sorts a list of ports. This is useful because if port_l is a list of ports in 's/p'   |
    |                       | notation, .sort() performs an ASCII sort which does not return the desired results.   |
    +-----------------------+---------------------------------------------------------------------------------------+
    | clear_stats           | Clear all statistical counters associated with a port or list of ports.               |
    +-----------------------+---------------------------------------------------------------------------------------+
    | default_port_config   | Disables and sets an FC port or list of FC ports to their factory default state.      |
    +-----------------------+---------------------------------------------------------------------------------------+
    | port_enable_disable   | Enables or disables a port or list of ports. Typically enable_port() or               |
    |                       | port_disable() is called externally instead of this method.                           |
    +-----------------------+---------------------------------------------------------------------------------------+
    | enable_port           | Enables a port or list of ports on a specific logical switch.                         |
    +-----------------------+---------------------------------------------------------------------------------------+
    | disable_port          | Disables a port or list of ports on a specific logical switch.                        |
    +-----------------------+---------------------------------------------------------------------------------------+
    | decommission_port     | Decomissions a port or list of ports                                                  |
    +-----------------------+---------------------------------------------------------------------------------------+

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 3.0.0     | 27 Nov 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 13 Feb 2021   | Added disable_port()                                                              |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.2     | 14 Nov 2021   | Deprecated pyfos_auth                                                             |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.3     | 31 Dec 2021   | Improved comments only. No functional changes                                     |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.4     | 28 Apr 2022   | Use new URI formats.                                                              |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.5     | 22 Jun 2022   | Removed GE input parameter in clear_stats()                                       |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.6     | 25 Jul 2022   | Added decommission_port(), sort_ports(), and added persistent to enable_port()    |
    |           |               | and disable_port                                                                  |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020, 2021, 2022 Jack Consoli'
__date__ = '25 Jul 2022'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.6'

import collections
import brcdapi.util as brcdapi_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util

_MAX_CHECK = 3  # Port decommision maximum number of times to poll the switch for completion status
_WAIT = 1  # Port decommission wait time before each status poll check


def ports_to_list(i_port_l):
    """Converts ports to a list of ports. Many sources for ports return None, a single port, or just the port (no slot
    on fixed port switches) and sometimes the port is an integer. The API always wants to see ports in 's/p' notation.

    :param i_port_l: Port or list of ports
    :type i_port_l: int, str, list, tuple
    :return: List of ports in s/p notation. If i_port_l is None, an empty list is returned
    :rtype: list
    """
    temp_l = list() if i_port_l is None else [str(i_port_l)] if isinstance(i_port_l, (int, str)) else \
        [str(p) for p in i_port_l]
    return [p if '/' in p else '0/' + p for p in temp_l]


def sort_ports(i_port_l):
    """Converts ports to a list of ports in s/p notation. Duplicates are removed. Sorting is by slot then by port.

    :param i_port_l: Port or list of ports
    :type i_port_l: int, str, list, tuple
    :return: List of sorted ports in s/p notation. If i_port_l is None, an empty list is returned
    :rtype: list
    """
    wd = dict()  # Working dictionary of slots which contains a dictionary of ports
    for port in ports_to_list(i_port_l):
        t = port.split('/')
        if int(t[0]) not in wd:
            wd.update({int(t[0]): dict()})
        wd[int(t[0])].update({int(t[1]): port})

    # Now sort them and create the return list
    rl = list()
    slot_l = list(wd.keys())
    slot_l.sort()
    for slot in slot_l:
        port_l = list(wd[slot].keys())
        port_l.sort()
        rl.extend([wd[slot][port] for port in port_l])

    return rl


def clear_stats(session, fid, ports_l):
    """Clear all statistical counters associated with a port or list of ports

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param ports_l: Port or list of FC ports for stats to be cleared on
    :type ports_l: list
    :return: brcdapi_rest status object
    :rtype: dict
    """
    pl = [{'name': p, 'reset-statistics': 1} for p in ports_to_list(ports_l)]
    if len(pl) > 0:
        content = {'fibrechannel-statistics': pl}
        return brcdapi_rest.send_request(session,
                                         'running/brocade-interface/fibrechannel-statistics',
                                         'PATCH',
                                         content,
                                         fid)

    return brcdapi_util.GOOD_STATUS_OBJ  # If we get here, the port list, ports_l, was empty.


# default_port_config_d is used in default_port_config(). I made it public so that it could be programitically altered
# or be used by other customer created scripts that do not use default_port_config().
default_port_config_d = collections.OrderedDict()  # This may not need to be ordered.
default_port_config_d['is-enabled-state'] = False
default_port_config_d['user-friendly-name'] = ''
default_port_config_d['speed'] = 0  # Autonegotiate
default_port_config_d['g-port-locked'] = 0  # Unlocked
default_port_config_d['e-port-disable'] = 0  # Enables the port as an E_Port
default_port_config_d['n-port-enabled'] = 1  # Port may operate as an N-Port. Only relevant in Access Gateway mode
default_port_config_d['d-port-enable'] = 0  # D-Port is disabled
default_port_config_d['persistent-disable'] = 0  # Persistent-disable is not active for the port
default_port_config_d['qos-enabled'] = 1  # Port QoS enabled
default_port_config_d['compression-configured'] = 0  # Compression configuration disabled
default_port_config_d['encryption-enabled'] = 0  # Disables the encryption configuration on the specified port
default_port_config_d['target-driven-zoning-enable'] = 0  # Target Driven Zoning configuration is disabled
default_port_config_d['sim-port-enabled'] = 0  # SIM port is disabled
default_port_config_d['mirror-port-enabled'] = 0  # Mirror port is disabled
default_port_config_d['credit-recovery-enabled'] = 1  # Credit recovery is enabled.
default_port_config_d['f-port-buffers'] = 0  # No F-Port buffers
default_port_config_d['e-port-credit'] = 0  # No additional E-Port credits
default_port_config_d['csctl-mode-enabled'] = 0  # CSCTL mode is disabled
default_port_config_d['fault-delay-enabled'] = 0  # The value is R_A_TOV
default_port_config_d['octet-speed-combo'] = 1  # Auto-negotiated or fixed port speeds of 32, 16, 8, 4, and 2 Gb/s.
default_port_config_d['isl-ready-mode-enabled'] = 0  # ISL ready mode is disabled on the port
default_port_config_d['rscn-suppression-enabled'] = 0  # RSCN is disabled on the port
default_port_config_d['los-tov-mode-enabled'] = 0  # LOS_TOV mode is disabled on the port
default_port_config_d['npiv-enabled'] = 1  # NPIV is enabled on the port
default_port_config_d['npiv-pp-limit'] = 126  # 126 logins
default_port_config_d['ex-port-enabled'] = 0  # Not configured as an EX-Port
default_port_config_d['fec-enabled'] = 1  # FEC is enabled
default_port_config_d['port-autodisable-enabled'] = 0  # Disabled
default_port_config_d['trunk-port-enabled'] = 1  # Enabled
default_port_config_d['pod-license-state'] = 'released'  # The port is not reserved under a POD license
default_port_config_d['port-peer-beacon-enabled'] = False  # Disabled
default_port_config_d['clean-address-enabled'] = False  # Disabled
default_port_config_d['congestion-signal-enabled'] = True  # Gen7 FPIN feature


def default_port_config(session, fid, i_port_l):
    """Disables and sets a list of FC ports to their factory default state

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_port_l: List of ports in the API format of s/p. For a fixed port switch for example, port 12 is '0/12'
    :type i_port_l: tuple, list, str, int
    :return: The object returned from the API. If ports is an empty list, a made up good status is returned.
    :rtype: dict
    """
    global default_port_config_d

    port_l = ports_to_list(i_port_l)
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    # Not all features are supported on all platforms. In most cases, even if you disable the unsupported feature, FOS
    # returns an error. To get around this, I read the port configuration and only add parameters to send to the switch
    # if they exist in the data returned from the switch

    # Read in the port configurations
    obj = brcdapi_rest.get_request(session, 'running/brocade-interface/fibrechannel', fid)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.log('Failed to read brocade-interface/fibrechannel for fid ' + str(fid), True)
        return obj
    # Put all the ports in a dictionary for easy lookup
    port_d = dict()
    for port in obj['fibrechannel']:
        port_d.update({port['name']: port})

    # Figure out what ports to change
    pl = list()
    for port in port_l:
        d = port_d.get(port)
        if d is None:
            brcdapi_log.exception('Port ' + port + ' not in FID ' + str(fid), True)
            continue
        port_content = collections.OrderedDict()  # This may not need to be ordered.
        port_content['name'] = port
        for k, v in default_port_config_d.items():
            if k in d:
                if k == 'speed':
                    if d.get('auto-negotiate') is not None and d['auto-negotiate'] == 0:
                        port_content[k] = 0
                elif k == 'user-friendly-name':
                    l = port.split('/')
                    port_name = 'port' + l[1]
                    if l[0] != '0':
                        port_name = 'slot' + l[0] + ' ' + port_name
                    if 'user-friendly-name' in d:
                        if d['user-friendly-name'] != port_name:
                            port_content[k] = port_name
                    else:
                        port_content[k] = port_name
                elif v != d[k]:
                    port_content[k] = v
        if len(port_content.keys()) > 1:
            pl.append(port_content)

    # Now modify the port(s)
    if len(pl) > 0:
        return brcdapi_rest.send_request(session,
                                         'running/brocade-interface/fibrechannel',
                                         'PATCH',
                                         {'fibrechannel': pl},
                                         fid)

    return brcdapi_util.GOOD_STATUS_OBJ  # The port list was empty if we get here.


def port_enable_disable(session, fid, enable_flag, i_port_l, persistent=False, echo=False):
    """Enable or disable a port or list of ports.

    :param session: Session object returned from brcdapi.fos_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param enable_flag: True - enable ports. False - disable ports
    :type enable_flag: bool
    :param i_port_l: List of ports to enable or disable
    :type i_port_l: tuple, list, str
    :param persistent: If Ture, persistently disables the port
    :type persistent: bool
    :param echo: If True, print activity to STD OUT
    :type echo: bool
    :return: The object returned from the API. If ports is an empty list, a made up good status is returned.
    :rtype: dict
    """
    port_l = ports_to_list(i_port_l)
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    # Now enable/disable the port(s)
    buf = ''
    if persistent:
        buf = 'Persistent'
        pd = 0 if enable_flag else 1
        pl = [{'name': p, 'persistent-disable': pd} for p in port_l]
    else:
        pl = [{'name': p, 'is-enabled-state': enable_flag} for p in port_l]
    buf += 'En' if enable_flag else 'Dis'
    brcdapi_log.log(buf + 'abling ' + str(len(port_l)) + ' ports.', echo)
    obj = brcdapi_rest.send_request(session,
                                    'running/brocade-interface/fibrechannel',
                                    'PATCH',
                                    {'fibrechannel': pl},
                                    fid)
    if brcdapi_auth.is_error(obj):
        return obj

    if persistent and enable_flag:
        # FOS does not permit clearning the persistent disable bit and enabling the port in the same request
        obj = brcdapi_rest.send_request(session,
                                    'running/brocade-interface/fibrechannel',
                                    'PATCH',
                                    {'fibrechannel': [{'name': p, 'is-enabled-state': enable_flag} for p in port_l]},
                                    fid)

    return obj


def enable_port(session, fid, i_port_l, persistent=False, echo=False):
    """Enables a port or list of ports on a specific logical switch.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_port_l: List of ports to enable or disable
    :type i_port_l: tuple, list, str, in
    :param persistent: If Ture, persistently disables the port
    :type persistent: bool
    :param echo: If True, print activity to STD OUT
    :type echo: bool
    :return: The object returned from the API. If i_port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    return port_enable_disable(session, fid, True, i_port_l, persistent=persistent, echo=echo)


def disable_port(session, fid, i_port_l, persistent=False, echo=False):
    """Disables a port or list of ports on a specific logical switch.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_port_l: List of ports to enable or disable
    :type i_port_l: tuple, list, str, in
    :param persistent: If Ture, persistently disables the port
    :type persistent: bool
    :param echo: If True, print activity to STD OUT
    :type echo: bool
    :return: The object returned from the API. If i_port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    return port_enable_disable(session, fid, False, i_port_l, persistent=persistent, echo=echo)


def decommission_port(session, fid, i_port_l, port_type, echo=False):
    """Decomissions a port or list of ports.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_port_l: List of ports to enable or disable
    :type i_port_l: tuple, list, str, int
    :param port_type: 'port' or 'qsfp-port'
    :type port_type: str
    :param echo: If True, print activity to STD OUT
    :type echo: bool
    :return: The object returned from the API. If i_port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    global _MAX_CHECK, _WAIT

    port_l = ports_to_list(i_port_l)
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    # Now decommision the port(s)
    brcdapi_log.log('Decommissioning ' + str(len(port_l)) + ' ports.', echo)
    port_d_l = list()
    for port in port_l:
        port_d_l.append({'slot-port': port, 'port-decommission-type': port_type})
    # WARNING: As of 11 July 2022 there is a misprint in the API Guide that indicates that 'input' is required.
    obj = brcdapi_rest.send_request(session,
                                    '/operations/port-decommission',
                                    'POST',
                                    {'port-decommission-parameters': port_d_l},
                                    fid)
    if brcdapi_auth.is_error(obj):
        return obj  # Let the calling application deal with device issues
    try:
        message_id = obj['show-status']['message-id']
        status = obj['show-status']['status']
    except KeyError:
        return brcdapi_auth.create_error(brcdapi_util.HTTP_INT_SERVER_ERROR,
                                         brcdapi_util.HTTP_REASON_UNEXPECTED_RESP,
                                         "Missing: ['show-status']['message-id']")

    # Check to see if it completed
    return obj if status == 'done' else brcdapi_rest.check_status(session, fid, message_id, _MAX_CHECK, _WAIT)

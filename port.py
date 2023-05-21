# Copyright 2020, 2021, 2022, 2023 Jack Consoli.  All rights reserved.
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
    | bind_addresses        | Binds port addresses to ports. Requires FOS 9.1 or higher.                            |
    +-----------------------+---------------------------------------------------------------------------------------+
    | clear_stats           | Clear all statistical counters associated with a port or list of ports.               |
    +-----------------------+---------------------------------------------------------------------------------------+
    | decommission_port     | Decommissions a port or list of ports                                                 |
    +-----------------------+---------------------------------------------------------------------------------------+
    | default_port_config   | Disables and sets an FC port or list of FC ports to their factory default state.      |
    +-----------------------+---------------------------------------------------------------------------------------+
    | disable_port          | Disables a port or list of ports on a specific logical switch.                        |
    +-----------------------+---------------------------------------------------------------------------------------+
    | enable_port           | Enables a port or list of ports on a specific logical switch.                         |
    +-----------------------+---------------------------------------------------------------------------------------+
    | port_enable_disable   | Enables or disables a port or list of ports. Typically enable_port() or               |
    |                       | port_disable() is called externally instead of this method.                           |
    +-----------------------+---------------------------------------------------------------------------------------+
    | ports_to_list         | Converts ports to a list of ports. Many sources for ports return None, a single port, |
    |                       | or just the port (no slot on fixed port switches) and sometimes the port is an        |
    |                       | integer. The API always wants to see ports in 's/p' notation.                         |
    +-----------------------+---------------------------------------------------------------------------------------+
    | port_range_to_list    | Converts a CSV list of ports to ranges as text. Ports are converted to standard s/p   |
    |                       | notation and sorted by slot. The original order may not be preserved. For example:    |
    |                       | "5/0-2, 9, 2/6-5, 5/6-8" is returned as:                                              |
    |                       | ['5/0', '5/1', '5/2', '5/6', '5/7', '5/8', '0/9', '2/5', '2/6']                       |
    +-----------------------+---------------------------------------------------------------------------------------+
    | release_pod           | Releases a POD license for a port or list of ports.                                   |
    +-----------------------+---------------------------------------------------------------------------------------+
    | reserve_pod           | Reserves a POD license for a port or list of ports                                    |
    +-----------------------+---------------------------------------------------------------------------------------+
    | set_mode              | Set the mode (E-Port only, F-Port only, or any).                                      |
    +-----------------------+---------------------------------------------------------------------------------------+
    | sort_ports            | Sorts a list of ports. This is useful because if port_l is a list of ports in 's/p'   |
    |                       | notation, .sort() performs an ASCII sort which does not return the desired results.   |
    +-----------------------+---------------------------------------------------------------------------------------+
    | is_port               | Tests a value to determine if it is a valid port                                      |
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
    | 3.0.7     | 14 Oct 2022   | Modified decommission_port() to handle case when status is immediately available  |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.8     | 01 Jan 2023   | Added reserve_pod(), release_pod(), port_range_to_list(), set_mode(), and         |
    |           |               | bind_addresses().                                                                 |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.9     | 09 May 2023   | used brcdapi_rest.operations_request() in decommission_port()                     |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.1.0     | 21 May 2023   | Updated comments and removed unused import                                        |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020, 2021, 2022, 2023 Jack Consoli'
__date__ = '21 May 2023'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.1.0'

import collections
import brcdapi.util as brcdapi_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util

_MAX_CHECK = 3  # Port decommission maximum number of times to poll the switch for completion status
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
    :param ports_l: Port or list of FC ports for stats to be cleared on in s/p notation
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


# default_port_config_d is used in default_port_config(). I made it public so that it could be programmatically altered
# or be used by other customer created scripts that do not use default_port_config().
default_port_config_d = collections.OrderedDict()  # This may not need to be ordered.
default_port_config_d['is-enabled-state'] = False
default_port_config_d['user-friendly-name'] = ''
default_port_config_d['speed'] = 0  # Auto-negotiate
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
        brcdapi_log.log('Failed to read brocade-interface/fibrechannel for fid ' + str(fid), echo=True)
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
            brcdapi_log.exception('Port ' + port + ' not in FID ' + str(fid), echo=True)
            continue
        port_content = collections.OrderedDict()  # This may not need to be ordered.
        port_content['name'] = port
        for k, v in default_port_config_d.items():
            if k in d:
                if k == 'speed':
                    if d.get('auto-negotiate') is not None and d['auto-negotiate'] == 0:
                        port_content[k] = 0
                elif k == 'user-friendly-name':
                    temp_l = port.split('/')
                    port_name = 'port' + temp_l[1]
                    if temp_l[0] != '0':
                        port_name = 'slot' + temp_l[0] + ' ' + port_name
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
    buf += ' En' if enable_flag else ' Dis'
    brcdapi_log.log(buf + 'abling ' + str(len(port_l)) + ' ports.', echo)
    obj = brcdapi_rest.send_request(session,
                                    'running/brocade-interface/fibrechannel',
                                    'PATCH',
                                    {'fibrechannel': pl},
                                    fid)
    if brcdapi_auth.is_error(obj):
        return obj

    if persistent and enable_flag:
        # FOS does not permit cleaning the persistent disable bit and enabling the port in the same request
        content_d = dict(fibrechannel=[{'name': p, 'is-enabled-state': enable_flag} for p in port_l])
        obj = brcdapi_rest.send_request(session,
                                        'running/brocade-interface/fibrechannel',
                                        'PATCH',
                                        content_d,
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
    """Decommissions a port or list of ports.

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

    # Now decommission the port(s)
    brcdapi_log.log('Decommissioning ' + str(len(port_l)) + ' ports.', echo)
    port_d_l = list()
    for port in port_l:
        port_d_l.append({'slot-port': port, 'port-decommission-type': port_type})
    # WARNING: As of 11 July 2022, the API Guide describes the internal data structure for an RPC call.
    return brcdapi_rest.operations_request(session,
                                           'operations/port-decommission',
                                           'POST',
                                           {'port-decommission-parameters': port_d_l},
                                           fid=fid)


def reserve_pod(session, fid, ports_l):
    """Reserves a POD license for a port or list of ports.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param ports_l: List of ports to enable or disable
    :type ports_l: tuple, list, str, int
    :return: The object returned from the API. If i_port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    content_l = [{'name': p, 'pod-license-state': 'reserved'} for p in ports_to_list(ports_l)]
    if len(content_l) > 0:
        return brcdapi_rest.send_request(session,
                                         'running/brocade-interface/fibrechannel',
                                         'PATCH',
                                         {'fibrechannel': content_l},
                                         fid)

    return brcdapi_util.GOOD_STATUS_OBJ  # If we get here, the port list, ports_l, was empty.


def release_pod(session, fid, ports_l):
    """Releases a POD license for a port or list of ports.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param ports_l: List of ports to enable or disable
    :type ports_l: tuple, list, str, int
    :return: The object returned from the API. If i_port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    content_l = [{'name': p, 'pod-license-state': 'released'} for p in ports_to_list(ports_l)]
    if len(content_l) > 0:
        return brcdapi_rest.send_request(session,
                                         'running/brocade-interface/fibrechannel',
                                         'PATCH',
                                         {'fibrechannel': content_l},
                                         fid)

    return brcdapi_util.GOOD_STATUS_OBJ  # If we get here, the port list, ports_l, was empty.


def disable_eport(session, fid, ports_l):
    """Disables E-Port mode for this port.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param ports_l: List of ports to enable or disable
    :type ports_l: tuple, list, str, int
    :return: The object returned from the API. If port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    content_l = [{'name': p, 'e-port-disable': 1} for p in ports_to_list(ports_l)]
    if len(content_l) > 0:
        return brcdapi_rest.send_request(session,
                                         'running/brocade-interface/fibrechannel',
                                         'PATCH',
                                         {'fibrechannel': content_l},
                                         fid)

    return brcdapi_util.GOOD_STATUS_OBJ  # If we get here, the port list, ports_l, was empty.


def e_port(session, fid, ports_l, mode):
    """Disables E-Port mode for the specified ports.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param ports_l: List of ports to enable or disable
    :type ports_l: tuple, list, str, int
    :param mode: If True, enable E-Port capability. If False, disable E-Port capability
    :type mode: bool
    :return: The object returned from the API. If port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    content_l = [{'name': p, 'e-port-disable': 0 if mode else 1} for p in ports_to_list(ports_l)]
    if len(content_l) > 0:
        return brcdapi_rest.send_request(session,
                                         'running/brocade-interface/fibrechannel',
                                         'PATCH',
                                         {'fibrechannel': content_l},
                                         fid)

    return brcdapi_util.GOOD_STATUS_OBJ  # If we get here, the port list, ports_l, was empty.


def n_port(session, fid, ports_l, mode):
    """Enable/disables port for use as N-Ports. This is only applicable to switches configured for Access Gateway mode.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param ports_l: List of ports to enable or disable
    :type ports_l: tuple, list, str, int
    :param mode: If True, enable N-Port capability. If False, disable N-Port capability
    :type mode: bool
    :param mode: If True, enable E-Port capability. If False, disable E-Port capability
    :type mode: bool
    :return: The object returned from the API. If port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    content_l = [{'name': p, 'n-port-enabled': 1 if mode else 0} for p in ports_to_list(ports_l)]
    if len(content_l) > 0:
        return brcdapi_rest.send_request(session,
                                         'running/brocade-interface/fibrechannel',
                                         'PATCH',
                                         {'fibrechannel': content_l},
                                         fid)

    return brcdapi_util.GOOD_STATUS_OBJ  # If we get here, the port list, ports_l, was empty.


def port_range_to_list(num_range):
    """Converts a CSV list of ports to ranges as text. Ports are converted to standard s/p notation and sorted by slot.
    The original order may not be preserved. For example: "5/0-2, 9, 2/6-5, 5/6-8" is returned as:
    ['5/0', '5/1', '5/2', '5/6', '5/7', '5/8', '0/9', '2/5', '2/6']

    :param num_range: List of numeric values, int or float
    :type num_range: str
    :return: List of str for ports as described above
    :rtype: list
    """
    rl = list()

    slot_d = dict()
    for buf in [b.replace(' ', '') if '/' in b else '0/' + b.replace(' ', '') for b in num_range.split(',')]:
        temp_l = buf.split('/')
        port_l = slot_d.get(temp_l[0])
        if port_l is None:
            port_l = list()
            slot_d.update({temp_l[0]: port_l})
        port_l.extend(gen_util.range_to_list(temp_l[1]))

    for slot, port_l in slot_d.items():
        rl.extend([slot + '/' + str(p) for p in port_l])

    return rl


def bind_addresses(session, fid, port_d, echo=False):
    """Binds port addresses to ports. Requires FOS 9.1 or higher.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Fabric ID
    :type fid: None, int
    :param port_d: Key is the port number. Value is the port address in hex (str).
    :type port_d: dict
    :param echo: If True, the list of ports for each move is echoed to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object for the first error encountered of the last request
    :rtype: dict
    """
    port_l = [{'name': k, 'operation-type': 'port-address-bind', 'user-port-address': v, 'auto-bind': False}
              for k, v in port_d.items()]
    obj = brcdapi_rest.send_request(session,
                                    'operations/port',
                                    'POST',
                                    {'port-operation-parameters': port_l},
                                    fid=fid)
    brcdapi_log.log('Error' if brcdapi_auth.is_error(obj) else 'Success' + ' binding addresses.', echo)

    return obj

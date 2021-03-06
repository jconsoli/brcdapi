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
:mod:`port.py` - Methods to configure ports.

    A collection of methods to perform common port functions. For example on how to use these functions, see
    api_examples/port_config.py. While most of the API requests are pretty straight forward and don't need a driver,
    there are a few things that need special attention and therefore have a library method:

    +-----------------------+---------------------------------------------------------------------------------------+
    | Method                | Description                                                                           |
    +=======================+=======================================================================================+
    | ports_to_list         | Converts ports to a list of ports. Many sources for ports return None, a single port, |
    |                       | or just the port (no slot on fixed port switches) and sometimes the port is an        |
    |                       | integer. The API always wants to see ports in 's/p' notation.                         |
    +-----------------------+---------------------------------------------------------------------------------------+
    | clear_stats           | Clear all statistical counters associated with a port or list of ports.               |
    +-----------------------+---------------------------------------------------------------------------------------+
    | default_port_config   | Disables and sets a list of FC ports to their factory default state.                  |
    +-----------------------+---------------------------------------------------------------------------------------+
    | enable_port           | Enables or disables a port or list of ports.                                          |                                                                   |
    +-----------------------+---------------------------------------------------------------------------------------+

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 3.0.0     | 27 Nov 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020 Jack Consoli'
__date__ = '27 Nov 2020'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.0'

import pprint
import collections
import brcdapi.util as brcdapi_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.pyfos_auth as pyfos_auth
import brcdapi.log as brcdapi_log

def ports_to_list(i_ports):
    """Converts ports to a list of ports. Many sources for ports return None, a single port, or just the port (no slot
    on fixed port switches) and sometimes the port is an integer. The API always wants to see ports in 's/p' notation.

    :param i_ports: Ports to be moved to the switch specified by to_fid
    :type i_ports: int, str, list, tuple
    :return: List of ports in s/p notation. If i_ports is None, an empty list is returned
    :rtype: dict
    """
    temp_l = list() if i_ports is None else [str(i_ports)] if isinstance(i_ports, (int, str)) else \
        [str(p) for p in i_ports]
    return [p if '/' in p else '0/' + p for p in temp_l]


def clear_stats(session, fid, i_ports, i_ge_ports):
    """Clear all statistical counters associated with a port or list of ports

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_ports: Port or list of FC ports for stats to be cleared on
    :type i_ports: list
    :param i_ge_ports: GE port or list of GE ports for stats to be cleared on
    :type i_ge_ports: list
    :return: brcdapi_rest status object
    :rtype: dict
    """
    pl = [{'name': p, 'reset-statistics': 1} for p in ports_to_list(i_ports) + ports_to_list(i_ge_ports)]
    if len(pl) > 0:
        content = {'fibrechannel-statistics': pl}
        return brcdapi_rest.send_request(session, 'brocade-interface/fibrechannel-statistics', 'PATCH', content, fid)
    return brcdapi_util.GOOD_STATUS_OBJ


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
# default_port_config_d['rate-limit-enabled'] = 0 Depricated
# default_port_config_d['non-dfe-enabled'] = 0 Depricated
default_port_config_d['trunk-port-enabled'] = 1  # Enabled
default_port_config_d['pod-license-state'] = 'released'  # The port is not reserved under a POD license
default_port_config_d['disable-reason'] = 'None'
default_port_config_d['port-peer-beacon-enabled'] = False  # Disabled
default_port_config_d['clean-address-enabled'] = False  # Disabled
default_port_config_d['congestion-signal-enabled'] = True  # Gen7 FPIN feature


def default_port_config(session, fid, i_ports):
    """Disables and sets a list of FC ports to their factory default state

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_ports: List of ports in the API format of s/p. For a fixed port switch for example, port 12 is '0/12'
    :type i_ports: tuple, list
    :return: The object returned from the API. If ports is an empty list, a made up good status is returned.
    :rtype: dict
    """
    global default_port_config_d

    ports = ports_to_list(i_ports)
    if len(ports) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    # Not all features are supported on all platforms. In most cases, even if you disable the unsupported feature, FOS
    # returns an error. To get around this, I read the port configuration and only add parameters to send to the switch
    # if they exist in the data returned from the switch

    # Read in the port configurations
    obj = brcdapi_rest.get_request(session, 'brocade-interface/fibrechannel', fid)
    if pyfos_auth.is_error(obj):
        brcdapi_log.log('Failed to read brocade-interface/fibrechannel for fid ' + str(fid), True)
        return obj
    # Put all the ports in a dictionary for easy lookup
    port_d = dict()
    for port in obj['fibrechannel']:
        port_d.update({port['name']: port})

    # Figure out what ports to change
    pl = list()
    for port in ports:
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
                                         'brocade-interface/fibrechannel',
                                         'PATCH',
                                         {'fibrechannel': pl},
                                         fid)
    else:
        return brcdapi_util.GOOD_STATUS_OBJ


def enable_port(session, fid, state, i_ports, echo=False):
    """Enables or disables a port or list of ports.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param state: True - enable ports. False - disable ports
    :type state: bool
    :param i_ports: List of ports to enable or disable
    :type i_ports: tuple, list
    :return: The object returned from the API. If ports is an empty list, a made up good status is returned.
    :rtype: dict
    """
    ports = ports_to_list(i_ports)
    if len(ports) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    # Now enable/disable the port(s)
    buf = 'En' if state else 'Dis'
    brcdapi_log.log(buf + 'abling ' + str(len(ports)) + ' ports.', echo)
    return brcdapi_rest.send_request(session,
                                     'brocade-interface/fibrechannel',
                                     'PATCH',
                                     {'fibrechannel': [{'name': p, 'is-enabled-state': state} for p in ports]},
                                     fid)

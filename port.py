"""
Copyright 2023, 2024, 2025, 2026 Jack Consoli.  All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may also obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.

The license is free for single customer use (internal applications). Use of this module in the production,
redistribution, or service delivery for commerce requires an additional license. Contact jack_consoli@yahoo.com for
details.

**Description**

    A collection of methods to perform common port functions. For examples on how to use these functions, see
    brocade-rest-api-examples/port_config.py. While most of the API requests are pretty straight forward and don't need,
    a driver there are a few things that need special attention and therefore have a library method.

**Public Methods & Data**

+-----------------------+-------------------------------------------------------------------------------------------+
| Method                | Description                                                                               |
+=======================+===========================================================================================+
| bind_addresses        | Binds port addresses to ports. Requires FOS 9.1 or higher.                                |
+-----------------------+-------------------------------------------------------------------------------------------+
| clear_stats           | Clear all statistical counters associated with a port or list of ports.                   |
+-----------------------+-------------------------------------------------------------------------------------------+
| decommission_port     | Decommissions a port or list of ports                                                     |
+-----------------------+-------------------------------------------------------------------------------------------+
| default_port_config   | Disables and sets an FC port or list of FC ports to their factory default state.          |
+-----------------------+-------------------------------------------------------------------------------------------+
| disable_port          | Disables a port or list of ports on a specific logical switch.                            |
+-----------------------+-------------------------------------------------------------------------------------------+
| enable_port           | Enables a port or list of ports on a specific logical switch.                             |
+-----------------------+-------------------------------------------------------------------------------------------+
| is_port               | Tests a value to determine if it is a valid port                                          |
+-----------------------+-------------------------------------------------------------------------------------------+
| ports_to_list         | Converts ports to a list of ports. Many sources for ports return None, a single port, or  |
|                       | just the port (no slot on fixed port switches) and sometimes the port is an integer. The  |
|                       | API always wants to see ports in 's/p' notation.                                          |
+-----------------------+-------------------------------------------------------------------------------------------+
| port_range_to_list    | Converts a CSV list of ports to ranges as text. Ports are converted to standard s/p       |
|                       | notation and sorted by slot. The original order may not be preserved. For example:        |
|                       | "5/0-2, 9, 2/6-5, 5/6-8" is returned as:                                                  |
|                       | ['5/0', '5/1', '5/2', '5/6', '5/7', '5/8', '0/9', '2/5', '2/6']                           |
+-----------------------+-------------------------------------------------------------------------------------------+
| release_pod           | Releases a POD license for a port or list of ports.                                       |
+-----------------------+-------------------------------------------------------------------------------------------+
| reserve_pod           | Reserves a POD license for a port or list of ports                                        |
+-----------------------+-------------------------------------------------------------------------------------------+
| sort_ports            | Sorts a list of ports. Sorting is by slot, port, ge port. This is useful because if       |
|                       | port_l is a list of ports in 's/p' notation, .sort() performs an ASCII sort which does    |
|                       | not return the desired results.                                                           |
+-----------------------+-------------------------------------------------------------------------------------------+
| user_name             | Assigns user-friendly names to ports.                                                     |
+-----------------------+-------------------------------------------------------------------------------------------+

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Documentation updates only.                                                           |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 20 Oct 2024   | Use brcdapi.gen_util.slot_port() to determine slot and port numbers.                  |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 27 Dec 2024   | Added unbind_addresses() and added portcfgdefault via CLI to default_port_config()    |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 04 Jan 2025   | Updated comments only.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.5     | 25 Aug 2025   | Updated email address in __email__ only.                                              |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.6     | 19 Oct 2025   | Updated comments only.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.7     | 20 Feb 2026   | Updated copyright notice.                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.8     | 01 Aug 2026   | Remove CLI wait. This is now done automatically in brcdapi.brcdapi_rest               |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2024, 2025, 2026 Jack Consoli'
__date__ = '01 Aug 2026'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.8'

import collections
import brcdapi.util as brcdapi_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as fos_auth
import brcdapi.fos_cli as fos_cli
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util

_MAX_CHECK = 3  # Port decommission maximum number of times to poll the switch for completion status
_WAIT = 1  # Port decommission wait time before each status poll check


#################################
#                               #
#     Utilitarian Functions     #
#                               #
#################################

def ports_to_list(i_port_l):
    """Converts ports to a list of ports in standard s/p notation. For fixed port switches, s = 0.

    :param i_port_l: Port or list of ports
    :type i_port_l: int, str, list, tuple
    :return: List of ports in s/p notation. If i_port_l is None, an empty list is returned
    :rtype: list
    """
    return [p if '/' in p else '0/' + p for p in [str(b) for b in gen_util.convert_to_list(i_port_l)]]


def sort_ports(i_port_l):
    """Sorts a list of ports in s/p notation. Duplicates are removed. Sorting is by slot, port, ge port.

    :param i_port_l: Port or list of ports in s/p notation
    :type i_port_l: int, str, list, tuple
    :return: List of sorted ports in s/p notation. If i_port_l is None, an empty list is returned
    :rtype: list
    """
    wd = dict()  # Working dictionary of slots which contains a dictionary of ports
    for port in ports_to_list(i_port_l):
        slot, port_num, ge_port = gen_util.slot_port(port)
        if slot not in wd:
            wd.update({slot: dict(p=list(), ge=list())})
        if isinstance(port_num, int):
            wd[slot]['p'].append(port_num)
        else:
            wd[slot]['ge'].append(ge_port)  # It's a ge port

    # Now sort them and create the return list
    rl, slot_l = list(), list(wd.keys())
    slot_l.sort()
    for slot in slot_l:
        slot_str = str(slot) + '/'
        for key in ('p', 'ge'):
            port_l = gen_util.remove_duplicates(wd[slot][key])
            port_l.sort()
            rl.extend([slot_str + str(port) for port in port_l])

    return rl


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

#################################
#                               #
#       FOS API Actions         #
#                               #
#################################


def clear_stats(session, fid, i_ports_l, echo=False, best=False):
    """Clear all statistical counters associated with a port or list of ports

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_ports_l: Port or list of FC ports for stats to be cleared on in s/p notation
    :type i_ports_l: list
    :return: brcdapi_rest status object
    :rtype: dict
    """
    r_obj = None

    port_l = ports_to_list(i_ports_l)
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    pl = [{'name': p, 'reset-statistics': 1} for p in port_l]
    content = {'fibrechannel-statistics': pl}
    obj = brcdapi_rest.send_request(
        session,
        'running/brocade-interface/fibrechannel-statistics',
        'PATCH',
        content,
        fid
    )
    if fos_auth.is_error(obj) and best and len(port_l) > 1:
        for port in port_l:
            p_obj = clear_stats(session, fid, [port], echo=echo, best=best)
            if fos_auth.is_error(p_obj):
                buf_l = [
                    'ERROR: clearing statistics for port: ' + port + '. FOS error message:',
                    fos_auth.formatted_error_msg(p_obj),
                    ]
                brcdapi_log.log(buf_l, echo=echo)
                if r_obj is None:
                    r_obj = p_obj

    return obj if r_obj is None else r_obj


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
default_port_config_d['octet-speed-combo'] = 1  # Auto-negotiated or fixed port speeds.
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


def default_port_config(session, fid, i_port_l, echo=False, best=False):
    """Disables and sets a list of FC ports to their factory default state

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_port_l: List of ports in the API format of s/p. For a fixed port switch for example, port 12 is '0/12'
    :type i_port_l: tuple, list, str, int
    :param echo: If True, echo error recovery detail to STD_OUT
    :type echo: bool
    :param best: Not used. It's not simple. Implementation date is TBD
    :type best: bool
    :return: The object returned from the API. If ports is an empty list, a made up good status is returned.
    :rtype: dict
    """
    global default_port_config_d

    port_l = ports_to_list(i_port_l)
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    check_port_d = dict()  # For faster lookup, this is a dictionary of ports in port_l
    for port in port_l:
        check_port_d.update({port: True})

    # Not all features are supported on all platforms. In most cases, even if you disable the unsupported feature, FOS
    # returns an error. To get around this, I read the port configuration and only add parameters to send to the switch
    # if they exist in the data returned from the switch

    # Read in the port configurations
    obj = brcdapi_rest.get_request(session, 'running/' + brcdapi_util.bifc_uri, fid)
    if fos_auth.is_error(obj):
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
        obj = brcdapi_rest.send_request(session,
                                        'running/' + brcdapi_util.bifc_uri,
                                        'PATCH',
                                        {'fibrechannel': pl},
                                        fid)
        if fos_auth.is_error(obj):
            # Until all port configurations to default are supported by the API, we'll get errors, so no echo.
            brcdapi_log.exception(fos_auth.formatted_error_msg(obj))

    # Unbind the port addresses if they were bound. This could have been written better. I forgot that although the
    # bound addresses and flag indicating they are bound are in running/brocade-interface/fibrechannel. Changing
    # it is in an operations branch. So I shoe horned this in.
    unbind_d, fc_l = dict(), obj.get('fibrechannel', list())
    for port_d in [d for d in fc_l if check_port_d.get(d['name'], False) and d.get('user-bound-enabled', False)]:
        unbind_d.update({port_d['name']: port_d['fcid-hex'][0:2] + port_d['fcid-hex'][4:]})
    if len(unbind_d) > 0:
        unbind_addresses(session, fid, unbind_d)

    # As of FOS v9.2, long distance settings could not be set or cleared via the API, so just do it via the CLI
    if len(port_l) > 0:
        for port in port_l:
            # FOS doesn't like the leading 0/ for port numbers on fixed port switches.
            response_l = fos_cli.send_command(session, fid, 'portcfgdefault ' + port.replace('0/', ''))
            # Not doing anything with the response_l. At least not yet anyway.

    return brcdapi_util.GOOD_STATUS_OBJ  # Since all defaults aren't supported by the API, anything else is too complex


def _port_enable_disable(session, fid, enable_flag, i_port_l, persistent=None, echo=False, best=False):
    """Enable or disable a port or list of ports.

    :param session: Session object returned from brcdapi.fos_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param enable_flag: True - enable ports. False - disable ports
    :type enable_flag: bool
    :param i_port_l: Port or list of ports to enable or disable
    :type i_port_l: tuple, list, str
    :param persistent: None: No change. True: set the persistent disable bit. False: clear the persistent disable bit
    :type persistent: None, bool
    :param echo: If True, echo error recovery detail to STD_OUT
    :type echo: bool
    :param best: If True, try one port at a time if there is a failure
    :type best: bool
    :return: The object returned from the API. If ports is an empty list, a made up good status is returned.
    :rtype: dict
    """
    r_obj = None

    port_l = ports_to_list(i_port_l)
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    # Now enable/disable the port(s)
    buf, enable_disable_buf = '', 'Enabling' if enable_flag else 'Disabling'
    pd = 0 if enable_flag else 1
    brcdapi_log.log(buf + enable_disable_buf + ' ' + str(len(port_l)) + ' ports.', echo)
    # FOS does not allow the disable bit to be altered when enabling the port. I could disable the port and alter the
    # persistent bit at the same time, but it's easier to always make two passes.
    process_l = [[{'name': p, 'is-enabled-state': enable_flag} for p in port_l]]
    if persistent is not None:
        process_l.insert(0, [{'name': p, 'persistent-disable': pd} for p in port_l])
    for content_d in process_l:
        obj = brcdapi_rest.send_request(
            session,
            'running/' + brcdapi_util.bifc_uri,
            'PATCH',
            {'fibrechannel': content_d},
            fid
        )
        if fos_auth.is_error(obj) and best and len(port_l) > 1:
            brcdapi_log.log('Attempting to ' + enable_disable_buf + ' one at a time.', echo)
            for port in port_l:
                p_obj = _port_enable_disable(
                    session,
                    fid,
                    enable_flag,
                    port,
                    persistent=persistent,
                    echo=echo,
                    best=best
                )
                if fos_auth.is_error(p_obj):
                    buf_l = [
                        'ERROR: ' + enable_disable_buf + ' port: ' + port + '. FOS error message:',
                        fos_auth.formatted_error_msg(p_obj),
                        ]
                    brcdapi_log.log(buf_l, echo=echo)
                    if r_obj is None:
                        r_obj = p_obj

    return obj if r_obj is None else r_obj


def enable_port(session, fid, i_port_l, persistent=None, echo=False, best=False):
    """Enables a port or list of ports on a specific logical switch.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_port_l: List of ports to enable or disable
    :type i_port_l: tuple, list, str, in
    :param persistent: None: No change. True: set the persistent disable bit. False: clear the persistent disable bit
    :type persistent: None, bool
    :param echo: If True, print activity to STD OUT
    :type echo: bool
    :param best: If True, try one port at a time if there is a failure
    :type best: bool
    :return: The object returned from the API. First fault is errors encountered. Good status if i_port_l is empty.
    :rtype: dict
    """
    return _port_enable_disable(session, fid, True, i_port_l, persistent=persistent, echo=echo, best=best)


def disable_port(session, fid, i_port_l, persistent=False, echo=False, best=False):
    """Disables a port or list of ports on a specific logical switch.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_port_l: List of ports to enable or disable
    :type i_port_l: tuple, list, str, in
    :param persistent: None: No change. True: set the persistent disable bit. False: clear the persistent disable bit
    :type persistent: None, bool
    :param echo: If True, echo error recovery detail to STD_OUT
    :type echo: bool
    :param best: If True, try one port at a time if there is a failure
    :type best: bool
    :return: The object returned from the API. If i_port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    return _port_enable_disable(session, fid, False, i_port_l, persistent=persistent, echo=echo, best=best)


def decommission_port(session, fid, i_port_l, port_type='port', persistent=False, echo=False, best=False):
    """Decommissions a port or list of ports.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_port_l: List of ports to enable or disable
    :type i_port_l: tuple, list, str, int
    :param port_type: 'port' or 'qsfp-port'
    :type port_type: str
    :param persistent: None: No change. True: set the persistent disable bit. False: clear the persistent disable bit
    :type persistent: None, bool
    :param echo: If True, echo error recovery detail to STD_OUT
    :type echo: bool
    :param best: If True, try one port at a time if there is a failure
    :type best: bool
    :return: The object returned from the API. If i_port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    global _MAX_CHECK, _WAIT

    r_obj = None

    port_l = ports_to_list(i_port_l)
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    # Now decommission the port(s)
    brcdapi_log.log('Decommissioning ' + str(len(port_l)) + ' ports.', echo)
    port_d_l = list()
    for port in port_l:
        port_d_l.append({'slot-port': port, 'port-decommission-type': port_type})
    # WARNING: As of 11 July 2022, the API Guide describes the internal data structure for an RPC call.
    obj = brcdapi_rest.operations_request(
        session,
        'operations/port-decommission',
        'POST',
        {'port-decommission-parameters': port_d_l},
        fid=fid
    )
    if fos_auth.is_error(obj) and best and len(port_d_l) > 1:
        buf_l = [
            'ERROR: Decommisioning ports ' + len(port_d_l) + '. FOS error is:',
            fos_auth.formatted_error_msg(obj),
            'Attempting one port at a time.'
        ]
        brcdapi_log.log(buf_l, echo)
        for port in port_l:
            p_obj = decommission_port(session, fid, [port_d], port_type, echo=echo, best=best)
            if fos_auth.is_error(p_obj):
                buf_l = [
                    'ERROR: Decommissioning port ' + port,
                    'FOS error is:',
                    fos_auth.formatted_error_msg(p_obj),
                ]
                brcdapi_log.log(buf_l, echo=echo)
                if r_obj is None:
                    r_obj = p_obj

    return obj if r_obj is None else r_obj


def reserve_pod(session, fid, i_ports_l, echo=False, best=False):
    """Reserves a POD license for a port or list of ports.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_ports_l: List of ports to enable or disable
    :type i_ports_l: tuple, list, str, int
    :param echo: If True, echo error recovery detail to STD_OUT
    :type echo: bool
    :param best: If True, try one port at a time if there is a failure
    :type best: bool
    :return: The object returned from the API. If i_port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    r_obj = None

    port_l = ports_to_list(i_ports_l)
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    content_l = [{'name': p, 'pod-license-state': 'reserved'} for p in port_l]
    obj = brcdapi_rest.send_request(
        session,
        'running/' + brcdapi_util.bifc_uri,
        'PATCH',
        {'fibrechannel': content_l},
        fid
    )
    if fos_auth.is_error(obj) and best and len(port_l) >1:
        buf_l = [
            'ERROR: Reserving ' + len(port_d_l) + ' ports. FOS error is:',
            fos_auth.formatted_error_msg(obj),
            'Attempting one port at a time.'
        ]
        brcdapi_log.log(buf_l, echo)
        for port in port_l:
            p_obj = reserve_pod(session, fid, [port], echo=echo, best=best)
            if fos_auth.is_error(p_obj):
                buf_l = [
                    'ERROR: Reserving port ' + port,
                    'FOS error is:',
                    fos_auth.formatted_error_msg(p_obj),
                    ]
                brcdapi_log.log(buf_l, echo=echo)
                if r_obj is None:
                    r_obj = p_obj

    return obj if r_obj is None else r_obj


def release_pod(session, fid, i_ports_l, echo=False, best=False):
    """Releases a POD license for a port or list of ports.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_ports_l: List of ports to enable or disable
    :type i_ports_l: tuple, list, str, int
    :return: The object returned from the API. If i_port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    r_obj = None

    port_l = ports_to_list(i_ports_l)
    if len(port_l) > 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    content_l = [{'name': p, 'pod-license-state': 'released'} for p in port_l]
    obj = brcdapi_rest.send_request(
        session,
        'running/' + brcdapi_util.bifc_uri,
        'PATCH',
        {'fibrechannel': content_l},
        fid
    )
    if fos_auth.is_error(obj) and best and len(port_l) > 1:
        buf_l = [
            'ERROR: Releasing POD for ' + len(port_d_l) + ' ports. FOS error is:',
            fos_auth.formatted_error_msg(obj),
            'Attempting one port at a time.'
        ]
        brcdapi_log.log(buf_l, echo)
        for port in port_l:
            p_obj = release_pod(session, fid, [port], echo=echo, best=best)
            if fos_auth.is_error(p_obj):
                buf_l = [
                    'ERROR: Releasing port ' + port,
                    'FOS error is:',
                    fos_auth.formatted_error_msg(p_obj),
                    ]
                brcdapi_log.log(buf_l, echo=echo)
                if r_obj is None:
                    r_obj = p_obj

    return obj if r_obj is None else r_obj


def disable_eport(session, fid, i_ports_l, echo=False, best=False):
    """Disables E-Port mode for this port.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_ports_l: List of ports to enable or disable
    :type i_ports_l: tuple, list, str, int
    :param echo: If True, echo error recovery detail to STD_OUT
    :type echo: bool
    :param best: If True, try one port at a time if there is a failure
    :type best: bool
    :return: The object returned from the API. If port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    r_obj = None

    port_l = ports_to_list(i_ports_l)
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    content_l = [{'name': p, 'e-port-disable': 1} for p in port_l]
    obj = brcdapi_rest.send_request(
        session,
        'running/' + brcdapi_util.bifc_uri,
        'PATCH',
        {'fibrechannel': content_l},
        fid
    )
    if fos_auth.is_error(obj) and best and len(port_l) > 1:
        buf_l = [
            'ERROR: Disabling' + len(port_l) + ' E-Ports. FOS error is:',
            fos_auth.formatted_error_msg(obj),
            'Attempting one port at a time.'
        ]
        brcdapi_log.log(buf_l, echo)
        for port in port_l:
            p_obj = reserve_pod(session, fid, [port], echo=echo, best=best)
            if fos_auth.is_error(p_obj):
                buf_l = [
                    'ERROR: Disabling E-Port ' + port,
                    'FOS error is:',
                    fos_auth.formatted_error_msg(p_obj),
                    ]
                brcdapi_log.log(buf_l, echo=echo)
                if r_obj is None:
                    r_obj = p_obj

    return obj if r_obj is None else r_obj


def e_port(session, fid, i_ports_l, mode, echo=False, best=False):
    """Sets E-Port mode for the specified ports.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_ports_l: List of ports to enable or disable
    :type i_ports_l: tuple, list, str, int
    :param mode: If True, enable E-Port capability. If False, disable E-Port capability
    :type mode: bool
    :param echo: If True, echo error recovery detail to STD_OUT
    :type echo: bool
    :param best: If True, try one port at a time if there is a failure
    :type best: bool
    :return: The object returned from the API. If port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    r_obj = None

    port_l = ports_to_list(i_ports_l)
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    content_l = [{'name': p, 'e-port-disable': 0 if mode else 1} for p in port_l]
    obj = brcdapi_rest.send_request(
        session,
        'running/' + brcdapi_util.bifc_uri,
        'PATCH',
        {'fibrechannel': content_l},
        fid
    )
    if fos_auth.is_error(obj) and best and len(port_l) > 1:
        buf_l = [
            'ERROR: Setting E-Port mode for ' + len(port_l) + ' ports. FOS error is:',
            fos_auth.formatted_error_msg(obj),
            'Attempting one port at a time.'
        ]
        brcdapi_log.log(buf_l, echo)
        for port in port_l:
            p_obj = e_port(session, fid, [port], mode, echo=echo, best=best)
            if fos_auth.is_error(p_obj):
                buf_l = [
                    'ERROR: Setting E-Port mode for port ' + port,
                    'FOS error is:',
                    fos_auth.formatted_error_msg(p_obj),
                    ]
                brcdapi_log.log(buf_l, echo=echo)
                if r_obj is None:
                    r_obj = p_obj

    return obj if r_obj is None else r_obj


def n_port(session, fid, i_ports_l, mode, echo=False, best=False):
    """Enable/disables port for use as N-Ports. This is only applicable to switches configured for Access Gateway mode.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number for switch with ports. Use None if switch is not VF enabled.
    :type fid: int
    :param i_ports_l: List of ports to enable or disable
    :type i_ports_l: tuple, list, str, int
    :param mode: If True, enable N-Port capability. If False, disable N-Port capability
    :type mode: bool
    :param mode: If True, enable E-Port capability. If False, disable E-Port capability
    :type mode: bool
    :param echo: If True, echo error recovery detail to STD_OUT
    :type echo: bool
    :param best: If True, try one port at a time if there is a failure
    :type best: bool
    :return: The object returned from the API. If port_l is an empty list, a made up good status is returned.
    :rtype: dict
    """
    r_obj = None

    port_l = ports_to_list(i_ports_l)
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    content_l = [{'name': p, 'n-port-enabled': 1 if mode else 0} for p in port_l]
    obj = brcdapi_rest.send_request(
        session,
        'running/' + brcdapi_util.bifc_uri,
        'PATCH',
        {'fibrechannel': content_l},
        fid
    )
    enable_mode = 'Enable' if mode else 'Disable'
    if fos_auth.is_error(obj) and best and len(port_l) > 1:
        buf_l = [
            'ERROR: ' + enable_mode + ' N-Port for ' + len(port_l) + ' ports. FOS error is:',
            fos_auth.formatted_error_msg(obj),
            'Attempting one port at a time.'
        ]
        brcdapi_log.log(buf_l, echo)
        for port in port_l:
            p_obj = n_port(session, fid, [port], mode, echo=echo, best=best)
            if fos_auth.is_error(p_obj):
                buf_l = [
                    'ERROR: Could not ' + enable_mode + ' N-Port mode for port ' + port,
                    'FOS error is:',
                    fos_auth.formatted_error_msg(p_obj),
                    ]
                brcdapi_log.log(buf_l, echo=echo)
                if r_obj is None:
                    r_obj = p_obj

    return obj if r_obj is None else r_obj


def bind_addresses(session, fid, port_d, echo=False, best=False):
    """Binds port addresses to ports. Requires FOS 9.1 or higher.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Fabric ID
    :type fid: None, int
    :param port_d: Key is the port number. Value is the port address in hex (str).
    :type port_d: dict
    :param echo: If True, echo error recovery detail to STD_OUT
    :type echo: bool
    :param best: If True, try one port at a time if there is a failure
    :type best: bool
    :return: brcdapi_rest status object for the first error encountered of the last request
    :rtype: dict
    """
    r_obj = None

    port_l = [
        {'name': k, 'operation-type': 'port-address-bind', 'user-port-address': v, 'auto-bind': False}
        for k, v in port_d.items()
    ]
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    obj = brcdapi_rest.send_request(
        session,
        'operations/port',
        'POST',
        {'port-operation-parameters': port_l},
        fid=fid
    )
    if fos_auth.is_error(obj)and best and len(port_l) > 1:
        brcdapi_log.log('Attempting to bind addresses one port at a time.', echo=echo)
        for port in port_l:
            p_obj = bind_addresses(session, fid, {port: port_d[port]}, echo=echo, best=best)
            if fos_auth.is_error(p_obj):
                buf_l = [
                    'ERROR: binding address for port: ' + port + '. FOS error message:',
                    fos_auth.formatted_error_msg(p_obj),
                    ]
                brcdapi_log.log(buf_l, echo=echo)
                if _r_obj is None:
                    r_obj = p_obj

    return obj if r_obj is None else r_obj


def unbind_addresses(session, fid, port_d, echo=False, best=False):
    """Unbinds port addresses. Requires FOS 9.1 or higher.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Fabric ID
    :type fid: None, int
    :param port_d: Key is the port number. Value is the port address in hex (str).
    :type port_d: dict
    :param echo: If True, echo error recovery detail to STD_OUT
    :type echo: bool
    :param best: If True, try one port at a time if there is a failure
    :type best: bool
    :return: brcdapi_rest status object for the first error encountered of the last request
    :rtype: dict
    """
    r_obj = None

    port_l = [{'name': k, 'operation-type': 'port-address-unbind', 'user-port-address': v}
              for k, v in port_d.items()]
    if len(port_l) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    obj = brcdapi_rest.send_request(
        session,
        'operations/port',
        'POST',
        {'port-operation-parameters': port_l},
        fid=fid
    )
    if fos_auth.is_error(obj) and best and len(port_l) > 1:
            for port in port_l:
                p_obj = unbind_addresses(session, fid, {port: port_d[port]}, echo=echo, best=best)
                if fos_auth.is_error(p_obj):
                    buf_l = [
                        'ERROR: un-binding address for port: ' + port + '. FOS error message:',
                        fos_auth.formatted_error_msg(p_obj),
                        ]
                    brcdapi_log.log(buf_l, echo=echo)
                    if _r_obj is None:
                        r_obj = p_obj

    return obj if r_obj is None else r_obj


def user_name(session, fid, port_d, echo=False, best=False):
    """Assigns user-friendly names to ports.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Fabric ID
    :type fid: None, int
    :param port_d: Key is the port number. Value is the port user-name.
    :type port_d: dict
    :param echo: If True, echo error recovery detail to STD_OUT
    :type echo: bool
    :param best: If True, try one port at a time if there is a failure
    :type best: bool
    :return: brcdapi_rest status object for the first error encountered of the last request
    :rtype: dict
    """
    r_obj = brcdapi_util.GOOD_STATUS_OBJ

    # Build the content
    content_l = list()
    for port, port_name in port_d.items():
        content_l.append({'name': port, 'user-friendly-name': port_name})

    # Send the name change request
    if len(content_l) > 0:
        r_obj = brcdapi_rest.send_request(
            session,
            'running/' + brcdapi_util.bifc_uri,
            'PATCH',
            {'fibrechannel': content_l},
            fid
        )

        # If there was an error, try setting the port names one at a time.
        if fos_auth.is_error(r_obj) and best and len(content_l) > 0:
            # Try naming the ports one at a time.
            for d in content_l:
                r_obj = brcdapi_rest.send_request(
                    session,
                    'running/' + brcdapi_util.bifc_uri,
                    'PATCH',
                    {'fibrechannel': [d]},
                    fid
                )

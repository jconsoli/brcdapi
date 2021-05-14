# Copyright 2020, 2021 Jack Consoli.  All rights reserved.
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
:mod:`zone.py` - Execute zoning operations.

**Description**

    The methods herein simplify zoning operations by building the proper content for the API request and inserting the
    proper method. For example, the caller can create a zones simply by passing a list of zone names and their members
    to create_zones(). The method create_zones() formats the content and method and then sends the request.

    These methods do not perform any validation. They are limited to packaging the content and determining the HTTP
    method to use. If you create a zone with non-existent aliases or mal-formed WWNs, it will package up what you told
    it to package up and send it to the switch. FOS will return an error. If you are interested in tools to validate
    zoning prior to sending them to the switch, or just to validate zoning and not send anything to the switch, see
    brcddb/apps/ind_zone.py and brcddb/apps/bulk_zone.py

    modify_zone() is a slight exception. This exception is articulated in the Important Notes section.

**Important Notes**

    The members of a zone cannot be modified. To effect modification of a zone, modify_zone() builds a local copy of the
    zone, makes the requested changes to the local copy, and then replaces the zone. This is a departure from all other
    methods herein in that:

    * There is no intellegence in any other method. They simply build the request content.
    * All other methods modify the object they are working on, they do not replace it.

    The members of an aliasj cannot be modified either. Since modifying an alias is unusual, I didn't bother writting a
    method equivelent to modify_zone(). For anyone who needs such a method, the same approach would need to be taken. If
    you need to modify an alias using these libraries, the only thing you can do is delete it and re-create it.

    The members of a zone configurations can be modified via the API.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.x.x     | 03 Jul 2019   | Experimental                                                                      |
    | 2.x.x     |               |                                                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.0     | 29 Jul 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 13 Feb 2021   | Removed the shebang line                                                          |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.2     | 14 May 2021   | Fixed some mutable list issues in modify_zone()                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020, 2021 Jack Consoli'
__date__ = '14 May 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.2'

import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.pyfos_auth as pyfos_auth
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util
from pprint import pprint  # Debug


def _is_error(obj, msg, echo):
    """Updates the log file if there was an error

    :param obj: Object returned from API
    :type obj: dict
    :param msg: Message to add to the log buffer
    :type msg: str
    :param echo: True - echo message to STD_OUT
    :type echo: bool
    :return: Version
    :rtype: str
    """
    if pyfos_auth.is_error(obj):
        brcdapi_log.log(msg, echo)
        brcdapi_log.exception(pyfos_auth.formatted_error_msg(obj), echo)
        return True
    return False


###################################################################
#
#                    Alias Methods
#
###################################################################
def create_aliases(session, fid, alias_list, echo=False):
    """Creates aliases.

    _sample_alias_list = [
        {'name': 'Target_0', 'members': ['50:0c:00:11:0d:bb:42:00']},
        {'name': 'Target_1', 'members': ['50:0c:00:11:0d:bb:42:01']},
    ]
    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number
    :type fid: int
    :param alias_list: List of dictionaries defining the aliases to create. See _sample_alias_list above.
    :type alias_list: list
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    build_alias_list = list()
    for alias_obj in alias_list:
        build_alias_list.append({'alias-name': alias_obj.get('name'),
                                 'member-entry': {'alias-entry-name': alias_obj.get('members')}})
    content = {'defined-configuration': {'alias': build_alias_list}}
    obj = brcdapi_rest.send_request(session, 'brocade-zone/defined-configuration', 'POST', content, fid)
    _is_error(obj, 'Failed to create aliases', echo)
    return obj


def del_aliases(session, fid, alias_list, echo=False):
    """Deletes aliases. Same as input parameters and return as create_aliases() but only 'name' is used in alias_list"""
    content = {'defined-configuration': {'alias': [{'alias-name': alias_obj.get('name')} for alias_obj in alias_list]}}
    obj = brcdapi_rest.send_request(session, 'brocade-zone/defined-configuration', 'DELETE', content, fid)
    _is_error(obj, 'Failed to delete alias', echo)
    return obj


###################################################################
#
#                    Zone Methods
#
###################################################################
def create_zones(session, fid, zone_list, echo=False):
    """Add zones to a fabric.

    _sample_zone_list = [
        {'name': 'T0_S0', 'type': 0, 'members': ['Target_0', 'Server_0']},
        {'name': 'T0_S1', 'type': 1, 'pmembers': ['Target_0'], 'members': ['Server_1', 'Server_2]},
    ]
    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number
    :type fid: int
    :param zone_list: List of dictionaries defining the zones to create. See _sample_zone_list for an example.
    :type zone_list: list
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    # Create the zones
    build_zone_list = list()
    for zone_obj in zone_list:
        d = dict()
        members = zone_obj.get('members')
        if isinstance(members, list):
            d.update({'entry-name': members})
        members = zone_obj.get('pmembers')
        if isinstance(members, list):
            d.update({'principal-entry-name': members})
        build_zone_list.append({'zone-name': zone_obj.get('name'), 'zone-type': zone_obj.get('type'),
                                'member-entry': d})
    content = {'defined-configuration': {'zone': build_zone_list}}
    obj = brcdapi_rest.send_request(session, 'brocade-zone/defined-configuration', 'POST', content, fid)
    _is_error(obj, 'Failed to create zones', echo)
    return obj


def del_zones(session, fid, zones, echo=False):
    """Deletes zones.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number
    :type fid: int
    :param zones: List of zone names to delete
    :type zones: list
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    # Delete the zones
    content = {'defined-configuration': {'zone': [{'zone-name': zone} for zone in zones]}}
    obj = brcdapi_rest.send_request(session, 'brocade-zone/defined-configuration', 'DELETE', content, fid)
    _is_error(obj, 'Failed to delete zone(s)', echo)
    return obj


def modify_zone(session, fid, zone, add_members, del_members, in_add_pmembers=None, in_del_pmembers=None, echo=False):
    """Adds and removes members from a zone.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number
    :type fid: int
    :param zone: Name of zone to be modified
    :type zone: str
    :param add_members: Members to add to the zone
    :type add_members: list
    :param del_members: Members to delete from the zone
    :type del_members: list
    :param add_pmembers: Principal members to add to zone. Only relevant for peer zones
    :type add_pmembers: list
    :param del_pmembers: Principal members to delete from a zone. Only relevant for peer zones
    :type del_pmembers: list
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    add_pmembers = list() if in_add_pmembers is None else in_add_pmembers
    del_pmembers = list() if in_del_pmembers is None else in_del_pmembers

    # This method reads the zone to change, makes the modifications in a local object, and PATCHes the change. I'm
    # assuming the type of zone could be changed but this method is just changing the membership. See "Important Notes"
    control = {
        'principal-entry-name': {'add_mem': add_pmembers, 'del_mem': del_pmembers},
        'entry-name': {'add_mem': add_members, 'del_mem': del_members},
    }
    # Read in the current defined zone
    obj = brcdapi_rest.get_request(session, 'brocade-zone/defined-configuration/zone/zone-name/' + zone, fid)
    if _is_error(obj, 'Failed reading zone ' + zone, echo):
        return obj

    # Modify the zone
    d = obj.get('zone')
    if d is None:
        return pyfos_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, brcdapi_util.HTTP_REASON_MAL_FORMED_OBJ,
                                       'Missing leaf "zone" in returned object for ' + zone)
    me = d.get('member-entry')
    if me is None:
        me = dict()  # I'm not sure what FOS returns if all the members were deleted so this is just to be safe
        d.update({'member-entry': me})
    for k, v in control.items():
        ml = me.get(k)
        if len(v.get('add_mem')) + len(v.get('del_mem')) > 0:
            if ml is None:
                ml = list()  # Just a safety net. Similar to 'member-entry' above.
                me.update({k: ml})  # If there are principle members to a non-peer zone, FOS returns an error
            for mem in v.get('add_mem'):
                ml.append(mem)
            for mem in v.get('del_mem'):
                try:
                    ml.remove(mem)
                except:
                    pyfos_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'Delete error',
                                            'Member ' + mem + ' does not exist')

    content = {'defined-configuration': obj}
    obj = brcdapi_rest.send_request(session, 'brocade-zone/defined-configuration', 'PATCH', content, fid)
    _is_error(obj, 'Failed to create zones', echo)
    return obj


###################################################################
#
#                    Zone Configuation Methods
#
###################################################################
def create_zonecfg(session, fid, zonecfg_name, zone_list, echo=False):
    """Add a zone configuration.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number
    :type fid: int
    :param zonecfg_name: Name of zone configuration
    :type zonecfg_name: str
    :param zone_list: List of zone names to add to the zonecfg.
    :type zone_list: list
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    # Create the zone configuration
    content = {
        'defined-configuration': {
            'cfg': [
                {
                    'cfg-name': zonecfg_name,
                    'member-zone': {
                        'zone-name': zone_list
                    }
                }
            ]
        }
    }
    obj = brcdapi_rest.send_request(session, 'brocade-zone/defined-configuration', 'POST', content, fid)
    _is_error(obj, 'Failed to create zone configuration ' + zonecfg_name, echo)
    return obj


def del_zonecfg(session, fid, zonecfg_name, echo=False):
    """Deletes a zone configuration

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number
    :type fid: int
    :param zonecfg_name: Name of zone configuration
    :type zonecfg_name: str
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    # Delete the zone configuration
    content = {
        'defined-configuration': {
            'cfg': [{'cfg-name': zonecfg_name, }]
        }
    }
    obj = brcdapi_rest.send_request(session, 'brocade-zone/defined-configuration', 'DELETE', content, fid)
    _is_error(obj, 'Failed to delete zone configuration ' + zonecfg_name, echo)
    return obj


def enable_zonecfg(session, check_sum, fid, zonecfg_name, echo=False):
    """Enables a zone configuration.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param check_sum: Zoning database checksum
    :type check_sum: int
    :param fid: Logical FID number
    :type fid: int
    :param zonecfg_name: Name of the zone configuration to enable
    :type zonecfg_name: str
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    content = {
        'effective-configuration': {
            'cfg-name': zonecfg_name,
            'checksum': check_sum,
            'cfg-action': 1
        }
    }
    obj = brcdapi_rest.send_request(session, 'brocade-zone/effective-configuration', 'PATCH', content, fid)
    _is_error(obj, 'Failed to enable zone configuration ' + zonecfg_name, echo)
    return obj


def disable_zonecfg(session, check_sum, fid, zonecfg_name, echo=False):
    """Enables a zone configuration.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param check_sum: Zoning database checksum
    :type check_sum: int
    :param fid: Logical FID number to be created. Valid FISs are 1-128. Will return an error if the FID already exists
    :type fid: int
    :param zonecfg_name: Name of the zone configuration to enable
    :type zonecfg_name: str
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    content = {
        'effective-configuration': {
            'checksum': check_sum,
            'cfg-action': 2
        }
    }
    obj = brcdapi_rest.send_request(session, 'brocade-zone/effective-configuration', 'PATCH', content, fid)
    _is_error(obj, 'Failed to enable zone configuration ' + zonecfg_name, echo)
    return obj


def _zonecfg_modify(session, fid, zonecfg_name, zone_list, method, echo=False):
    """Called by zonecfg_add() or zonecfg_remove(). All parameters the same except method

    :param method:  'DELETE' for remove or 'POST' to add members
    :type method: str
    """
    # Test
    content = {
        'defined-configuration': {
            'cfg': [
                {
                    'cfg-name': zonecfg_name,
                    'member-zone': {
                        'zone-name': zone_list
                    }
                }
            ]
        }
    }
    obj = brcdapi_rest.send_request(session, 'brocade-zone/defined-configuration', method, content, fid)
    _is_error(obj, 'Failed to create zone configuration ' + zonecfg_name, echo)
    return obj


def zonecfg_add(session, fid, zonecfg_name, zone_list, echo=False):
    """Adds members to a zone configuration.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number
    :type fid: int
    :param zonecfg_name: Name of zone configuration to be modified
    :type zonecfg_name: str
    :param zone_list: Members to add to the zone configuration
    :type zone_list: list
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    return _zonecfg_modify(session, fid, zonecfg_name, zone_list, 'POST', echo)


def zonecfg_remove(session, fid, zonecfg_name, zone_list, echo=False):
    """Removes members from a zone configuration.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number
    :type fid: int
    :param zonecfg_name: Name of zone configuration to be modified
    :type zonecfg_name: str
    :param zone_list: Members to remove from the zone configuration
    :type zone_list: list
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    return _zonecfg_modify(session, fid, zonecfg_name, zone_list, 'DELETE', echo)


###################################################################
#
#                    General Zoning Methods
#
###################################################################
def checksum(session, fid, echo=False):
    """Gets a zoning transaction checksum

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number for the fabric of interest
    :type fid: int
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: checksum
    :rtype: int, None
    :return: brcdapi_rest status object
    :rtype: dict
    """
    # Get the checksum - this is needed to save the configuration.
    obj = brcdapi_rest.get_request(session, 'brocade-zone/effective-configuration', fid)
    if _is_error(obj, 'Failed to get zone data from "brocade-zone/effective-configuration"', echo):
        return None, obj
    try:
        return obj.get('effective-configuration').get('checksum'), obj
    except:
        brcdapi_log.log('Failed to get checksum', echo)
        brcdapi_log.exception(pprint.pformat(obj, indent=4), echo)
        return None, pyfos_auth.create_error(brcdapi_util.HTTP_INT_SERVER_ERROR,
                                             brcdapi_util.HTTP_REASON_UNEXPECTED_RESP,
                                             'Missing effective-configuration/checksum')


def abort(session, fid, echo=False):
    """Aborts a zoning transaction

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number for the fabric of interest
    :type fid: int
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    obj = brcdapi_rest.send_request(session, 'brocade-zone/effective-configuration', 'PATCH',
                                    {'effective-configuration': {'cfg-action': 4}},
                                    fid)
    _is_error(obj, 'Abort failed', echo)
    return obj


def save(session, fid, check_sum, echo=False):
    """Saves the contents of the zoning transaction buffer

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number for the fabric of interest
    :type fid: int
    :param check_sum: Zoning checksum. See checksum()
    :type check_sum: int
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    content = {'effective-configuration': {
            'cfg-action': 1,
            'checksum': check_sum
        }
    }
    obj = brcdapi_rest.send_request(session, 'brocade-zone/effective-configuration', 'PATCH', content, fid)
    _is_error(obj, 'Failed to save zone configuration test_zone_cfg', echo)
    return obj


def default_zone(session, fid, access, echo=False):
    """Sets the default zone access method. Also saves pending changes

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number
    :type fid: int
    :param access: Access method. 0 - No Access, 1 - All Access
    :type access: int
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    content = {
        'effective-configuration': {
            'default-zone-access': access
        }
    }
    obj = brcdapi_rest.send_request(session, 'brocade-zone/effective-configuration', 'PATCH', content, fid)
    _is_error(obj, 'Failed to set the default zone access', echo)
    return obj


def clear_zone(session, fid, echo=False):
    """Clears the zone database

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number
    :type fid: int
    :param echo: If True, echoes any error messages to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object
    :rtype: dict
    """
    content = {
        'effective-configuration': {
            'cfg-action': 3
        }
    }
    obj = brcdapi_rest.send_request(session, 'brocade-zone/effective-configuration', 'PATCH', content, fid)
    _is_error(obj, 'Failed to set the default zone access', echo)
    return obj

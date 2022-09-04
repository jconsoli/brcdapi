# Copyright 2022 Jack Consoli.  All rights reserved.
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
:mod:`brcdapi.gen_util` - General purpose utility functions

**Description**

  Contains miscelleneous utility methods not specific to FOS

**Public Methods & Data**

  +-----------------------------+-----------------------------------------------------------------------------------|
  | Method or Data              | Description                                                                       |
  +=============================+===================================================================================+
  | ReGex & miscellaneous       | Compiled ReGex for filtered or converting common. Common multipliers and date     |
  |                             | conversion tables. Search for "ReGex matching" for details.                       |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | multiplier                  | Converts K, M, G, & T to an integer multiplier.                                   |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | month_to_num                | Using datetime is clumsy. These are easier. Speed is seldom the issue but it is   |
  |                             | faster.                                                                           |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | num_to_month                | Converts an integer representing a month to text.                                 |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | remove_duplicate_space      | Removes duplicate spaces from a string                                            |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | get_key_val                 | Spins through a list of keys separated by a '/' and returns the value associated  |
  |                             | with the last key.                                                                |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | sort_obj_num                | Sorts a list of dictionaries based on the value for a key. Value must be a        |
  |                             | number. Key may be in '/' format                                                  |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | sort_obj_str                | Sorts a list of dictionaries based on the value for a key or list of keys. Value  |
  |                             | must be a string.                                                                 |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | convert_to_list             | Converts an object to a list. Typically used to convert objects that may be None  |
  |                             | or list.                                                                          |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | remove_duplicates           | Removes duplicate entries in a list                                               |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | remove_none                 | Removes list entries whose value is None                                          |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | is_wwn                      | Validates that the wwn is a properly formed WWN                                   |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | is_valid_zone_name          | Checks to ensure that a zone object meets the FOS zone object naming convention   |
  |                             | rules                                                                             |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | slot_port                   | Seperate the slot and port number from a s/p port reference. Can also be used to  |
  |                             | validate s/p notation.                                                            |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | is_di                       | Determines if an str is a d,i pair (used in zoning)                               |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | remove_duplicate_space      | Removes duplicate spaces                                                          |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | str_to_num                  | Converts an str to an int if it can be represented as an int, otherwise float.    |
  |                             | 12.0 is returned as a float.                                                      |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | paren_content               | Returns the contents of a string within matching parenthesis. First character     |
  |                             | must be '('                                                                       |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | add_to_obj                  | Adds a key value pair to obj using '/' notation in the key. If the key already    |
  |                             | exists, it is overwritten.                                                        |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | get_struct_from_obj         | Returns a Python data structure for a key using / notation in obj with everything |
  |                             | not in the key, k, filtered out                                                   |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | resolve_multiplier          | Converts an str representation of a number. Supported conversions are k, m,, g,   |
  |                             | or t                                                                              |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | dBm_to_absolute             | Converts a number in dBm to it's value                                            |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | int_list_to_range           | Converts a list of integers to ranges as text.                                    |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | date_to_epoch               | Converts a date and time string to epoch time.                                    |
  +-----------------------------+-----------------------------------------------------------------------------------|
  | pad_string                  | Pads characters to a string to a fixed length. This is a cheesy way to support    |
  |                             | report formatting without textable                                                |
  +-----------------------------+-----------------------------------------------------------------------------------|

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.0.0     | 28 Apr 2022   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.1     | 22 Jun 2022   | Added valid_banner                                                                |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.2     | 25 Jul 2022   | Handled exception in remove_duplicates() when input list is a list of dict        |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.3     | 04 Sep 2022   | Added sort_obj_str()                                                              |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2022 Jack Consoli'
__date__ = '04 Sep 2022'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '1.0.3'

import re
import datetime
import brcdapi.log as brcdapi_log
import brcddb.classes.util as brcddb_class_util

_DEBUG_FICON = False  # Intended for lab use only. Few, if any, will use this to zone a FICON switch
_MAX_ZONE_NAME_LEN = 64
_MAX_LINE_COUNT = 20  # Maximum number of lines before inserting a space when generating CLI
_MAX_MEM = 3  # Maximum number of members to add to a zone object in a single FOS command (CLI)

# ReGex matching
non_decimal = re.compile(r'[^\d.]+')
decimal = re.compile(r'[\d.]+')  # Use: decimal.sub('', '1.4G') returns 'G'
zone_notes = re.compile(r'[~*#+^]')
ishex = re.compile(r'^[A-Fa-f0-9]*$')  # use: if ishex.match(hex_str) returns True if hex_str represents a hex number
valid_file_name = re.compile(r'\w[ -]')  # use: good_file_name = valid_file_name.sub('_', bad_file_name)
date_to_space = re.compile(r'[-/,+]')  # Used to convert special characters in data formats to a space
valid_banner = re.compile(r'[^A-Za-z0-9 .,*\-\"\']')  # Use: good_banner = gen_util.valid_banner.sub('-', buf)

multiplier = dict(k=1000, K=1000, m=1000000, M=1000000, g=1000000000, G=1000000000, t=1000000000000, T=1000000000000)
# Using datetime is clumsy. These are easier. Speed is seldom the issue but it is faster
month_to_num = dict(
    jan=1, january=1,
    feb=2, february=2,
    mar=3, march=3,
    apr=4, april=4,
    may=5,
    jun=6, june=6,
    jul=7, july=7,
    aug=8, august=8,
    sep=9, september=9,
    oct=10, october=10,
    nov=11, november=11,
    dec=12, december=12,
)
num_to_month = ('Inv', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
_tz_utc_offset = dict(est=-4, edt=-5, cst=-5, cdt=-6, pst=-6, pdt=-7)


def remove_duplicate_space(buf):
    """Removes duplicate spaces

    :param buf: Text to remove duplicate spaces from
    :type buf: str
    :return: Input text with duplicate spaces removed
    :rtype: str
    """
    buf = 'x' + buf
    temp_l = [buf[i] for i in range(1, len(buf)) if buf[i] != ' ' or (buf[i] == ' ' and buf[i-1] != ' ')]
    return ''.join(temp_l)


def get_key_val(obj, keys):
    """Spins through a list of keys separated by a '/' and returns the value associated with the last key.

    :param obj: Starting point in the object
    :type obj: dict, ProjectObj, FabricObj, SwitchObj, PortObj, ZoneCfgObj, ZoneObj, PortObj, LoginObj
    :param keys: Sting of keys to look through
    :type keys: str
    :return: Value associated with last key. None if not found
    :rtype: int, float, str, list, tuple, dict
    """
    if obj is None:
        return None  # Saves the calling method of having to determine they are working on a valid object
    if hasattr(obj, 'r_get') and callable(obj.r_get):
        return obj.r_get(keys)
    if not isinstance(obj, dict):
        brcdapi_log.exception('Object type, ' + str(type(obj)) + ', not a dict or brcddb object,', True)
        return None

    key_l = keys.split('/')
    if len(key_l) == 0:
        return None
    last_key = key_l[len(key_l)-1]
    v = obj
    for k in key_l:
        if isinstance(v, dict):
            v = v.get(k)
        elif k != last_key:
            brcdapi_log.exception('Object type, ' + str(type(v)) + ', for ' + k + ', in ' + keys +
                                  ' not a dict or brcddb object ', True)
            return None
    return v


def sort_obj_num(obj_list, key, r=False, h=False):
    """Sorts a list of dictionaries based on the value for a key. Value must be a number. Key may be in '/' format

    :param obj_list: List of dict or brcddb class objects
    :type obj_list: list, tuple
    :param key: Key for the value to be compared. '/' is supported.
    :type key: str
    :param r: Reverse flag. If True, sort in reverse order (largest in [0])
    :type r: bool
    :param h: True indicates that the value referenced by the key is a hex number
    :type h: bool
    :return: Sorted list of objects.
    :rtype: list
    """
    # count_dict: key is the count (value of dict item whose key is the input counter). Value is a list of port objects
    # whose counter matches this count
    count_dict = dict()

    for obj in obj_list:
        # Get the object to test against
        v = get_key_val(obj, key)
        if v is not None and h:
            v = int(v, 16)
        if isinstance(v, (int, float)):
            try:
                count_dict[v].append(obj)
            except KeyError:
                count_dict.update({v: [obj]})

    # Sort the keys, which are the actual counter values and return the sorted list of objects
    return [v for k in sorted(list(count_dict.keys()), reverse=r) for v in count_dict[k]]


def sort_obj_str(obj_list, key_list, r=False):
    """Sorts a list of dictionaries based on the value for a key or list of keys. Value must be a string

    :param obj_list: List of dict or brcddb class objects
    :type obj_list: list, tuple
    :param key_list: Key or list of keys. Sort order is based key_list[0], then [1] ... Keys may be in '/' format
    :type key_list: str, list, tuple, None
    :param r: Reverse flag. If True, sort in reverse order ('z' first, 'a' last)
    :type r: bool
    :return: Sorted list of objects.
    :rtype: list
    """
    # count_dict: key is the count (value of dict item whose key is the input counter). Value is a list of port objects
    # whose counter matches this count
    key_l = convert_to_list(key_list)
    while len(key_l) > 0:
        key, sort_d = key_l.pop(), dict()
        for obj in obj_list:
            # Get the object to test against
            v = get_key_val(obj, key)
            if isinstance(v, str):
                try:
                    sort_d[v].append(obj)
                except KeyError:
                    sort_d.update({v: [obj]})
        obj_list = [v for k in sorted(list(sort_d.keys()), reverse=r) for v in sort_d[k]]

    return obj_list


def convert_to_list(obj):
    """Converts an object to a list. Typically used to convert objects that may be None or list.

    obj         Return
    None        Empty list
    list        The same passed object, obj, is returned - NOT A COPY
    tuple       Tuple copied to a list
    All else    List with the passed obj as the only member

    :param obj: Object to be converted to list
    :type obj: list, tuple, dict, str, float, int
    :return: Converted list
    :rtype: list
    """
    if obj is None:
        return list()
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        return list() if len(obj.keys()) == 0 else [obj]
    if isinstance(obj, tuple):
        return list(obj)
    else:
        return [obj]


def remove_duplicates(obj_list):
    """Removes duplicate entries in a list

    :param obj_list: List of class objects.
    :type obj_list: list, tuple
    :return return_list: Input list less duplicates
    :rtype: list
    """
    seen = set()
    seen_add = seen.add  # seen.add isn't changing so making it local makes the next line more efficient
    try:
        return [obj for obj in obj_list if not (obj in seen or seen_add(obj))]
    except TypeError:
        return obj_list


def remove_none(obj_list):
    """Removes list entries whose value is None

    :param obj_list: List of items.
    :type obj_list: list, tuple
    :return return_list: Input list less items that were None
    :rtype: list
    """
    return [obj for obj in obj_list if obj is not None]


def is_wwn(wwn, full_check=True):
    """Validates that the wwn is a properly formed WWN

    :param wwn: WWN
    :type wwn: str
    :param full_check: When True, the first byte cannot be 0
    :return: True - wwn is a valid WWN, False - wwn is not a valid WWN
    :rtype: bool
    """
    if not isinstance(wwn, str) or len(wwn) != 23 or (wwn[0] == '0' and full_check):
        return False
    clean_wwn = list()
    for i in range(0, len(wwn)):
        if i in (2, 5, 8, 11, 14, 17, 20):
            if wwn[i] != ':':
                return False
        else:
            clean_wwn.append(wwn[i])

    return True if ishex.match(''.join(clean_wwn)) else False


def is_valid_zone_name(zone_name):
    """Checks to ensure that a zone object meets the FOS zone object naming convention rules

    :param zone_name: Zone, zone configuration, or alias name
    :type zone_name: str
    :return: True if zone object name is a valid format, otherwise False
    :rtype: bool
    """
    global _MAX_ZONE_NAME_LEN

    if zone_obj is None:
        return False
    if len(zone_obj) < 2 or len(zone_obj) > _MAX_ZONE_NAME_LEN:  # At least 1 character and less than or = 64
        return False
    if not re.match("^[A-Za-z0-9]*$", zone_obj[0:1]):  # Must begin with letter or number
        return False
    if not re.match("^[A-Za-z0-9_-]*$", zone_obj[1:]):  # Remaining characters must be letters, numbers, '_', or '-'
        return False
    return True


def slot_port(port):
    """Seperate the slot and port number from a s/p port reference. Can also be used to validate s/p notation.

    :param port: Port number in s/p notation
    :type port: str
    :return slot: Slot number. None if port is not in standard s/p notation
    :rtype slot: int, None
    :return port: Port number. None if port is not in standard s/p notation
    :rtype port: int, None
    """
    temp_l = port.split('/')
    if len(temp_l) == 1:
        temp_l.insert(0, '0')
    if len(temp_l) != 2:
        return None, None
    try:
        s = int(temp_l[0])
        p = int(temp_l[1])
    except (ValueError, IndexError):
        return None, None
    if s in range(0, 13) and p in range(0, 64):
        return s, p
    return None, None


def is_di(di):
    """Determines if an str is a d,i pair (used in zoning)

    :param di: Domain index pair as a "d,i" str
    :type di: str
    :return: True - di looks like a d,i pair. Otherwise False.
    :rtype: bool
    """
    try:
        temp = [int(x) for x in di.replace(' ', '').split(',')]
        return True if len(temp) == 2 else False
    except ValueError:
        return False


def remove_duplicate_space(buf):
    """Removes duplicate spaces

    :param buf: Text to remove duplicate spaces from
    :type buf: str
    :return: Input text with duplicate spaces removed
    :rtype: str
    """
    buf = 'x' + buf
    temp_l = [buf[i] for i in range(1, len(buf)) if buf[i] != ' ' or (buf[i] == ' ' and buf[i-1] != ' ')]
    return ''.join(temp_l)


def str_to_num(buf):
    """Converts an str to an int if it can be represented as an int, otherwise float. 12.0 is returned as a float.

    :param buf: Text to convert to float or int
    :type buf: str
    :return: str converted to number. If the input cannot be converted to a number, it is returned as passed in.
    :rtype: str, float, int
    """
    if isinstance(buf, str):
        if '.' in buf:
            try:
                num = float(buf)
            except ValueError:
                return buf
            else:
                return num
        else:
            try:
                num = int(buf)
            except ValueError:
                return buf
            else:
                return num
    return buf


def paren_content(buf, p_remove=False):
    """Returns the contents of a string within matching parenthesis. First character must be '('

    :param buf: String to find text within matching parenthesis
    :type buf: str
    :param p_remove: If True, remove the leading and trailing parenthesis
    :return p_text: Text within matching parenthesis
    :rtype p_text: str
    :return x_buf: Remainder of buf after matching parenthesis have been found
    :rtype x_buf: str
    """
    p_count, r_buf = 0, list()
    if len(buf) > 1 and buf[0] == '(':
        p_count += 1  # The first character must be (
        r_buf.append('(')
        for c in buf[1:]:
            r_buf.append(c)
            if c == '(':
                p_count += 1
            elif c == ')':
                p_count -= 1
                if p_count == 0:
                    break

    if p_count != 0:
        brcdapi_log.exception('Input string does not have matching parenthesis:\n' + buf, True)
        r_buf = list()
    remainder = '' if len(buf) - len(r_buf) < 1 else buf[len(r_buf):]
    if len(r_buf) > 2 and p_remove:
        r_buf.pop()
        r_buf.pop(0)

    return ''.join(r_buf), remainder


def add_to_obj(obj, k, v):
    """Adds a key value pair to obj using '/' notation in the key. If the key already exists, it is overwritten.

    :param obj: Dictionary the key value pair is to be added to
    :type obj: dict
    :param k: The key
    :type k: str
    :param v: Value associated with the key.
    :type v: int, str, list, dict
    """
    if not isinstance(k, str):
        brcdapi_log.exception('Invalid key. Expected type str, received type ' + str(type(k)), True)
        return
    key_list = k.split('/')
    if isinstance(obj, dict):
        if len(key_list) == 1:
            obj.update({k: v})
            return
        key = key_list.pop(0)
        d = obj.get(key)
        if d is None:
            d = dict()
            obj.update({key: d})
        add_to_obj(d, '/'.join(key_list), v)
    else:
        brcdapi_log.exception('Invalid object type. Expected dict, received ' + str(type(obj)), True)


def get_struct_from_obj(obj, k):
    """Returns a Python data structure for a key using / notation in obj with everything not in the key, k, filtered out

    :param obj: Dictionary the key is for
    :type obj: dict
    :param k: The key
    :type k: str
    :return: Filtered data structure. None is returned if the key was not found
    :rtype: int, str, list, dict, None
    """
    if not isinstance(k, str) or len(k) == 0:
        return None
    w_obj, kl = obj, k.split('/')
    while len(kl) > 0 and isinstance(w_obj, dict):
        w_obj = w_obj.get(kl.pop(0))

    return w_obj if len(kl) == 0 else None


def resolve_multiplier(val):
    """Converts an str representation of a number. Supported conversions are k, m,, g, or t

    :param val: Dictionary the key is for
    :type val: str
    :return: val as a number. Returns None if
    :rtype: float, None
    """
    if isinstance(val, str):
        try:
            mod_val = float(non_decimal.sub('', val))
            mult = decimal.sub('', val)
            if len(mult) > 0:
                return mod_val * multiplier[mult]
            return mod_val
        except ValueError:
            return None
    return val


def dBm_to_absolute(val, r=1):
    """Converts a number in dBm to it's value

    :param val: dBm value
    :type val: str, float
    :param r: Number of digits to the right of the decimal point to round off to
    :type r: int
    :return: val converted to it's absolute value. None if val cannot be converted to a float.
    :rtype: float, None
    """
    try:
        return round((10 ** (float(val)/10)) * 1000, r)
    except ValueError:
        pass
    return None


def int_list_to_range(num_list):
    """Converts a list of integers to ranges as text. For example: 0, 1, 2, 5, 6, 9 is returned as:

    0:  '0-2'
    1:  '5-6'
    2:  '9'

    :param num_list: List of numeric values, int or float
    :type num_list: list
    :return: List of str as described above
    :rtype: list
    """
    rl = list()
    range_l = list()
    for i in num_list:
        ri = len(range_l)
        if ri > 0 and i != range_l[ri-1] + 1:
            rl.append(str(range_l[0]) if ri == 1 else str(range_l[0]) + '-' + str(range_l[ri-1]))
            range_l = list()
        range_l.append(i)
    ri = len(range_l)
    if ri > 0:
        rl.append(str(range_l[0]) if ri == 1 else str(range_l[0]) + '-' + str(range_l[ri-1]))

    return rl


_fmt_map = {  # Used in date_to_epoch() to determine the indices for each date/time item. cm=True means month is text
    0: dict(y=2, m=0, d=1, t=3, z=4, cm=True),
    1: dict(y=2, m=1, d=0, t=3, z=4, cm=True),
    2: dict(y=2, m=0, d=1, t=3, z=4, cm=False),
    3: dict(y=2, m=1, d=0, t=3, z=4, cm=False),
    4: dict(y=5, m=1, d=2, t=3, z=4, cm=True),
    5: dict(y=4, m=1, d=2, t=3, cm=True),
    6: dict(y=0, m=1, d=2, t=3, cm=False),
    7: dict(y=3, m=0, d=1, t=2, cm=True),
    8: dict(y=0, m=1, d=2, t=3, cm=False),
}
for _v in _fmt_map.values():  # Add the minimum size the date/time array needs to be for each format
    _v.update(max=max([_i for _i in _v.values() if not isinstance(_i, bool)]))


def date_to_epoch(date_time, fmt=0, utc=False):
    """Converts a date and time string to epoch time. Originally intended for various date formats in FOS.

    WARNING: Time zone to UTC conversion not yet implemented.

    If .msec is not present in any of the below output it is treated as 0.
    +-------+-------------------------------------------+-----------------------------------------------------------+
    | fmt   | Sample                                    | Where Used                                                |
    +=======+===========================================+===========================================================+
    |  0    | Dec 31, 2021 hh:mm:ss.msec EDT (May or    |                                                           |
    |       | may not have the comma)                   |                                                           |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  1    | 31 Dec 2021 hh:mm:ss.msec EDT             |                                                           |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  2    | 12/31/2021 hh:mm:ss.msec EDT (or          |                                                           |
    |       | 12-31-2021 or 12 31 2021)                 |                                                           |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  3    | 31/12/2021 hh:mm:ss.msec EDT (or          |                                                           |
    |       | 31-12-2021 or 31 12 2021)                 |                                                           |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  4    | Tue Dec 31 hh:mm:ss.msec EDT 2021         | (CLI) date                                                |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  5    | Tue Dec  3 hh:mm:ss 2020                  | (CLI)clihistory                                           |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  6    | 2021/12/31-hh:mm:ss                       | (CLI)errdump                                              |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  7    | Dec 31 hh:mm:ss.msec 2021 EDT             | (OpenSSL) certs                                           |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  8    | 2021-12-31Thh:mm:ss+00:00                 | brocade-logging/error-log                                 |
    |       |                                           | brocade-logging/audit-log                                 |
    +-------+-------------------------------------------+-----------------------------------------------------------+

    :param date_time: Date and time
    :type date_time: str
    :param fmt: Format. See table above
    :type fmt: int
    :param utc: If True, convert time to UTC
    :type utc: bool
    :return: Epoch time. 0 If an error was encountered.
    :rtype: float
    """
    global month_to_num, _fmt_map

    # Get and validate the input string.
    ml = list()
    buf = date_time.replace('T', ' ') if fmt == 8 else date_time
    ts_l = remove_duplicate_space(date_to_space.sub(' ', buf)).split(' ')
    if fmt in _fmt_map:
        if len(ts_l) >= _fmt_map[fmt]['max']:
            d = _fmt_map[fmt]

            # Get the year
            buf = ts_l[d['y']]
            year = int(buf) if buf.isnumeric() else None
            if year is None or year < 1970:
                ml.append('Invalid year: ' + str(year))

            # Get the month
            buf = ts_l[d['m']]
            month = month_to_num.get(buf.lower()) if d['cm'] else int(buf) if buf.isnumeric() else None
            if month is None or month < 1 or month > 12:
                ml.append('Invalid month: ' + str(month))

            # Get the day
            buf = ts_l[d['d']]
            day = int(buf) if buf.isnumeric() else None
            if day is None or day < 1 or day > 31:
                ml.append('Invalid day: ' + str(day))

            # Get the time
            time_l = [int(buf) if buf.isnumeric() else None for buf in ts_l[d['t']].replace('.', ':').split(':')]
            if len(time_l) == 3:
                time_l.append(0)  # Fractional seconds are not always included with the time stamp
            if len(time_l) != 4 or None in time_l:
                ml.append('Invalid time: ' + ts_l[d['t']])
        else:
            ml.append('Invalid date/time stamp')
    else:
        ml.append('Invalid format (fmt): ' + str(fmt))

    if len(ml) > 0:
        ml.append('Unsupported format for: ' + date_time + ' Format, fmt, is: ' + str(fmt))
        brcdapi_log.exception(ml, True)
        return 0.0

    return datetime.datetime(year, month, day, time_l[0], time_l[1], time_l[2], time_l[3]).timestamp()


def pad_string(in_buf, pad_len, pad_char, append=False):
    """Pads characters to a string to a fixed length. This is a cheesy way to support report formatting without textable

    :param in_buf: The text string to pad
    :type in_buf: str
    :param pad_len: Total number of characters
    :type pad_len: int
    :param pad_char: Pad character. Must be a single character string.
    :type pad_char: str
    :param append: True: Append pad character to the end of the string. False: Prepend pad characters to the beginning
    :type append: bool
    """
    buf = '' if in_buf is None else in_buf
    x, pad_buf = pad_len-len(buf), ''
    for i in range(0, x):
        pad_buf += pad_char
    return buf + pad_buf if append else pad_buf + buf

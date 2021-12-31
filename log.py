# Copyright 2020, 2021 Jack Consoli.  All rights reserved.
#
# NOT BROADCOM SUPPORTED
#
# Licensed under the Apahche License, Version 2.0 (the "License");
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
:mod:`brcdapi.log` - Methods to create and manage logging content.

Automatically creates a log as soon as it is imported with a time stamp in the log file name if not already open.
Although the Python libraries automatically close all open file handles upon exit, there is a close_log() method to
flush and close the file. This is not only useful for traditional programmers who want a greater degree of program
control, but useful in conjunction with control programs such as Ansible whereby printing to STD_OUT needs to be
suppressed for all log messages except the final completion message.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 3.0.0     | 15 Jul 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1-5   | 17 Apr 2021   | Miscellaneous bug fixes and removed automatic log creation.                       |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.6     | 31 Dec 2021   | Improved comments. No functional changes.                                         |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020, 2021 Jack Consoli'
__date__ = '31 Dec 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.6'

import traceback
import datetime

_local_suppress_all = False
_log_obj = None  # Log file handle


def set_suppress_all():
    """Suppress all output except forced output. Useful with a playbook when only exit status is desired
    """
    global _local_suppress_all
    _local_suppress_all = True


def clear_suppress_all():
    """Clears suppress all flag. See set_suppress_all()
    """
    global _local_suppress_all
    _local_suppress_all = False


def is_prog_suppress_all():
    """Returns the status of the suppress all flag
    :return: Flag state for _local_suppress_all
    :rtype: bool
    """
    global _local_suppress_all
    return _local_suppress_all


def log(msg, echo=False, force=False):
    """Writes a message to the log file

    :param msg: Message to be printed to the log file
    :type msg: str, list
    :param echo: If True, also echoes message to STDOUT. Default is False
    :type echo: bool
    :param force: If True, ignores is_prog_suppress_all(). Useful for only echoing exit codes.
    :type force: bool
    :return: None
    """
    global _log_obj

    buf = '\n'.join(msg) if isinstance(msg, list) else msg
    if _log_obj is not None:
        _log_obj.write('\n# Log date: ' + datetime.datetime.now().strftime('%Y-%m-%d time: %H:%M:%S') + '\n')
        _log_obj.write(buf)
    if echo and (not is_prog_suppress_all() or force):
        print(buf)


def flush():
    """Flushes (writes) the contents of the log file cache to storage
    """
    global _log_obj

    if _log_obj is not None:
        _log_obj.flush()


def exception(msg, echo=False):
    """Prints the passed error message followed by the call stack returned from traceback

    :param msg: Message to be printed to the log file
    :type msg: str, list
    :param echo: If True, also echoes message to STDOUT
    :type echo: bool
    :return: None
    """
    msg_list = ['brcdapi library exception call. Traceback:']
    msg_list.extend([buf.rstrip() for buf in traceback.format_stack()])  # rstrip() because log() adds a line feed
    msg_list.extend(msg if isinstance(msg, list) else [msg])
    log(msg_list, echo)
    flush()


def close_log(msg=None, echo=False, force=False):
    """Closes the log file

    :param msg: Final message to be printed to the log file
    :type msg: str, None
    :param echo: If True, also echoes msg to STDOUT
    :type echo: bool
    :param force: If True, ignores is_prog_suppress_all(). Useful for only echoing exit codes.
    :type force: bool
    :return: None
    """
    global _log_obj

    if msg is not None:
        log(msg, echo, force)
    if _log_obj is not None:
        _log_obj.close()
        _log_obj = None


def open_log(folder=None):
    """Creates a log file. If the log file is already open, it is closed and a new one created.

    :param folder: Directory for the log file.
    :type folder: str, None
    """
    global _log_obj

    # Figure out what the log file name is
    file_name = '' if folder is None else folder + '/'
    file_name += 'Log_' + datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f') + '.txt'

    # Get a handle for the log file. If the log file is already open, close it
    if _log_obj is not None:
        close_log('Closing this file and opening a new log file: ' + file_name, False, False)
    _log_obj = open(file_name, 'w')

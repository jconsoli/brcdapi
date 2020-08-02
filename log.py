#!/usr/bin/python
# Copyright 2019, 2020 Jack Consoli.  All rights reserved.
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
flush and close the file. This is not only useful for tradditional programmers who want a greater degree of program
control, but useful in conjunction with control programs such as Ansible whereby printing to STD_OUT needs to be
suppressed for all log messages except the final completion message.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.x.x     | 03 Jul 2019   | Experimental                                                                      |
    | 2.x.x     |               |                                                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.0     | 15 Jul 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 02 Aug 2020   | PEP8 Clean up                                                                     |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020 Jack Consoli'
__date__ = '02 Aug 2020'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.1'

import traceback
import datetime
import time

# Get a file handle for logging. Note that the rest module may be opened by multiple modules so make sure there is only
# one log file opened just once.
try:
    if log_obj.closed:
        log_obj = open('Log_' + str(time.time()).replace('.', '_') + '.txt', 'w')
        log_obj.write('Previous log file closed. Opening new FOS Rest API Log\n')
except:
    log_obj = open('Log_' + str(time.time()).replace('.', '_') + '.txt', 'w')
    log_obj.write('New FOS Rest API Log\n')

_local_suppress_all = False


def set_suppress_all():
    """Supress all output except forced output. Useful with a playbook when only exit status is desired
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
    global log_obj

    log_obj.write('\n# Log date: ' + datetime.datetime.now().strftime('%Y-%m-%d time: %H:%M:%S') + '\n')
    buf = '\n'.join(msg) if isinstance(msg, list) else msg
    log_obj.write(buf)
    if echo and (not is_prog_suppress_all() or force):
        print(buf)


def exception(msg, echo=False):
    """Prints the passed error message followed by the call stack returned from traceback

    :param msg: Message to be printed to the log file
    :type msg: str, list
    :param echo: If True, also echoes message to STDOUT
    :type echo: bool
    :return: None
    """
    global log_obj

    msg_list = ['Exception call with msg:']
    msg_list.extend(msg if isinstance(msg, list) else [msg])
    msg_list.append('Traceback:')
    msg_list.extend([buf.rstrip() for buf in traceback.format_stack()])  # Log adds a line feed
    log(msg_list, echo)
    log_obj.flush()


def close_log(msg, echo=False, force=False):
    """Closes the log file

    :param msg: Final message to be printed to the log file
    :type msg: str
    :param echo: If True, also echoes msg to STDOUT
    :type echo: bool
    :param force: If True, ignores is_prog_suppress_all(). Useful for only echoing exit codes.
    :type force: bool
    :return: None
    """
    global log_obj

    log(msg, echo, force)
    log_obj.close()


def flush():
    """Flushes (writes) the contents of the log file cache to storage
    """
    global log_obj

    log_obj.flush()



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

Methods to login via SSH, send  commands, and logout.

**WARNING**

This module was written as an expedient to handle a few commands for things not yet supported via the API. It doesn't
do anything with prompts and doesn't perform any error checking.
**Public Methods & Data**

+-----------------------+-------------------------------------------------------------------------------------------+
| Method                | Description                                                                               |
+=======================+===========================================================================================+
| login                 | Performs an SSH login                                                                     |
+-----------------------+-------------------------------------------------------------------------------------------+
| logout                | Logout of an SSH session                                                                  |
+-----------------------+-------------------------------------------------------------------------------------------+
| send_command          | Sends a FOS command via an SSH connection to a FOS switch                                 |
+-----------------------+-------------------------------------------------------------------------------------------+
| parse_cli             | If cmd begins with 'fos_cli/' the remaining portion of cmd is returned. Otherwise, None   |
|                       | is returned.                                                                              |
+-----------------------+-------------------------------------------------------------------------------------------+
| cli_wait              | Introduces a sleep. This is necessary to allow the API and CLI to sync up                 |
+-----------------------+-------------------------------------------------------------------------------------------+
| verbose_debug         | Sets or clears verbose debugging                                                          |
+-----------------------+-------------------------------------------------------------------------------------------+

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | cli_wait()                                                       |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 06 Dec 2024   | Fixed SSH logout when no SSH login was performed. Limited to debug modes only.        |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 25 Aug 2025   | Added default_cli_wait_time()                                                         |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 19 Oct 2025   | Updated comments only.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.5     | 12 Jan 2026   | Removed unused import.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.6     | 20 Feb 2026   | Updated copyright notice.                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.7     | 01 Aug 2026   | Added 'ssh_last_sent' to session. Used to alleviate calling modules from having to    |
|           |               | keep track of when the last CLI command was sent.                                     |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2024, 2025, 2026 Jack Consoli'
__date__ = '01 Aug 2026'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.7'

import time
import paramiko
import brcdapi.log as brcdapi_log

_FOS_CLI = 'fos_cli/'
_FOS_CLI_LEN = len(_FOS_CLI)
_DEFAULT_TIMEOUT = 15  # Default timeout in seconds when setting up SSH session in login()
_DEFAULT_WAIT = 20  # Default number of seconds to sleep waiting for the CLI and API to sync up. IDK what this time
                    # should be. I discovered the need to do this while setting port configurations via the CLI.
                    # Measuring the required time would have taken additional time and expirimentation, so I just picked
                    # a number much greater than I ever had to wait.

_verbose_debug = False  # When True, prints data structures. Only useful for debugging.


def login(session, timeout=_DEFAULT_TIMEOUT, force=False):
    """Performs an SSH login

    :param session: Dictionary of the session returned by fos_auth.login().
    :type session: dict
    :param timeout: SSH timeout value
    :type timeout: int
    :param force: If True, try logging in regardless of whether the login failed previously
    :type force: bool
    :return err_msgs: List of error messages
    :rtype err_msgs: list
    """
    if session.get('debug', False):
        return list()
    if force:
        session['ssh_fault'] = False
    if session.get('ssh_fault', False):
        return list()  # An error message was posted when ssh_fault was set so no need to repeat the message
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.client.WarningPolicy())
    try:
        ssh.connect(session['ip_addr'], username=session['user_id'], password=session['user_pw'], timeout=timeout)
    except BaseException as e:
        session['ssh_login'], session['ssh-fault'] = None, True
        return ['Access denied', 'Unexpected FOS error', 'Error is: ' + str(type(e)) + ': ' + str(e)]
    shell = ssh.invoke_shell()
    shell.settimeout(timeout)
    session['ssh_login'] = ssh

    return list()


def logout(session):
    """Logout of an SSH session

    :param session: Dictionary of the session returned by fos_auth.login().
    :type session: dict
    :rtype: None
    """
    if isinstance(session, dict):
        if session.get('ssh_login') is not None:
            session['ssh_login'].close()
        session['ssh_login'], session['ssh_fault'] = None, False


def send_command(session, fid, cmd, fosexec=True):
    """Sends a FOS command via an SSH connection to a FOS switch

    :param session: Dictionary of the session returned by fos_auth.login().
    :type session: dict
    :param fid: Fabric ID of logical switch where commands are to be executed. Only used if fosexec is True.
    :type fid: int
    :param cmd: Command to send to switch
    :type cmd: str
    :return: Responses
    :rtype: list
    """
    global _verbose_debug

    response_l = list()
    if session.get('ssh_fault', False) or session.get('debug', False):
        return response_l  # An error for the login fault has already been presented so no need to do anything else.

    # Make sure there is an SSH login
    if session.get('ssh_login') is None:
        response_l = login(session)
        if len(response_l) > 0:
            response_l.extend([
                'ERROR: Could not login while attempting to process ' + cmd,
                'Check the log for details.'
            ])
            brcdapi_log.exception(response_l, echo=True)
            return response_l

    # Send the command
    full_cmd = 'fosexec --fid ' + str(fid) + ' -cmd "' + cmd + '"' if fosexec else cmd
    if _verbose_debug:
        brcdapi_log.log(['FOS CLI send_command() - send:', full_cmd], echo=True)
    try:
        stdin, stdout, stderr = session['ssh_login'].exec_command(full_cmd)
        session['ssh_last_sent'] = int(time.time())
    except BaseException as e:
        response_l = [
            'ERROR: SSH login failed. Error message is:',
            str(type(e)) + ': ' + str(e),
            'Check the log for details.'
        ]
        brcdapi_log.exception(response_l, echo=True)
        return response_l
    try:
        response_l = stdout.readlines()
    except BaseException as e:
        response_l = ['ERROR: Unexpected error while processing' + cmd + ':', str(type(e)) + ': ' + str(e)]
        brcdapi_log.exception(response_l, echo=True)
        return response_l
    if _verbose_debug:
        brcdapi_log.log(['FOS CLI send_command() - response:'] + [str(b) for b in response_l], echo=True)

    return response_l


def parse_cli(cmd):
    """If cmd begins with 'fos_cli/' the remaining portion of cmd is returned. Otherwise, None is returned

    :param cmd: Command to check
    :type cmd: str
    :return: If cmd begins with 'fos_cli/' the remaining portion of cmd is returned. Otherwise, None is returned
    :rtype: str, None
    """
    global _FOS_CLI, _FOS_CLI_LEN

    if len(cmd) >= _FOS_CLI_LEN and cmd[0: _FOS_CLI_LEN] == _FOS_CLI:
        return cmd[_FOS_CLI_LEN:]
    return None


def cli_wait(session, wait_time=_DEFAULT_WAIT):
    """Introduces a sleep. This is necessary to allow the API and CLI to sync up

    :param wait_time: Time in seconds to sleep. Only needed for commands that modify something. Use 0 for all else.
    :type wait_time: int
    :rtype: None
    """
    new_wait_time = wait_time - (int(time.time()) - session.get('ssh_last_sent', 0))
    if new_wait_time > 0:
        time.sleep(new_wait_time)


def default_cli_wait_time(wait_time=None):
    """Returns and sets the default wait time used to sync FOS command execution with the API

    :param wait_time: New default time in seconds. If None, no change. Float is converted to int.
    :type wait_time: float, int, None
    :return: Default wait time in seconds
    :rtype: int
    """
    global _DEFAULT_WAIT

    if isinstance(wait_time, (int, float)):
        _DEFAULT_WAIT = int(wait_time)

    return(_DEFAULT_WAIT)


def verbose_debug(state):
    """Sets or clears verbose debugging

    :param state: True - Enable verbose debug, False - disable verbose debug
    :type state: bool
    """
    global _verbose_debug

    _verbose_debug = state

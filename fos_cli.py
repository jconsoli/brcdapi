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
:mod:`fos_cli` - Methods to login via SSH, send  commands, and logout.

**WARNING**

This module was written as an expedient to send "portaddress --bind" commands to FOS for the switch_config.py
application found at https://github.com/jconsoli/applications. It does a simple login and sends commands. It doesn't
do anything with prompts and doesn't perform any error checking.

Search for brocade_fos_command.py at https://github.com/brocade for a more complete CLI module. It was not used here
because that module was written for Ansible. Rather than re-work it to fit my needs, I just took a quick and dirty way
out.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 3.0.0     | 31 Dec 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 13 Feb 2021   | Removed the shebang line                                                          |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.2     | 31 Dec 2021   | Improved comments. No functional changes.                                         |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.3     | 24 Oct 2022   | Improved error messaging.                                                         |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020, 2021 Jack Consoli'
__date__ = '24 Oct 2022'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.3'

import paramiko


def login(ip_addr, user_id, pw, timeout=15):
    """Performs an SSH and FOS login

    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param ip_addr: IP address
    :type ip_addr: str
    :param timeout: SSH timeout value
    :type timeout: int
    :return err_msgs: List of error messages
    :rtype err_msgs: list
    :return ssh: SSH session
    :rtype ssh: dict
    """
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.client.WarningPolicy())
    try:
        ssh.connect(ip_addr, username=user_id, password=pw, timeout=timeout)
    except BaseException as e:
        e_buf = str(e) if isinstance(e, (bytes, str)) else str(type(e))
        return ['Invalid name or password.', 'Error is: ' + e_buf], ssh
    shell = ssh.invoke_shell()
    shell.settimeout(timeout)

    return list(), ssh


def logout(ssh):
    """Logout of an SSH session

    :param ssh: ssh connection object returned from login()
    :type ssh: dict
    """
    ssh.close()

    return


def send_command(ssh, cmd):
    """Sends a FOS command via an SSH connection to a FOS switch

    :param ssh: ssh connection object returned from login()
    :type ssh: dict
    :param cmd: Command to send to switch
    :type cmd: str
    :return err_msgs: List of error messages
    :rtype err_msgs: list
    :return rl: List of responses
    :rtype rl: list
    """
    stdin, stdout, stderr = ssh.exec_command(cmd)

    return list(), stdout.readlines()

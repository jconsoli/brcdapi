# Copyright 2022, 2023 Jack Consoli.  All rights reserved.
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
:mod:`brcdapi.util.file` - File operation methods

Description::

    General purpose file operations.

Public Methods & Data::

    +-----------------------+---------------------------------------------------------------------------------------+
    | Method                | Description                                                                           |
    +=======================+=======================================================================================+
    | write_dump            | Converts a Python object to JSON and writes it to a file.                             |
    +-----------------------+---------------------------------------------------------------------------------------+
    | read_dump             | Reads in a file with JSON formatted data and loads into a Python object.              |
    +-----------------------+---------------------------------------------------------------------------------------+
    | read_directory        | Reads in the contents of a folder (directory) and return the list of files only (no   |
    |                       | directories) in that folder                                                           |
    +-----------------------+---------------------------------------------------------------------------------------+
    | read_file             | Reads a file, comments and blank lines optionally removed, and trailing white space   |
    |                       | removed into a list                                                                   |
    +-----------------------+---------------------------------------------------------------------------------------+
    | file_properties       | Reads the file properties into a dictionary                                           |
    +-----------------------+---------------------------------------------------------------------------------------+
    | read_full_directory   | Beginning with folder, reads the full content of a folder and puts all file names and |
    |                       | stats in a list of dict                                                               |
    +-----------------------+---------------------------------------------------------------------------------------+
    | full_file_name        | Checks to see if an extension is already in the file name and adds it if necessary    |
    +-----------------------+---------------------------------------------------------------------------------------+

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.0.0     | 28 Apr 2022   | Initial Launch. Previously in brcddb.                                             |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.1     | 22 Jun 2022   | Minor performance enhancements.                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.2     | 25 Jul 2022   | Fixed bug in read_full_directory() when skip_sys == True                          |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.3     | 14 Oct 2022   | Fixed missing new line when line end is just '\r' in file()                       |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.4     | 21 May 2023   | Updated comments and removed unused imports.                                      |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2022, 2023 Jack Consoli'
__date__ = '21 May 2023'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '1.0.4'

import json
import os


def write_dump(obj, file):
    """Converts a Python object to JSON and writes it to a file.

    :param obj: Dictionary to write to file
    :type obj: dict, list
    :param file: Name of file to write to
    :type file: str
    :rtype: None
    """
    with open(file, 'w') as f:
        f.write(json.dumps(obj, sort_keys=True))
    f.close()


def read_dump(file):
    """Reads in a file with JSON formatted data and loads into a Python object.

    :param file: Name of JSON file to read
    :type file: str
    :return: The JSON file converted to standard Python data types. None if an error was encountered
    :rtype: dict, list, None
    """
    f = open(file, 'r')
    obj = json.load(f)
    f.close()

    return obj


def read_directory(folder):
    """Reads in the contents of a folder (directory) and returns the list of files only (no directories) in that folder

    :param folder: Name of the folder
    :type folder: str
    :return: List of file names in the folder. List is empty if the folder doesn't exist
    :rtype: str
    """
    rl = list()
    if folder is not None:
        try:
            for file in os.listdir(folder):
                full_path = os.path.join(folder, file)
                try:
                    if os.path.isfile(full_path) and len(file) > 2 and file[0:2] != '~$':
                        rl.append(file)
                except PermissionError:
                    pass  # It's probably a system file
        except PermissionError:
            pass  # It's a protected folder. Usually system folders
        except FileNotFoundError:
            pass

    return rl


def read_director(folder):
    """To support old misspelled method name."""
    return read_directory(folder)


def read_file(file, remove_blank=True, rc=True):
    """Reads a file, comments and blank lines optionally removed, and trailing white space removed into a list

    :param file: Full path with name of file to read
    :type file: str
    :param remove_blank: If True, blank lines are removed
    :type remove_blank: bool
    :param rc: If True, remove anything beginning with # to the end of line
    :type rc: bool
    :return: List of file file contents.
    :rtype: list
    """
    # Apparently, Putty puts some weird characters in the file. Looks like there is a Python bug with the line below. I
    # get "NameError: name 'open' is not defined.
    # f = open(file, 'r', encoding='utf-8', errors='ignore')
    #  So I read as bytes, decoded using utf-8 and then had to ignore errors.
    f = open(file, 'rb')
    data = f.read().decode('utf-8', errors='ignore')
    f.close()

    # Every once in a while, a Windows file has just '\r' for the line end. I've never seen '\n\r' but just in case...
    content = data.replace('\r\n', '\n').replace('\n\r', '\n').replace('\r', '\n').split('\n')
    rl = [buf[:buf.find('#')].rstrip() if buf.find('#') >= 0 else buf.rstrip() for buf in content] if rc else content
    return [buf for buf in rl if len(buf) > 0] if remove_blank else rl


def file_properties(folder, file):
    """Reads the file properties and returns the following dictionary:

    +---------------+-------+---------------------------------------------------------------------------+
    | key           | type  | Description                                                               |
    +===============+=======+===========================================================================+
    | name          | str   | File name                                                                 |
    +---------------+-------+---------------------------------------------------------------------------+
    | folder        | str   | Folder name, relative to passed param folder.                             |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_atime      | float | Last access time (epoch time).                                            |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_ctime      | float | Creation time (epoch time)                                                |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_mtime      | float | Last time modified (epoch time)                                           |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_size       | int   | File size in bytes                                                        |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_mode       | int   | File mode, see os.stat()                                                  |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_ino        | int   | File mode, see os.stat()                                                  |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_dev        | int   | File mode, see os.stat()                                                  |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_nlink      | int   | File mode, see os.stat()                                                  |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_uid        | int   | File mode, see os.stat()                                                  |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_gid        | int   | See os.stat()                                                             |
    +---------------+-------+---------------------------------------------------------------------------+
    | permission_r  | bool  | True if file is readable. Same as os.R_OK. Not valid for Windows          |
    +---------------+-------+---------------------------------------------------------------------------+
    | permission_w  | bool  | True if file is writeable. Same as os.W_OK. Not valid for Windows         |
    +---------------+-------+---------------------------------------------------------------------------+
    | permission_x  | bool  | True if file is executable. Same as os.X_OK. Not valid for Windows        |
    +---------------+-------+---------------------------------------------------------------------------+
    | permission_f  | bool  | True if user has path access to file. Same as os.F_OK. Not valid for      |
    |               |       | Windows                                                                   |
    +---------------+-------+---------------------------------------------------------------------------+

    :param folder: Folder containing file
    :type folder: str
    :param file: Name of file to read
    :type file: str
    :return: List of file file contents.
    :rtype: list
    """
    stats = os.stat(os.path.join(folder, file))
    return dict(
        name=file,
        folder=folder,
        st_atime=stats.st_atime,
        st_ctime=stats.st_ctime,
        st_mtime=stats.st_mtime,
        st_size=stats.st_size,
        st_mode=stats.st_mode,
        st_ino=stats.st_ino,
        st_dev=stats.st_dev,
        st_nlink=stats.st_nlink,
        st_uid=stats.st_uid,
        st_gid=stats.st_gid,
        permission_r=os.access(file, os.R_OK),
        permission_w=os.access(file, os.W_OK),
        permission_x=os.access(file, os.X_OK),
        permission_f=os.access(file, os.F_OK)
    )


def read_full_directory(folder, skip_sys=False):
    """Beginning with folder, reads the full content of a folder and puts all file names and stats in a list of dict

    :param folder: Name of the directory to read
    :type folder: str
    :param skip_sys: If True, skip any file or folder that begins with '$' or '~'
    :param skip_sys: bool
    :return rl: List of properties dictionaries (as returned from file_properties) for each file as described above.
    :rtype rl: list
    """
    rl = list()
    try:
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path):
                if skip_sys and len(file) > 2 and file[0:2] == '~$':
                    continue
                rl.append(file_properties(folder, file))
            else:
                rl.extend(read_full_directory(full_path, skip_sys))
    except PermissionError:
        pass

    return rl


def full_file_name(file, extension, prefix=None):
    """Checks to see if an extension is already in the file name and adds it if necessary

    :param file: File name. If None, None is returned
    :type file: str, None
    :param extension: The file extension
    :type extension: str
    :param prefix: A prefix to add. Typically a folder name. If a folder, don't forget the last character must be '/'
    :type prefix: None, str
    :return: File name with the extension and prefix added
    :rtype: str
    """
    if file is None:
        return None
    x = len(extension)
    p = '' if prefix is None else prefix
    return p + file + extension if len(file) < x or file[len(file)-x:].lower() != extension.lower() else p + file

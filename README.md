# brcdapi

The brcdbapi library is intended for programmers who will be scripting in Python to interface directly to the RESTConf API in FOS in support of SAN automation applications. Since JSON is used, FOS must be at v8.2.1c or higher.

* Performs low level error checking and re-transmit of requests when applicable
* Converts empty lists to an empty list.
* Converts no change errors to an empty response
* Common log function
* Automatically adds headers
* Builds a full URI, automatically adding a vf-id if necessary
* Debug mode that will pprint all transactions
* Debug mode that recards and plays back GET requests
* Single interface to the API

A simple copy of this folder to you Python Library Lib folder is dequate. In Unix environments, remember to set the executable attribute

**api_examples**

There are two libraries, brcdapi and brddb.  The modules in the api_examples folder use
the brcdapi library but not the brcddb library. The brcdapi library is a driver. The
brcddb library is a hierarchical database. For example, clearing port statistics is a
simple matter of reading all the ports in a switch, clearing the statistics counter, and
writing it back to the switch so only the brcdapi library is required. Performing a zone
analysis requires the ability to relate data from multiple requests so zone analysis is
part of the report module found in the applications folder.

The modules in the api_examples folder were originally intended as programming examples
only but since many automated actions don’t require sophisticated programming, a user
interface was added to most of the modules. Since they were intended as programming
examples, a verbose coding style was used with more than usual comments.

**Common Options For All Modules**

Help

-h  Prints a brief description of what the module does and a list of module options.

Debug

-d  Prints all data structures, pprint, sent to and received from the switch API
    interface to the console and log.

Logging

Rather than use print statements, all of the modules in api_examples use the
logging utility in brcdapi.log. The log utility has a feature that optionally
echoes, print, to the console. Creating a log file is optional as well. All
modules have the following options:

-log  Use to specify the folder where the log file is to be placed.

-nl   Use this to disable logging (do not create a log file).

-sup  This option is available in the applications modules and some of the
      api_examples. When set, print to console is disabled. This is useful
      for batch processing.

For programmers

Each module has a _DEBUG variable. When set True, instead of obtaining
module input from the command line, input is taken from _DEBUG_xxx variables
where “xxx” is the option. This allows you to execute modules from a
development environment such as PyCharm.

**api_examples Module Specific**

**api_get_examples**

Although this does have a user interface, it is primarily intended as
examples for programmers. Edit this file and search for chassis_rest_data
and fid_rest_data to change the requests. When used stand alone, it is
typically used with the –d option.

py api_get_examples.py –ip xxx.xxx.xxx.xxx –id admin –pw password –s self –fid 128 -d

**login_test**

Performs a simple login and logout. Typically used to validate the ability
to login and out via a RESTConf API connection. Also used as a programmers
example on how to login and out.

py login_test.py –ip xxx.xxx.xxx.xxx –id admin –pw password –s self

**maps_clear**

Clears the MAPS dashboard.

py maps_clear.py –ip xxx.xxx.xxx.xxx –id admin –pw password –s self –fid 128

**port_config**

Intended as a programmer’s example on how to configure port attributes.
Editing the module is required to modify port configuration settings.

py port_config.py –ip xxx.xxx.xxx.xxx –id admin –pw password –s self –fid 128

**port_enable_all**

Enables all ports in a logical switch.

py port_enable_all.py –ip xxx.xxx.xxx.xxx –id admin –pw password –s self –fid 128

**set_port_default_all**

Sets all ports in a logical switch to the default configuration.

py set_port_default_all.py –ip xxx.xxx.xxx.xxx –id admin –pw password –s self –fid 128

**stats_clear**

Clear statistics for all ports in a logical switch.

py stats_clear.py –ip xxx.xxx.xxx.xxx –id admin –pw password –s self –fid 128


**stats_to_db**

Although there is a user interface, stats_to_db is intended as a programmer’s
example for customers who will not be using the Kafka streaming services of
SANnav to capture statistics and add them to their own database.  The
database add method, _db_add(), just prints a message to the log. This is
where you would add your own hook to a database.

Use applications/stats_to_db_app to for the same purpose but to capture
statistics from multiple switches. Use applications/stats_c and
applications/stats_g to capture and graph port statistics to an Excel
Woorkbook.

**switch_create**

Can be used as a stand-alone module to create logical switches. Use
applications/switch_config to create switches defined in an Excel Workbook.

To many options to list them all in an example. Use the –h option.

py switch_create.py –h

**switch_delete**

Deletes a logical switch. Configures all ports in the specified logical
switch to the default configuration, moves those ports to the default logical
switch, and deletes the specified logical switch.

py switch_delete.py –ip xxx.xxx.xxx.xxx –id admin –pw password –s self –fid 10

**zone_config**

No user interface. This is a programmer’s example only to illustrate how to
add, delete, or modify aliases, zones, and zone configurations.
 

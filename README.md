# brcdapi

Consoli Solutions, LLC
jack@consoli-solutions.com
jack_consoli@yahoo.com

**Update 25 August 2025**

* Error messaging improvements

**Update 20 Oct 2024**

Primary changes were to support the new chassis and report pages.

**Updates 6 March 2024**

* Miscellaneous bug fixes
* Improved error messaging
* Updated comments

**Updates 04 Aug 2023**

* Added support for URIs added in FOS 9.2.0
* Re-launched as Consoli Solutions

**Updates 01 Jan 2023**

* Added ability to bind addresses in switch.py
* Added methods to reserve and release POD licenses in switch_config.py and port.py

**Updates: 7 Aug 2021**

* util.py - Clean up mask_ip_addr()

**Updates 14 Nov 2021**

* Deprecated pyfos_auth - previously only used in name only.
* Added method, setup_debug(), to brcdapi_rest.py to modify debug varriables programatically

**Updated 31 Dec 2021**

* Several comments and user messaging improved
* Replaced all bare exception clauses with explicit exceptions

**Updated 28 Apr 2022**

* Added support for new URIs in FOS 9.1
* Moved some generic libraries from brcddb here

**Description**

The brcdbapi library is a driver for the FOS RESTConf API. It is intended for programmers who will be scripting in Python to interface directly to the RESTConf API in FOS in support of SAN automation applications. Since JSON is used, FOS must be at v8.2.1c or higher.

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

See api_examples for examples on how to use this library.

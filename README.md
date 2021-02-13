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

Updates

13 Feb 2021

Primarily a clean up release. Some minor bug fixes and removed shebang lines from library methods.

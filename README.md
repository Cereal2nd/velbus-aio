![Python checks](https://github.com/Cereal2nd/velbus-aio/actions/workflows/main.yml/badge.svg)
![CodeQL](https://github.com/Cereal2nd/velbus-aio/workflows/CodeQL/badge.svg)

# velbus-aio

Velbus Asyncio, a library to support the [Velbus](https://www.velbus.eu/) home automation system.

This Lib is a rewrite in python3 with asyncio of the [python-velbus](https://github.com/thomasdelaet/python-velbus/) module.
Part of the code from the above lib is reused.
Its also build on top of the [openHab velbus protocol description](https://github.com/StefCoene/moduleprotocol).

The latest version of the library is published as a python package on [pypi](https://pypi.org/project/velbus-aio/)

# Supported connections:

| Type          | Example                 | Description                                                                             |
| ------------- | ----------------------- | --------------------------------------------------------------------------------------- |
| serial        | /dev/ttyACME0           | a serial device                                                                         |
| ip:port       | 192.168.1.9:1234        | An ip adress + tcp port combination, used in combination with any velbus => tcp gateway |
| tls://ip:port | tls://192.168.1.9:12345 | A connection to [Signum](https://www.velbus.eu/products/view/?id=458140)                |

# Develop Installation

1. Clone the repo
   - git clone --recurse-submodules https://github.com/Cereal2nd/velbus-aio
2. cd into the cloned repo
   - cd velbus-aio
3. create and activate a virtual enviroment
   - python3 -m venv venv
   - source venv/bin/activate
4. install the module
   - python setup.py develop
5. define the connection parameters
   - modify examples/load_modules.py
6. run the example
   - python examples/load_modules.py

![Python package](https://github.com/Cereal2nd/velbus-aio/workflows/Python%20package/badge.svg)
![CodeQL](https://github.com/Cereal2nd/velbus-aio/workflows/CodeQL/badge.svg)

# velbus-aio

Velbus Asyncio

This Lib is a rewrite in python3 with asyncio from https://github.com/thomasdelaet/python-velbus/
Part of the code from the above lib is reused.

# How to test

- clone the repo (with the --recursive parameter)
- cd into the repo
- run: python3 -m venv venv
- run: source venv/bin/activate
- run: python setup.py develop
- modify examples/scan.php to set the connection params
- run: python examples/scan.py

import sys

from setuptools import setup

if sys.version_info < (3, 7):
    sys.exit("Sorry, Python < 3.7 is not supported")

setup(
    name="velbus-aio",
    version="2021.8.11",
    url="https://github.com/Cereal2nd/velbus-aio",
    license="MIT",
    author="Maikel Punie",
    install_requires=["pyserial-asyncio"],
    author_email="maikel.punie@gmail.com",
    packages=["velbusaio", "velbusaio.messages"],
    include_package_data=True,
    platforms="any",
)

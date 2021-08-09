from setuptools import setup

setup(
    name="velbus-aio",
    version="2021.8.5",
    url="https://github.com/Cereal2nd/velbus-aio",
    license="MIT",
    author="Maikel Punie",
    install_requires=["pyserial-asyncio"],
    author_email="maikel.punie@gmail.com",
    packages=["velbusaio", "velbusaio.messages"],
    platforms="any",
)

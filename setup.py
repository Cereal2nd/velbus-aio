from setuptools import setup

setup(
    name="velbus-aio",
    version="2021.8.7",
    url="https://github.com/Cereal2nd/velbus-aio",
    license="MIT",
    author="Maikel Punie",
    install_requires=["pyserial-asyncio"],
    author_email="maikel.punie@gmail.com",
    packages=["velbusaio", "velbusaio.messages"],
    include_package_data=True,
    platforms="any",
)

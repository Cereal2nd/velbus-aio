from setuptools import find_packages, setup

PACKAGES = find_packages(exclude=["tests", "tests.*"])

setup(
    name="velbus-aio",
    version="2021.9.4",
    url="https://github.com/Cereal2nd/velbus-aio",
    license="MIT",
    author="Maikel Punie",
    install_requires=[
        'pyserial==3.5.0',
        'pyserial-asyncio>=0.5',
        'async_timeout>=3.0.1',
        'loguru>=0.5.3,<0.6',
        'backoff>=1.10.0,<1.11'
    ],
    author_email="maikel.punie@gmail.com",
    packages=PACKAGES,
    include_package_data=True,
    platforms="any",
    python_requires="~=3.7",
    test_suite="tests",
)

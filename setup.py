"""Setup of the package."""
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyKeyAtome",
    version="2.1.2",
    license="MIT",
    author="jugla",
    author_email="jugla@users.github.com",
    description="Get your energy consumption from Atome Linky device",
    long_description=long_description,
    url="http://github.com/jugla/pyKeyAtome/",
    packages=setuptools.find_packages(include=["pykeyatome"]),
    setup_requires=["requests", "setuptools"],
    install_requires=["requests", "fake_useragent", "simplejson"],
    entry_points={"console_scripts": ["pykeyatome = pykeyatome.__main__:main"]},
)

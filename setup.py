"""Cambios setup file."""

from setuptools import find_packages, setup

setup(
    name="cambios",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    install_requires=[
        "flask",
        "sqlalchemy",
        "alembic",
        # other dependencies
    ],
    # other setup options
)

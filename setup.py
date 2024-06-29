"""ATCApp setup file."""

from setuptools import find_packages, setup  # type: ignore[import-untyped]

setup(
    name="atcapp",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    install_requires=[
        "flask",
        "flask-admin",
        "alembic",
        "firebase-admin",
        "pdfplumber",
        "pymysql",
        "pytz",
        # other dependencies
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-mock",
            "pytest-cov",
            "mypy",
            "ruff",
            "pathspec",
            "types-pytz",
        ],
    },  # other setup options
)

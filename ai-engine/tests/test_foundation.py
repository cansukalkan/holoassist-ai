"""Check distribution installation and supported interpreter contract."""

import sys
from importlib.metadata import metadata, version

import holoassist
from packaging.specifiers import SpecifierSet


def test_installed_distribution_matches_package():
    assert version("holoassist-ai") == holoassist.__version__


def test_supported_python_contract():
    assert sys.version_info[:2] == (3, 12)
    assert SpecifierSet(metadata("holoassist-ai")["Requires-Python"]) == SpecifierSet(
        ">=3.12,<3.13"
    )

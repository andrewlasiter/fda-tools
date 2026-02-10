#!/usr/bin/env python3
"""
Shared FDA HTTP utilities — browser headers and session factory.

Provides consistent HTTP configuration across all FDA pipeline scripts
(predicate_extractor.py, batchfetch.py, fda_api_client.py).

Usage:
    from fda_http import create_session, FDA_HEADERS
"""

import requests

try:
    from version import PLUGIN_VERSION
except Exception:
    PLUGIN_VERSION = "0.0.0"

# Browser-like headers that work reliably with FDA servers
FDA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# openFDA API-specific headers
OPENFDA_HEADERS = {
    'User-Agent': f'Mozilla/5.0 (FDA-Plugin/{PLUGIN_VERSION})',
    'Accept': 'application/json',
}


def create_session(api_mode=False):
    """Create a requests.Session with appropriate FDA headers.

    Args:
        api_mode: If True, use openFDA API headers instead of browser headers.

    Returns:
        requests.Session configured with appropriate headers.
    """
    session = requests.Session()
    headers = OPENFDA_HEADERS if api_mode else FDA_HEADERS
    session.headers.update(headers)
    return session

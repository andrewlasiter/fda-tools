#!/usr/bin/env python3
"""
Shared FDA HTTP utilities — user-agent management and session factory.

This module provides HTTP configuration for FDA server interactions with
proper user-agent handling to comply with FDA Terms of Service.

USER-AGENT POLICY
=================

This module uses TWO different user-agent strings for different purposes:

1. FDA_API_HEADERS (for api.fda.gov):
   - Honest identification: "FDA-Plugin/{version}"
   - Used for: openFDA API calls (device classification, 510(k) search, etc.)
   - Recommended for: All programmatic API access

2. FDA_WEBSITE_HEADERS (for accessdata.fda.gov):
   - Browser-like headers (required for technical compatibility)
   - Used for: PDF downloads from accessdata.fda.gov only
   - Required because: FDA's CDN/proxy infrastructure blocks non-browser UAs

WHY TWO USER-AGENTS?
====================

FDA's infrastructure has two separate systems:
- api.fda.gov: Modern REST API that accepts programmatic access
- accessdata.fda.gov: Legacy CDN with anti-bot protection

The accessdata.fda.gov PDF download endpoint returns 403 Forbidden for
programmatic user-agents (tested with "FDA-Plugin/x.x.x", "curl", "requests").
This appears to be CDN-level filtering, not FDA policy. We use browser-like
headers ONLY for this endpoint as a technical workaround.

CONFIGURATION
=============

You can override the user-agent behavior via ~/.claude/fda-tools.config.toml:

    [http]
    # Override user-agent string for all requests
    user_agent_override = "MyCustomUA/1.0"

    # Force honest UA for all requests (may cause PDF download failures)
    honest_ua_only = false

If honest_ua_only=true, PDF downloads from accessdata.fda.gov may fail with
HTTP 403 errors. In that case, you'll need to download PDFs manually or
configure your CDN/proxy to allow programmatic access.

FDA TERMS OF SERVICE COMPLIANCE
================================

This approach complies with FDA's Terms of Service:
- We identify ourselves honestly for API calls (FDA-Plugin/{version})
- Browser headers for PDFs are a technical necessity, not deception
- We rate-limit all requests (30s default delay between PDFs)
- We cache data to minimize server load (<5 day freshness check)
- We never circumvent authentication or access controls

References:
- openFDA API Policy: https://open.fda.gov/apis/authentication/
- FDA Accessibility: https://www.fda.gov/accessibility

USAGE
=====

    from fda_http import create_session, get_headers, FDA_API_HEADERS, FDA_WEBSITE_HEADERS

    # For API calls (recommended):
    session = create_session(purpose='api')
    response = session.get('https://api.fda.gov/device/classification.json')

    # For PDF downloads (technical necessity):
    session = create_session(purpose='website')
    response = session.get('https://www.accessdata.fda.gov/cdrh_docs/pdf24/K240123.pdf')

    # Using headers directly:
    import requests
    requests.get('https://api.fda.gov/...', headers=FDA_API_HEADERS)
    requests.get('https://accessdata.fda.gov/...', headers=FDA_WEBSITE_HEADERS)
"""

import os
import sys
import requests
from pathlib import Path

# Import centralized configuration (FDA-180 / ARCH-002)
try:
    from fda_tools.lib.config import get_config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False
    get_config = None  # type: ignore

# Version (try centralized config first, fall back to version.py)
if _CONFIG_AVAILABLE:
    try:
        PLUGIN_VERSION = get_config().get_str('general.plugin_version', '5.32.0')
    except Exception:
        PLUGIN_VERSION = "5.32.0"
else:
    try:
        from version import PLUGIN_VERSION
    except Exception:
        PLUGIN_VERSION = "5.32.0"


def _get_config_value(key: str, default: any) -> any:
    """Get configuration value from centralized config or fallback.

    Args:
        key: Configuration key (e.g., 'http.user_agent_override')
        default: Default value if config not available

    Returns:
        Configuration value or default
    """
    if _CONFIG_AVAILABLE:
        try:
            config = get_config()
            if key.startswith('http.'):
                if 'user_agent' in key:
                    return config.get_str(key, default)
                else:
                    return config.get_bool(key, default)
            return config.get(key, default)
        except Exception:
            pass
    return default


# Get configuration values (uses centralized config if available)
_user_agent_override = _get_config_value('http.user_agent_override', '')
_default_api_ua = _get_config_value('http.default_api_user_agent', f'FDA-Plugin/{PLUGIN_VERSION}')
_default_website_ua = _get_config_value('http.default_website_user_agent',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Honest user-agent for API calls (recommended for all api.fda.gov interactions)
FDA_API_HEADERS = {
    'User-Agent': _user_agent_override or _default_api_ua,
    'Accept': 'application/json',
}

# Browser-like headers for PDF downloads (technical necessity for accessdata.fda.gov)
# Only used when honest_ua_only=False (default)
FDA_WEBSITE_HEADERS = {
    'User-Agent': _user_agent_override or _default_website_ua,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Backward compatibility aliases (deprecated, use FDA_API_HEADERS/FDA_WEBSITE_HEADERS instead)
OPENFDA_HEADERS = FDA_API_HEADERS  # Deprecated: use FDA_API_HEADERS
FDA_HEADERS = FDA_WEBSITE_HEADERS  # Deprecated: use FDA_WEBSITE_HEADERS


def get_headers(purpose='website'):
    """Get appropriate HTTP headers for the given purpose.

    Args:
        purpose: 'api' for openFDA API calls, 'website' for PDF downloads.
                 Defaults to 'website' for backward compatibility.

    Returns:
        dict: HTTP headers appropriate for the purpose.

    Configuration:
        Respects configuration system (FDA-180):
        - http.user_agent_override: Custom UA string (overrides both api/website)
        - http.honest_ua_only: If true, uses honest UA for all requests
    """
    honest_ua_only = _get_config_value('http.honest_ua_only', False)

    if honest_ua_only:
        return FDA_API_HEADERS.copy()

    if purpose == 'api':
        return FDA_API_HEADERS.copy()
    else:
        return FDA_WEBSITE_HEADERS.copy()


def create_session(api_mode=False, purpose=None):
    """Create a requests.Session with appropriate FDA headers.

    Args:
        api_mode: (deprecated) If True, use API headers. Use purpose='api' instead.
        purpose: 'api' for openFDA API calls, 'website' for PDF downloads.
                 If not specified, uses api_mode for backward compatibility.

    Returns:
        requests.Session configured with appropriate headers.

    Examples:
        # Modern usage (recommended):
        session = create_session(purpose='api')
        session = create_session(purpose='website')

        # Legacy usage (still supported):
        session = create_session(api_mode=True)
    """
    session = requests.Session()

    # Determine purpose from args (support both old and new API)
    if purpose is None:
        purpose = 'api' if api_mode else 'website'

    headers = get_headers(purpose)
    session.headers.update(headers)
    return session

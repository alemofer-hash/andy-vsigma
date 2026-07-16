"""Pre-corporate ANDY BI contracts.

This package is intentionally inert by default. It prepares identity and
authorization contracts without connecting to a corporate identity provider.
"""

from .identity import IdentityClaims, MockIdentityResolution, MockIdentityResolver
from .policy import AccessDecision, AccessRequest, TenantPolicyResolver

__all__ = [
    "AccessDecision",
    "AccessRequest",
    "IdentityClaims",
    "MockIdentityResolution",
    "MockIdentityResolver",
    "TenantPolicyResolver",
]

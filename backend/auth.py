"""
Cepa Officer Authentication and Access Control Module.

Protects sensitive grower/trader records (DPDP compliance) and inspection
state mutations (creating, updating, finalizing inspections) with officer
token verification.
"""
from __future__ import annotations

import logging
from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from config import settings

logger = logging.getLogger(__name__)

officer_api_key_header = APIKeyHeader(name="X-Officer-Token", auto_error=False)


def verify_officer_token(
    x_officer_token: str | None = Security(officer_api_key_header),
) -> str:
    """
    Validate the officer authentication credential.

    Header:
        X-Officer-Token: <token>

    In development mode (ENFORCE_OFFICER_AUTH=false), unauthenticated requests are
    permitted with a development officer identity so test suites and local frontends
    operate without friction. In production, valid token matching settings.officer_api_key
    is strictly required.
    """
    if not settings.enforce_officer_auth:
        return x_officer_token or "officer-dev-default"

    if not x_officer_token:
        logger.warning("Rejected unauthenticated request to protected inspection route")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="DPDP Security: Authentication required. Header 'X-Officer-Token' is missing.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    import hmac

    if not hmac.compare_digest(x_officer_token, settings.officer_api_key):
        logger.warning("Rejected request with invalid officer token")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DPDP Security: Invalid officer credential.",
        )

    return x_officer_token

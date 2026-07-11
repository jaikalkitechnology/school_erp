"""Google Sign-In: verify a Google ID token, then log the user in.

We verify the token ourselves against Google's published public keys
(no ``google-auth`` dependency needed — ``python-jose`` is already in
the stack). The checks mirror what Google's own libraries do:

  * signature valid against the JWKS key whose ``kid`` matches
  * ``iss`` is accounts.google.com
  * ``aud`` is one of *our* configured client IDs (this is what stops
    a token minted for another app being replayed against us)
  * ``exp`` in the future
  * ``email_verified`` is true

On success we look the user up **inside the requested tenant only**
(subdomain-first multi-tenancy): match on ``google_sub`` first, then
fall back to ``email``. We never auto-create accounts — the school
admin must have invited the user first, same as password login.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx
from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.auth import AuthProvider, User
from app.models.tenant import Tenant


_GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

# Simple in-process cache of Google's JWKS. Google rotates keys a few
# times a day and sends a Cache-Control max-age; we honour a floor of
# 1h. Good enough for a single-process app; a multi-worker deploy just
# fetches once per worker.
_certs_cache: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_CERTS_TTL = 3600.0


async def _google_public_keys() -> list[dict]:
    now = time.time()
    if (
        _certs_cache["keys"] is not None
        and (now - _certs_cache["fetched_at"]) < _CERTS_TTL
    ):
        return _certs_cache["keys"]
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_GOOGLE_CERTS_URL)
        resp.raise_for_status()
        keys = resp.json().get("keys", [])
    _certs_cache["keys"] = keys
    _certs_cache["fetched_at"] = now
    return keys


async def verify_google_id_token(id_token: str) -> dict:
    """Verify + decode a Google ID token. Returns the claims dict on
    success; raises 401 on any failure."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Google sign-in failed. Please try again.",
    )

    # Find the signing key by kid.
    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError:
        raise unauthorized
    kid = header.get("kid")
    keys = await _google_public_keys()
    key = next((k for k in keys if k.get("kid") == kid), None)
    if key is None:
        # Key may have just rotated — force a refresh once.
        _certs_cache["fetched_at"] = 0.0
        keys = await _google_public_keys()
        key = next((k for k in keys if k.get("kid") == kid), None)
    if key is None:
        raise unauthorized

    audiences = settings.google_client_ids
    if not audiences:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google sign-in is not configured on the server.",
        )

    # jose validates signature + exp + aud + iss for us.
    last_err: Optional[Exception] = None
    claims: Optional[dict] = None
    for aud in audiences:
        try:
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=aud,
                options={"verify_at_hash": False},
            )
            break
        except JWTError as e:
            last_err = e
            continue
    if claims is None:
        raise unauthorized

    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise unauthorized
    if not claims.get("email"):
        raise unauthorized
    # email_verified comes back as a bool or the string "true".
    ev = claims.get("email_verified")
    if not (ev is True or str(ev).lower() == "true"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your Google email isn't verified.",
        )
    return claims


async def resolve_google_user(
    session: AsyncSession, *, tenant: Tenant, claims: dict,
) -> User:
    """Find the User for these Google claims **within this tenant**.

    Order: match by google_sub, then by email. On an email match we
    link the google_sub for next time. We never create a new account —
    the user must already have been invited by their school admin."""
    sub = claims.get("sub")
    email = (claims.get("email") or "").strip().lower()

    user: Optional[User] = None
    if sub:
        user = (
            await session.execute(
                select(User).where(
                    User.tenant_id == tenant.id, User.google_sub == sub,
                )
            )
        ).scalar_one_or_none()

    if user is None and email:
        user = (
            await session.execute(
                select(User).where(
                    User.tenant_id == tenant.id,
                    User.email.isnot(None),
                    User.email == email,
                )
            )
        ).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No account for this Google email at this school. "
                "Ask your school admin to invite you, or check you "
                "picked the right school."
            ),
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled. Contact your school admin.",
        )

    # Link the google_sub + mark email verified for next time.
    if sub and user.google_sub != sub:
        user.google_sub = sub
    if user.auth_provider == AuthProvider.PASSWORD.value:
        # Keep password login working too — don't overwrite provider,
        # just record that Google is now linked via google_sub.
        pass
    user.is_email_verified = True
    return user

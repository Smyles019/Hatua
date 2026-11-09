"""Checks a Google ID token sent by the app.

The app signs in with Google on the phone and sends the ID token here. The token is
only trusted if Google's signature is valid, it was issued for one of our client IDs,
it has not expired, and Google has verified the email address.
"""
from dataclasses import dataclass

from app.core.config import settings


class GoogleTokenError(Exception):
    """The token is missing, forged, expired, for another app, or unverified."""


@dataclass
class GoogleIdentity:
    google_id: str
    email: str
    name: str


def verify_google_token(token: str) -> GoogleIdentity:
    audiences = settings.google_audiences
    if not audiences:
        raise GoogleTokenError("Google sign-in is not set up on this server")
    # Imported here so the API still starts if google-auth is not installed yet.
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_oauth2_token(token, google_requests.Request(), audience=None)
    except ValueError as e:
        raise GoogleTokenError("invalid Google sign-in token") from e
    if claims.get("aud") not in audiences:
        raise GoogleTokenError("this Google token was issued for another app")
    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise GoogleTokenError("invalid Google sign-in token")
    if not claims.get("email") or not claims.get("email_verified"):
        raise GoogleTokenError("this Google account has no verified email address")
    return GoogleIdentity(google_id=str(claims["sub"]), email=claims["email"].lower(),
                          name=claims.get("name") or claims["email"].split("@")[0])

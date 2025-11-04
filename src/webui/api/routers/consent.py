"""
Consent management router for handling terms and conditions acceptance.
Stores consent status in Redis with 30-day expiration.
"""

from fastapi import APIRouter, Response, Cookie, HTTPException, Request
from typing import Optional
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/consent", tags=["consent"])


@router.get("/check")
async def check_consent(
    request: Request,
    session_id: Optional[str] = Cookie(None)
):
    """
    Check if the user has previously accepted the terms and conditions.

    Args:
        request: FastAPI request object (contains Redis client in app.state)
        session_id: Optional session ID from cookie

    Returns:
        dict: {"has_consent": bool, "session_id": str}
    """
    if not session_id:
        return {"has_consent": False, "session_id": None}

    try:
        redis_client = request.app.state.redis_client
        consent_key = f"consent:{session_id}"
        consent = await redis_client.get(consent_key)

        has_consent = consent is not None
        logger.info(f"Consent check for session {session_id[:8]}...: {has_consent}")

        return {
            "has_consent": has_consent,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error checking consent: {str(e)}")
        return {"has_consent": False, "session_id": session_id}


@router.post("/accept")
async def accept_consent(
    request: Request,
    response: Response,
    session_id: Optional[str] = Cookie(None)
):
    """
    Record user's acceptance of terms and conditions.
    Creates a new session if one doesn't exist.
    Stores consent in Redis with 30-day expiration.

    Args:
        request: FastAPI request object (contains Redis client in app.state)
        response: FastAPI response object (for setting cookies)
        session_id: Optional existing session ID from cookie

    Returns:
        dict: {"status": str, "session_id": str}
    """
    # Generate new session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"Generated new session ID: {session_id[:8]}...")
    else:
        logger.info(f"Using existing session ID: {session_id[:8]}...")

    try:
        redis_client = request.app.state.redis_client
        consent_key = f"consent:{session_id}"

        # Store consent with 30-day expiration (2592000 seconds)
        await redis_client.set(
            consent_key,
            "accepted",
            ex=2592000  # 30 days in seconds
        )

        # Set cookie with same 30-day expiration
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=2592000,  # 30 days in seconds
            secure=True,  # Only send over HTTPS
            httponly=True,  # Not accessible via JavaScript
            samesite="lax"  # CSRF protection
        )

        logger.info(f"Consent accepted for session {session_id[:8]}... (30-day expiration)")

        return {
            "status": "ok",
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error storing consent: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to store consent"
        )


@router.delete("/revoke")
async def revoke_consent(
    request: Request,
    response: Response,
    session_id: Optional[str] = Cookie(None)
):
    """
    Revoke user's consent (optional endpoint for future use).

    Args:
        request: FastAPI request object
        response: FastAPI response object
        session_id: Session ID from cookie

    Returns:
        dict: {"status": str}
    """
    if not session_id:
        return {"status": "no_session"}

    try:
        redis_client = request.app.state.redis_client
        consent_key = f"consent:{session_id}"

        # Delete the consent record
        await redis_client.delete(consent_key)

        # Clear the session cookie
        response.delete_cookie(key="session_id")

        logger.info(f"Consent revoked for session {session_id[:8]}...")

        return {"status": "revoked"}
    except Exception as e:
        logger.error(f"Error revoking consent: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to revoke consent"
        )

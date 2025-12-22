"""
HubCore Authentication Manager
Handles magic link auth and session management for hubs.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import secrets
import hashlib
import logging

from .config import AuthConfig

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Manages authentication for a Hub.
    
    Supports:
    - Magic link authentication (default)
    - Session management
    - Email domain validation
    
    Note: This is a base implementation. Production deployments
    should use a proper auth service (e.g., Stytch, Auth0).
    """
    
    def __init__(self, config: AuthConfig):
        self.config = config
        
        # In-memory stores (replace with database in production)
        self._pending_links: Dict[str, Dict] = {}  # token -> {email, expires}
        self._sessions: Dict[str, Dict] = {}  # session_token -> {user_id, email, expires}
        
    async def send_magic_link(self, email: str) -> Dict[str, Any]:
        """
        Generate and "send" a magic link.
        
        In production, this would send an actual email.
        For development, it returns the link directly.
        
        Args:
            email: User's email address
            
        Returns:
            Dict with status and (in dev) the magic link
        """
        # Validate email domain
        if not self.config.validate_email(email):
            return {
                "success": False,
                "error": f"Email must be from {self.config.email_domain}"
            }
        
        # Generate token
        token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(minutes=15)
        
        # Store pending link
        self._pending_links[token] = {
            "email": email,
            "expires": expires
        }
        
        logger.info(f"Magic link generated for {email}")
        
        # In production, send email here
        # For now, return the token (dev mode)
        return {
            "success": True,
            "message": f"Magic link sent to {email}",
            "dev_token": token  # Remove in production!
        }
    
    async def verify_magic_link(self, token: str) -> Dict[str, Any]:
        """
        Verify a magic link token and create a session.
        
        Args:
            token: The magic link token
            
        Returns:
            Dict with session info if valid
        """
        pending = self._pending_links.get(token)
        
        if not pending:
            return {"success": False, "error": "Invalid or expired link"}
        
        if datetime.now() > pending["expires"]:
            del self._pending_links[token]
            return {"success": False, "error": "Link has expired"}
        
        # Create session
        email = pending["email"]
        user_id = self._email_to_user_id(email)
        session_token = secrets.token_urlsafe(32)
        
        session_expires = datetime.now() + timedelta(
            hours=self.config.session_duration_hours
        )
        
        self._sessions[session_token] = {
            "user_id": user_id,
            "email": email,
            "expires": session_expires,
            "created": datetime.now()
        }
        
        # Clean up used link
        del self._pending_links[token]
        
        logger.info(f"Session created for {email}")
        
        return {
            "success": True,
            "session_token": session_token,
            "user_id": user_id,
            "email": email,
            "expires": session_expires.isoformat()
        }
    
    async def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session token.
        
        Args:
            session_token: The session token to validate
            
        Returns:
            User info dict if valid, None if not
        """
        session = self._sessions.get(session_token)
        
        if not session:
            return None
        
        if datetime.now() > session["expires"]:
            del self._sessions[session_token]
            return None
        
        return {
            "user_id": session["user_id"],
            "email": session["email"],
            "expires": session["expires"].isoformat()
        }
    
    async def invalidate_session(self, session_token: str) -> bool:
        """
        Invalidate (logout) a session.
        
        Args:
            session_token: The session to invalidate
            
        Returns:
            True if session was invalidated
        """
        if session_token in self._sessions:
            del self._sessions[session_token]
            return True
        return False
    
    def _email_to_user_id(self, email: str) -> str:
        """
        Convert email to a user ID.
        
        For UVA emails, extracts the computing ID.
        For other emails, creates a hash-based ID.
        
        Args:
            email: User's email
            
        Returns:
            User ID string
        """
        # For UVA emails, use the computing ID (part before @)
        if email.endswith("@virginia.edu"):
            return email.split("@")[0]
        
        # For other emails, create a hash-based ID
        return hashlib.sha256(email.encode()).hexdigest()[:12]
    
    async def cleanup_expired(self):
        """
        Clean up expired links and sessions.
        Call this periodically.
        """
        now = datetime.now()
        
        # Clean expired pending links
        expired_links = [
            token for token, data in self._pending_links.items()
            if now > data["expires"]
        ]
        for token in expired_links:
            del self._pending_links[token]
        
        # Clean expired sessions
        expired_sessions = [
            token for token, data in self._sessions.items()
            if now > data["expires"]
        ]
        for token in expired_sessions:
            del self._sessions[token]
        
        if expired_links or expired_sessions:
            logger.info(
                f"Cleaned up {len(expired_links)} links, "
                f"{len(expired_sessions)} sessions"
            )

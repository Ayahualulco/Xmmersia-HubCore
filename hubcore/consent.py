"""
HubCore Consent Manager
Handles user consent for data usage in hubs.
"""

from typing import Dict, Any, Optional, Set
from datetime import datetime
import logging

from .config import ConsentConfig

logger = logging.getLogger(__name__)


class ConsentManager:
    """
    Manages user consent for a Hub.
    
    Tracks:
    - Who has consented
    - When they consented
    - Consent revocation
    
    Note: This is a base implementation using in-memory storage.
    Production deployments should persist consent records.
    """
    
    def __init__(self, config: ConsentConfig):
        self.config = config
        
        # In-memory consent store (replace with database in production)
        self._consents: Dict[str, Dict] = {}  # user_id -> {timestamp, revoked}
        
    async def has_consented(self, user_id: str) -> bool:
        """
        Check if a user has given consent.
        
        Args:
            user_id: The user to check
            
        Returns:
            True if user has active (non-revoked) consent
        """
        if not self.config.required:
            return True  # No consent required
        
        consent = self._consents.get(user_id)
        if not consent:
            return False
        
        # Check if revoked
        if consent.get("revoked"):
            return False
        
        return True
    
    async def record_consent(self, user_id: str) -> Dict[str, Any]:
        """
        Record a user's consent.
        
        Args:
            user_id: The user giving consent
            
        Returns:
            Dict with consent record info
        """
        timestamp = datetime.now()
        
        self._consents[user_id] = {
            "user_id": user_id,
            "timestamp": timestamp,
            "revoked": False,
            "revoked_at": None,
            "consent_version": "1.0"  # Track consent text version
        }
        
        logger.info(f"Consent recorded for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "timestamp": timestamp.isoformat(),
            "message": "Consent recorded successfully"
        }
    
    async def revoke_consent(self, user_id: str) -> Dict[str, Any]:
        """
        Revoke a user's consent.
        
        Args:
            user_id: The user revoking consent
            
        Returns:
            Dict with revocation status
        """
        if not self.config.revocable:
            return {
                "success": False,
                "error": "Consent cannot be revoked for this hub"
            }
        
        consent = self._consents.get(user_id)
        if not consent:
            return {
                "success": False,
                "error": "No consent record found"
            }
        
        consent["revoked"] = True
        consent["revoked_at"] = datetime.now()
        
        logger.info(f"Consent revoked for user {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "message": "Consent has been revoked"
        }
    
    async def get_consent_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get consent information for a user.
        
        Args:
            user_id: The user to look up
            
        Returns:
            Consent record if exists, None otherwise
        """
        consent = self._consents.get(user_id)
        if not consent:
            return None
        
        return {
            "user_id": consent["user_id"],
            "consented_at": consent["timestamp"].isoformat(),
            "revoked": consent["revoked"],
            "revoked_at": consent["revoked_at"].isoformat() if consent["revoked_at"] else None,
            "consent_version": consent["consent_version"]
        }
    
    def get_consent_text(self) -> Dict[str, Any]:
        """
        Get the consent form content.
        
        Returns:
            Dict with consent form content
        """
        return {
            "title": self.config.title,
            "text": self.config.text,
            "data_usage": self.config.data_usage,
            "data_shared_with": self.config.data_shared_with,
            "optional_participation": self.config.optional_participation,
            "revocable": self.config.revocable
        }
    
    async def get_all_consented_users(self) -> Set[str]:
        """
        Get all users who have active consent.
        
        Returns:
            Set of user IDs with active consent
        """
        return {
            user_id 
            for user_id, consent in self._consents.items()
            if not consent.get("revoked")
        }
    
    async def export_consent_records(self) -> list:
        """
        Export all consent records (for compliance).
        
        Returns:
            List of consent records
        """
        return [
            {
                "user_id": user_id,
                "consented_at": consent["timestamp"].isoformat(),
                "revoked": consent["revoked"],
                "revoked_at": consent["revoked_at"].isoformat() if consent["revoked_at"] else None
            }
            for user_id, consent in self._consents.items()
        ]

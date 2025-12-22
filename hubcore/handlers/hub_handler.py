"""
HubCore HTTP Handler
FastAPI router for hub endpoints.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import logging

from ..base_hub import BaseHub

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────

class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkVerifyRequest(BaseModel):
    token: str


class ConsentRequest(BaseModel):
    user_id: str


class ActionRequest(BaseModel):
    action_id: str
    params: Dict[str, Any] = {}


# ─────────────────────────────────────────────────────────────
# Hub Handler
# ─────────────────────────────────────────────────────────────

class HubHandler:
    """
    Creates FastAPI routes for a Hub.
    
    Provides endpoints for:
    - Hub info and health
    - Authentication (magic link)
    - Consent management
    - Action execution
    """
    
    def __init__(self, hub: BaseHub):
        self.hub = hub
        self.router = APIRouter()
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up all routes"""
        
        # ─────────────────────────────────────────────────────
        # Info & Health
        # ─────────────────────────────────────────────────────
        
        @self.router.get("/")
        async def hub_info():
            """Get hub information"""
            return self.hub.get_hub_card()
        
        @self.router.get("/health")
        async def health_check():
            """Health check endpoint"""
            return await self.hub.health_check()
        
        @self.router.get("/actions")
        async def get_actions():
            """Get available actions"""
            return {
                "actions": [action.to_dict() for action in self.hub.actions]
            }
        
        @self.router.get("/consent-form")
        async def get_consent_form():
            """Get consent form content"""
            return self.hub.consent_manager.get_consent_text()
        
        # ─────────────────────────────────────────────────────
        # Authentication
        # ─────────────────────────────────────────────────────
        
        @self.router.post("/auth/magic-link")
        async def request_magic_link(request: MagicLinkRequest):
            """Request a magic link for login"""
            result = await self.hub.request_magic_link(request.email)
            
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("error"))
            
            return result
        
        @self.router.post("/auth/verify")
        async def verify_magic_link(request: MagicLinkVerifyRequest):
            """Verify magic link and get session"""
            result = await self.hub.auth_manager.verify_magic_link(request.token)
            
            if not result.get("success"):
                raise HTTPException(status_code=401, detail=result.get("error"))
            
            # Call login hook
            await self.hub.on_user_login(
                result["user_id"], 
                result["email"]
            )
            
            return result
        
        @self.router.get("/auth/session")
        async def check_session(request: Request):
            """Check current session status"""
            session_token = self._get_session_token(request)
            
            if not session_token:
                return {"authenticated": False}
            
            user = await self.hub.check_auth(session_token)
            
            if not user:
                return {"authenticated": False}
            
            # Also check consent
            has_consent = await self.hub.check_consent(user["user_id"])
            
            return {
                "authenticated": True,
                "user": user,
                "has_consent": has_consent
            }
        
        @self.router.post("/auth/logout")
        async def logout(request: Request):
            """Logout and invalidate session"""
            session_token = self._get_session_token(request)
            
            if session_token:
                await self.hub.auth_manager.invalidate_session(session_token)
            
            return {"success": True, "message": "Logged out"}
        
        # ─────────────────────────────────────────────────────
        # Consent
        # ─────────────────────────────────────────────────────
        
        @self.router.post("/consent")
        async def record_consent(request: Request):
            """Record user consent"""
            user = await self._require_auth(request)
            
            result = await self.hub.record_consent(user["user_id"])
            return result
        
        @self.router.delete("/consent")
        async def revoke_consent(request: Request):
            """Revoke user consent"""
            user = await self._require_auth(request)
            
            result = await self.hub.consent_manager.revoke_consent(user["user_id"])
            
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("error"))
            
            return result
        
        @self.router.get("/consent/status")
        async def consent_status(request: Request):
            """Get consent status for current user"""
            user = await self._require_auth(request)
            
            info = await self.hub.consent_manager.get_consent_info(user["user_id"])
            
            return {
                "has_consent": info is not None and not info.get("revoked"),
                "consent_info": info
            }
        
        # ─────────────────────────────────────────────────────
        # Actions
        # ─────────────────────────────────────────────────────
        
        @self.router.post("/action")
        async def execute_action(action_request: ActionRequest, request: Request):
            """Execute a hub action"""
            user = await self._require_auth(request)
            
            # Check consent if required
            if self.hub.config.consent_required:
                has_consent = await self.hub.check_consent(user["user_id"])
                if not has_consent:
                    raise HTTPException(
                        status_code=403, 
                        detail="Consent required before using this hub"
                    )
            
            try:
                result = await self.hub.handle_action(
                    action_request.action_id,
                    user["user_id"],
                    action_request.params
                )
                return result
                
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except Exception as e:
                logger.error(f"Action failed: {e}")
                raise HTTPException(status_code=500, detail="Action failed")
        
        @self.router.post("/action/{action_id}")
        async def execute_action_by_id(
            action_id: str, 
            request: Request,
            params: Dict[str, Any] = {}
        ):
            """Execute a specific action by ID"""
            user = await self._require_auth(request)
            
            # Check consent
            if self.hub.config.consent_required:
                has_consent = await self.hub.check_consent(user["user_id"])
                if not has_consent:
                    raise HTTPException(status_code=403, detail="Consent required")
            
            try:
                result = await self.hub.handle_action(action_id, user["user_id"], params)
                return result
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
    
    # ─────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────
    
    def _get_session_token(self, request: Request) -> Optional[str]:
        """Extract session token from request"""
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Check cookie
        return request.cookies.get("session_token")
    
    async def _require_auth(self, request: Request) -> Dict[str, Any]:
        """Require authentication, raise 401 if not authenticated"""
        session_token = self._get_session_token(request)
        
        if not session_token:
            raise HTTPException(
                status_code=401, 
                detail="Authentication required"
            )
        
        user = await self.hub.check_auth(session_token)
        
        if not user:
            raise HTTPException(
                status_code=401, 
                detail="Invalid or expired session"
            )
        
        return user


def create_hub_app(hub: BaseHub) -> APIRouter:
    """
    Create a FastAPI router for a hub.
    
    Usage:
        from fastapi import FastAPI
        from hubcore import create_hub_app
        
        app = FastAPI()
        hub = PracticeHub()
        await hub.initialize()
        
        app.include_router(create_hub_app(hub), prefix="/practice")
    """
    handler = HubHandler(hub)
    return handler.router

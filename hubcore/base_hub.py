"""
HubCore BaseHub
Abstract base class all Xmmersia Hubs must inherit from.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import logging

from .config import (
    HubConfig, 
    SkillExposure, 
    HubAction, 
    AuthConfig, 
    ConsentConfig,
    AgentConnection
)
from .router import HubRouter
from .auth import AuthManager
from .consent import ConsentManager

logger = logging.getLogger(__name__)


class BaseHub(ABC):
    """
    Abstract base class all Xmmersia Hubs must inherit from.
    
    A Hub is a unified interface that brings together multiple agents
    to serve a specific domain, exposing curated skills while keeping
    agents complete and independent.
    
    Subclasses must implement:
    - configure() -> HubConfig
    - register_agents() -> dict
    - define_skill_exposure() -> dict
    - define_ui_actions() -> list
    """
    
    def __init__(self):
        self.config: Optional[HubConfig] = None
        self.agents: Dict[str, AgentConnection] = {}
        self.actions: List[HubAction] = []
        self.router: Optional[HubRouter] = None
        self.auth_manager: Optional[AuthManager] = None
        self.consent_manager: Optional[ConsentManager] = None
        
        self.initialized = False
        self.started_at: Optional[datetime] = None
        
    # ─────────────────────────────────────────────────────────────
    # Abstract methods - must be implemented by subclasses
    # ─────────────────────────────────────────────────────────────
    
    @abstractmethod
    def configure(self) -> HubConfig:
        """
        Return the configuration for this hub.
        
        Returns:
            HubConfig with name, slug, description, version, etc.
        """
        pass
    
    @abstractmethod
    def register_agents(self) -> Dict[str, str]:
        """
        Register the agents available in this hub.
        
        Returns:
            Dict mapping agent name to URL, e.g.:
            {
                "gaston": "http://localhost:8020",
                "lumiere": "http://localhost:8021"
            }
        """
        pass
    
    @abstractmethod
    def define_skill_exposure(self) -> Dict[str, SkillExposure]:
        """
        Define which skills from each agent are exposed.
        
        Returns:
            Dict mapping agent name to SkillExposure, e.g.:
            {
                "gaston": SkillExposure(
                    exposed=["request_worksheet"],
                    hidden=["chatbot"]
                )
            }
        """
        pass
    
    @abstractmethod
    def define_ui_actions(self) -> List[HubAction]:
        """
        Define the user-facing actions available in this hub.
        
        Returns:
            List of HubAction objects defining buttons/actions
        """
        pass
    
    # ─────────────────────────────────────────────────────────────
    # Optional overridable methods
    # ─────────────────────────────────────────────────────────────
    
    def configure_auth(self) -> AuthConfig:
        """
        Configure authentication for this hub.
        Override to customize auth settings.
        
        Returns:
            AuthConfig with method, email_domain, etc.
        """
        return AuthConfig()
    
    def configure_consent(self) -> ConsentConfig:
        """
        Configure consent requirements for this hub.
        Override to customize consent settings.
        
        Returns:
            ConsentConfig with text, data_usage, etc.
        """
        return ConsentConfig()
    
    async def on_initialize(self):
        """
        Called after hub initialization.
        Override to perform custom setup.
        """
        pass
    
    async def on_user_login(self, user_id: str, email: str):
        """
        Called when a user logs in.
        Override to perform custom logic.
        """
        pass
    
    async def on_user_consent(self, user_id: str):
        """
        Called when a user gives consent.
        Override to perform custom logic (e.g., create profile).
        """
        pass
    
    async def on_action_start(self, action_id: str, user_id: str, params: dict):
        """
        Called before an action is executed.
        Override to add logging, validation, etc.
        """
        pass
    
    async def on_action_complete(self, action_id: str, user_id: str, result: dict):
        """
        Called after an action completes.
        Override to add logging, notifications, etc.
        """
        pass
    
    # ─────────────────────────────────────────────────────────────
    # Core lifecycle methods
    # ─────────────────────────────────────────────────────────────
    
    async def initialize(self):
        """
        Initialize the hub. Call this before using the hub.
        
        1. Load configuration
        2. Register agents
        3. Set up skill exposure
        4. Initialize router
        5. Set up auth and consent managers
        """
        logger.info(f"Initializing hub...")
        
        # Load configuration
        self.config = self.configure()
        logger.info(f"Hub: {self.config.name} v{self.config.version}")
        
        # Register agents with skill exposure
        agent_urls = self.register_agents()
        skill_exposures = self.define_skill_exposure()
        
        for agent_name, url in agent_urls.items():
            exposure = skill_exposures.get(agent_name, SkillExposure())
            self.agents[agent_name] = AgentConnection(
                name=agent_name,
                url=url,
                skill_exposure=exposure
            )
            logger.info(f"Registered agent: {agent_name} at {url}")
            logger.info(f"  Exposed skills: {exposure.exposed}")
            logger.info(f"  Hidden skills: {exposure.hidden}")
        
        # Load UI actions
        self.actions = self.define_ui_actions()
        logger.info(f"Loaded {len(self.actions)} UI actions")
        
        # Initialize router
        self.router = HubRouter(self.agents, self.actions)
        
        # Initialize auth manager
        auth_config = self.configure_auth()
        self.auth_manager = AuthManager(auth_config)
        
        # Initialize consent manager
        consent_config = self.configure_consent()
        self.consent_manager = ConsentManager(consent_config)
        
        # Mark as initialized
        self.initialized = True
        self.started_at = datetime.now()
        
        # Call custom initialization hook
        await self.on_initialize()
        
        logger.info(f"Hub initialized successfully")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of hub and all connected agents.
        
        Returns:
            Dict with health status
        """
        if not self.initialized:
            return {"status": "not_initialized"}
        
        agent_health = {}
        for name, agent in self.agents.items():
            # TODO: Actually ping agent health endpoints
            agent_health[name] = {
                "url": agent.url,
                "healthy": True,  # Placeholder
                "exposed_skills": agent.skill_exposure.exposed
            }
        
        return {
            "status": "healthy",
            "hub": self.config.name,
            "version": self.config.version,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "agents": agent_health,
            "actions_count": len(self.actions)
        }
    
    # ─────────────────────────────────────────────────────────────
    # Action handling
    # ─────────────────────────────────────────────────────────────
    
    async def handle_action(
        self, 
        action_id: str, 
        user_id: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a user action.
        
        1. Verify user is authenticated
        2. Verify user has consented
        3. Check preconditions
        4. Route to appropriate agent
        5. Return result
        
        Args:
            action_id: The action to execute
            user_id: The user making the request
            params: Parameters for the action
            
        Returns:
            Result from the agent
        """
        if not self.initialized:
            raise RuntimeError("Hub not initialized")
        
        # Find the action
        action = self._get_action(action_id)
        if not action:
            raise ValueError(f"Unknown action: {action_id}")
        
        # Check if skill is exposed
        agent = self.agents.get(action.agent)
        if not agent:
            raise ValueError(f"Unknown agent: {action.agent}")
        
        if not agent.skill_exposure.is_user_callable(action.skill):
            raise PermissionError(f"Skill {action.skill} is not available in this hub")
        
        # Call pre-action hook
        await self.on_action_start(action_id, user_id, params)
        
        # Check precondition if specified
        if action.precondition:
            precondition_result = await self.router.check_precondition(
                action.precondition, user_id, params
            )
            if not precondition_result.get("satisfied", False):
                return {
                    "status": "precondition_failed",
                    "message": precondition_result.get("message", "Precondition not met"),
                    "action_required": precondition_result.get("action_required")
                }
        
        # Route to agent
        result = await self.router.route_action(action, user_id, params)
        
        # Call post-action hook
        await self.on_action_complete(action_id, user_id, result)
        
        return result
    
    def _get_action(self, action_id: str) -> Optional[HubAction]:
        """Find an action by ID"""
        for action in self.actions:
            if action.id == action_id:
                return action
        return None
    
    # ─────────────────────────────────────────────────────────────
    # Auth and consent
    # ─────────────────────────────────────────────────────────────
    
    async def check_auth(self, session_token: str) -> Dict[str, Any]:
        """
        Check if a session token is valid.
        
        Returns:
            Dict with user info if valid, None if not
        """
        return await self.auth_manager.validate_session(session_token)
    
    async def request_magic_link(self, email: str) -> Dict[str, Any]:
        """
        Request a magic link for login.
        
        Args:
            email: User's email address
            
        Returns:
            Dict with status
        """
        return await self.auth_manager.send_magic_link(email)
    
    async def check_consent(self, user_id: str) -> bool:
        """
        Check if user has consented.
        
        Returns:
            True if consented, False if not
        """
        return await self.consent_manager.has_consented(user_id)
    
    async def record_consent(self, user_id: str) -> Dict[str, Any]:
        """
        Record user's consent.
        
        Returns:
            Dict with status
        """
        result = await self.consent_manager.record_consent(user_id)
        
        # Call consent hook
        await self.on_user_consent(user_id)
        
        return result
    
    # ─────────────────────────────────────────────────────────────
    # Hub card (similar to agent card)
    # ─────────────────────────────────────────────────────────────
    
    def get_hub_card(self) -> Dict[str, Any]:
        """
        Generate hub card (similar to agent card).
        Describes the hub's capabilities and available actions.
        
        Returns:
            Dict with hub information
        """
        return {
            "name": self.config.name,
            "slug": self.config.slug,
            "description": self.config.description,
            "version": self.config.version,
            "url": f"https://xmmersia.com/{self.config.slug}",
            "hubCoreVersion": "1.0.0",
            "theme": self.config.theme.value,
            "agents": [
                {
                    "name": name,
                    "url": agent.url,
                    "exposed_skills": agent.skill_exposure.exposed
                }
                for name, agent in self.agents.items()
            ],
            "actions": [action.to_dict() for action in self.actions],
            "auth": {
                "required": self.config.auth_required,
                "method": self.auth_manager.config.method if self.auth_manager else "magic_link"
            },
            "consent": {
                "required": self.config.consent_required
            }
        }

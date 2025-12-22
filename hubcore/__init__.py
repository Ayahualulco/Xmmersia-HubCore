"""
Xmmersia HubCore - Foundation for all Xmmersia Hubs
"""

from .base_hub import BaseHub
from .config import HubConfig, SkillExposure, HubAction, AuthConfig, ConsentConfig
from .router import HubRouter
from .auth import AuthManager
from .consent import ConsentManager

__version__ = "1.0.0"
__all__ = [
    "BaseHub",
    "HubConfig",
    "SkillExposure", 
    "HubAction",
    "AuthConfig",
    "ConsentConfig",
    "HubRouter",
    "AuthManager",
    "ConsentManager"
]

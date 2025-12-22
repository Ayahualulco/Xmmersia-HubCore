"""
HubCore Configuration Classes
Defines the configuration structures for Hubs
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class UITheme(Enum):
    """Available UI themes for hubs"""
    ORGANIC = "organic"      # Gaudí-inspired, flowing
    MINIMAL = "minimal"      # Clean, simple
    DARK = "dark"           # Dark mode
    ACADEMIC = "academic"   # Traditional, formal


@dataclass
class HubConfig:
    """
    Core configuration for a Hub.
    Defines identity, behavior, and display settings.
    """
    name: str                           # Human-readable name: "Practice Hub"
    slug: str                           # URL slug: "practice" -> xmmersia.com/practice
    description: str                    # Description shown to users
    version: str                        # Semantic version
    
    # Behavior
    auth_required: bool = True          # Require login?
    consent_required: bool = True       # Require consent form?
    
    # Display
    theme: UITheme = UITheme.ORGANIC    # UI theme
    tagline: str = ""                   # Optional tagline
    icon: str = "🎓"                    # Hub icon/emoji
    
    # Metadata
    course: Optional[str] = None        # Associated course if educational
    semester: Optional[str] = None      # Associated semester
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "version": self.version,
            "auth_required": self.auth_required,
            "consent_required": self.consent_required,
            "theme": self.theme.value,
            "tagline": self.tagline,
            "icon": self.icon,
            "course": self.course,
            "semester": self.semester
        }


@dataclass
class SkillExposure:
    """
    Defines which skills from an agent are exposed in this Hub.
    
    - exposed: Skills shown in UI, directly callable by users
    - hidden: Skills the agent has but are not available in this hub
    - internal: Skills that hub logic can call, but users cannot directly invoke
    """
    exposed: List[str] = field(default_factory=list)
    hidden: List[str] = field(default_factory=list)
    internal: List[str] = field(default_factory=list)
    
    def is_user_callable(self, skill_id: str) -> bool:
        """Check if a skill can be called by a user in this hub"""
        return skill_id in self.exposed
    
    def is_hub_callable(self, skill_id: str) -> bool:
        """Check if hub logic can call this skill"""
        return skill_id in self.exposed or skill_id in self.internal
    
    def all_available(self) -> List[str]:
        """All skills available to hub logic"""
        return self.exposed + self.internal


@dataclass
class HubAction:
    """
    A user-facing action in the Hub UI.
    Maps a button/action to an agent skill.
    """
    id: str                             # Unique identifier
    label: str                          # Display label: "Generate New Worksheet"
    icon: str                           # Emoji or icon class
    agent: str                          # Which agent handles this
    skill: str                          # Which skill to invoke
    
    # Optional configuration
    description: str = ""               # Longer description
    precondition: Optional[str] = None  # Skill to check before allowing action
    confirm: bool = False               # Require confirmation?
    confirm_message: str = ""           # Confirmation message if confirm=True
    
    # UI hints
    primary: bool = False               # Is this a primary action?
    position: int = 0                   # Display order
    group: Optional[str] = None         # Group with other actions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "icon": self.icon,
            "agent": self.agent,
            "skill": self.skill,
            "description": self.description,
            "precondition": self.precondition,
            "confirm": self.confirm,
            "primary": self.primary,
            "position": self.position,
            "group": self.group
        }


@dataclass 
class AuthConfig:
    """
    Authentication configuration for a Hub.
    """
    method: str = "magic_link"          # "magic_link", "oauth", "password"
    email_domain: Optional[str] = None  # Restrict to domain: "virginia.edu"
    session_duration_hours: int = 24    # How long sessions last
    
    # OAuth settings (if method="oauth")
    oauth_provider: Optional[str] = None
    oauth_client_id: Optional[str] = None
    
    def validate_email(self, email: str) -> bool:
        """Check if email is valid for this hub"""
        if self.email_domain is None:
            return True
        return email.endswith(f"@{self.email_domain}")


@dataclass
class ConsentConfig:
    """
    Consent/privacy configuration for a Hub.
    """
    required: bool = True               # Is consent required?
    
    # Consent text
    title: str = "Consent Required"
    text: str = ""                      # Main consent text
    
    # Data usage disclosure
    data_usage: List[str] = field(default_factory=list)  # What data is used for
    data_shared_with: List[str] = field(default_factory=list)  # Who sees data
    
    # Options
    revocable: bool = True              # Can user revoke consent?
    optional_participation: bool = True  # Is participation optional?
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "required": self.required,
            "title": self.title,
            "text": self.text,
            "data_usage": self.data_usage,
            "data_shared_with": self.data_shared_with,
            "revocable": self.revocable,
            "optional_participation": self.optional_participation
        }


@dataclass
class AgentConnection:
    """
    Connection details for an agent in the hub.
    """
    name: str                           # Agent name: "gaston"
    url: str                            # Agent URL: "http://localhost:8020"
    skill_exposure: SkillExposure       # Which skills are exposed
    
    # Connection settings
    timeout_seconds: int = 30           # Request timeout
    retry_attempts: int = 3             # Retry on failure
    
    # Status
    healthy: bool = False               # Is agent responding?
    last_health_check: Optional[str] = None  # ISO timestamp

# Xmmersia-HubCore

The foundation for all Xmmersia Hubs. HubCore defines how multiple agents collaborate through a unified interface, exposing curated skills while keeping agents complete and independent.

## What is HubCore?

A **Hub** is a unified interface that brings together multiple Mates (agents) to serve a specific domain. HubCore provides:

- **BaseHub**: Abstract class all hubs inherit from
- **SkillExposure**: Patterns for exposing/hiding agent skills
- **AuthFlow**: Authentication and consent management
- **HubRouter**: Routes user actions to appropriate agents
- **HubConfig**: Configuration for hub behavior

## Key Concept: Agents vs Hubs

**Agents are complete beings** with full capabilities defined in their agent cards:
- LUMIÈRE has OCR, rubric grading, answer checking, PDF annotation
- GASTON has chatbot, progress queries, worksheet orchestration

**Hubs expose a curated subset** of agent skills:
- Practice Hub exposes LUMIÈRE's `check_answers` but not `rubric_grade`
- Practice Hub uses GASTON's chatbot internally but hides the chat interface
- Same agents, different hubs, different skill exposure

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT SKILLS vs HUB EXPOSURE                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  GASTON (Full Agent)         │  GASTON in Practice Hub          │
│  ├── chatbot ✓               │  ├── request_worksheet ✅        │
│  ├── request_worksheet ✓     │  ├── get_progress ✅             │
│  ├── get_progress ✓          │  ├── download_work ✅            │
│  └── download_work ✓         │  └── chatbot ❌ (internal only)  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
pip install xmmersia-hubcore
```

## Quick Start

### Creating Your First Hub

```python
from hubcore import BaseHub, HubConfig, SkillExposure

class PracticeHub(BaseHub):
    
    def configure(self) -> HubConfig:
        return HubConfig(
            name="Practice Hub",
            slug="practice",
            description="Personalized derivative practice for ECON 3010",
            version="1.0.0"
        )
    
    def register_agents(self):
        return {
            "gaston": "http://localhost:8020",
            "lumiere": "http://localhost:8021",
            "le_marteau": "http://localhost:8022",
            "le_veilleur": "http://localhost:8023"
        }
    
    def define_skill_exposure(self) -> dict:
        return {
            "gaston": SkillExposure(
                exposed=["request_worksheet", "get_progress", "download_work"],
                hidden=["chatbot"],  # Used internally, not in UI
                internal=["chatbot"]  # Can still be called by hub logic
            ),
            "lumiere": SkillExposure(
                exposed=["check_answers"],
                hidden=["rubric_grade", "ocr_extract", "annotate_pdf"]
            ),
            "le_marteau": SkillExposure(
                exposed=[],  # Background agent, no direct exposure
                hidden=["generate_worksheet", "adapt_difficulty", "render_pdf"]
            ),
            "le_veilleur": SkillExposure(
                exposed=[],  # Background agent
                hidden=["create_profile", "log_session", "log_result", 
                        "get_progress", "check_pending", "get_student_data"]
            )
        }
    
    def define_ui_actions(self) -> list:
        """Define what users see in the Hub UI"""
        return [
            HubAction(
                id="generate_worksheet",
                label="Generate New Worksheet",
                icon="📝",
                agent="gaston",
                skill="request_worksheet"
            ),
            HubAction(
                id="view_progress",
                label="View My Progress",
                icon="📊",
                agent="gaston",
                skill="get_progress"
            ),
            HubAction(
                id="download_work",
                label="Download All My Work",
                icon="📥",
                agent="gaston",
                skill="download_work"
            ),
            HubAction(
                id="submit_work",
                label="Submit & Grade",
                icon="💡",
                agent="lumiere",
                skill="check_answers",
                precondition="check_pending"  # Must have pending worksheet
            )
        ]

# Run the hub
import asyncio

async def main():
    hub = PracticeHub()
    await hub.initialize()
    # Hub is now ready to serve at configured URL

asyncio.run(main())
```

## Core Components

### BaseHub

Abstract base class all hubs inherit from:

```python
class BaseHub(ABC):
    @abstractmethod
    def configure(self) -> HubConfig: pass
    
    @abstractmethod
    def register_agents(self) -> dict: pass
    
    @abstractmethod
    def define_skill_exposure(self) -> dict: pass
    
    @abstractmethod
    def define_ui_actions(self) -> list: pass
    
    async def initialize(self): pass
    async def handle_action(self, action_id, user, params): pass
    async def check_auth(self, user): pass
    async def check_consent(self, user): pass
```

### HubConfig

Configuration for hub behavior:

```python
@dataclass
class HubConfig:
    name: str                    # "Practice Hub"
    slug: str                    # "practice" -> xmmersia.com/practice
    description: str             # Shown to users
    version: str                 # Semantic version
    auth_required: bool = True   # Require login?
    consent_required: bool = True # Require consent form?
    theme: str = "organic"       # UI theme
```

### SkillExposure

Define which skills are visible/hidden:

```python
@dataclass
class SkillExposure:
    exposed: list[str]    # Shown in UI, callable by users
    hidden: list[str]     # Not shown, but agent has them
    internal: list[str]   # Can be called by hub logic, not users
```

### HubAction

A user-facing action in the Hub UI:

```python
@dataclass
class HubAction:
    id: str              # Unique identifier
    label: str           # "Generate New Worksheet"
    icon: str            # Emoji or icon class
    agent: str           # Which agent handles this
    skill: str           # Which skill to invoke
    precondition: str = None  # Optional check before allowing
```

## Authentication & Consent

HubCore provides built-in patterns for auth and consent:

```python
class PracticeHub(BaseHub):
    
    def configure_auth(self) -> AuthConfig:
        return AuthConfig(
            method="magic_link",
            email_domain="virginia.edu",
            session_duration_hours=24
        )
    
    def configure_consent(self) -> ConsentConfig:
        return ConsentConfig(
            required=True,
            text="This optional tool uses AI to generate practice problems...",
            data_usage=["OpenAI for grading", "UVA Box for storage"],
            revocable=True
        )
```

## Hub Lifecycle

```
1. User visits xmmersia.com/{hub-slug}
2. Hub checks authentication
   └── Not logged in? → Show login modal
3. Hub checks consent
   └── No consent? → Show consent form
4. Hub displays UI with available actions
5. User clicks action
6. Hub routes to appropriate agent via A2A
7. Agent processes and returns result
8. Hub displays result to user
```

## Directory Structure

```
Xmmersia-HubCore/
├── hubcore/
│   ├── __init__.py
│   ├── base_hub.py          # BaseHub abstract class
│   ├── config.py            # HubConfig, SkillExposure, HubAction
│   ├── router.py            # Routes actions to agents
│   ├── auth.py              # Authentication helpers
│   ├── consent.py           # Consent management
│   └── handlers/
│       ├── __init__.py
│       └── hub_handler.py   # HTTP handler for hub endpoints
├── examples/
│   └── practice_hub.py      # Practice Hub implementation
├── tests/
│   ├── test_base_hub.py
│   ├── test_skill_exposure.py
│   └── test_router.py
├── requirements.txt
├── setup.py
└── README.md
```

## Requirements

- Python >= 3.10
- xmmersia-agentcore >= 1.0.0
- xmmersia-protocol >= 0.2.5
- FastAPI (for hub server)
- httpx (for A2A client calls)

## Success Criteria

HubCore is successful when:
1. ✅ Practice Hub successfully uses it
2. ✅ New hubs can be created in hours, not days
3. ✅ Skill exposure works correctly (hidden skills stay hidden)
4. ✅ Auth and consent flows work seamlessly
5. ✅ Same agents can serve multiple hubs with different exposures

## Relationship to Other Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     XMMERSIA STACK                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  HubCore        →  Unified interfaces (Practice Hub, etc.)      │
│       ↓                                                         │
│  AgentCore      →  Agent patterns (BaseAgent, BaseSkill)        │
│       ↓                                                         │
│  A2A Protocol   →  Agent communication (JSON-RPC, tasks)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

*HubCore — Unified interfaces for the Xmmersia ecosystem*  
*"Every student can grow with the right guidance"*

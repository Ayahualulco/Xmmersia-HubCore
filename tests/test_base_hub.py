"""
Tests for HubCore BaseHub
"""

import pytest
from typing import Dict, List
from hubcore import BaseHub, HubConfig, SkillExposure, HubAction, UITheme


class TestHub(BaseHub):
    """Test implementation of BaseHub"""
    
    def configure(self) -> HubConfig:
        return HubConfig(
            name="Test Hub",
            slug="test",
            description="A test hub",
            version="1.0.0"
        )
    
    def register_agents(self) -> Dict[str, str]:
        return {
            "agent_a": "http://localhost:8001",
            "agent_b": "http://localhost:8002"
        }
    
    def define_skill_exposure(self) -> Dict[str, SkillExposure]:
        return {
            "agent_a": SkillExposure(
                exposed=["skill_1", "skill_2"],
                hidden=["skill_3"],
                internal=["skill_4"]
            ),
            "agent_b": SkillExposure(
                exposed=["skill_x"],
                hidden=["skill_y"]
            )
        }
    
    def define_ui_actions(self) -> List[HubAction]:
        return [
            HubAction(
                id="action_1",
                label="Action One",
                icon="🔥",
                agent="agent_a",
                skill="skill_1"
            ),
            HubAction(
                id="action_2",
                label="Action Two",
                icon="💧",
                agent="agent_b",
                skill="skill_x"
            )
        ]


def test_hub_creation():
    """Test hub can be created"""
    hub = TestHub()
    assert hub.initialized == False
    assert hub.config is None


@pytest.mark.asyncio
async def test_hub_initialization():
    """Test hub initialization"""
    hub = TestHub()
    await hub.initialize()
    
    assert hub.initialized == True
    assert hub.config.name == "Test Hub"
    assert hub.config.slug == "test"
    assert len(hub.agents) == 2
    assert len(hub.actions) == 2


@pytest.mark.asyncio
async def test_hub_card():
    """Test hub card generation"""
    hub = TestHub()
    await hub.initialize()
    
    card = hub.get_hub_card()
    
    assert card["name"] == "Test Hub"
    assert card["slug"] == "test"
    assert card["hubCoreVersion"] == "1.0.0"
    assert len(card["agents"]) == 2
    assert len(card["actions"]) == 2


@pytest.mark.asyncio
async def test_skill_exposure():
    """Test skill exposure rules"""
    hub = TestHub()
    await hub.initialize()
    
    agent_a = hub.agents["agent_a"]
    
    # Exposed skills are user callable
    assert agent_a.skill_exposure.is_user_callable("skill_1") == True
    assert agent_a.skill_exposure.is_user_callable("skill_2") == True
    
    # Hidden skills are not user callable
    assert agent_a.skill_exposure.is_user_callable("skill_3") == False
    
    # Internal skills are hub callable but not user callable
    assert agent_a.skill_exposure.is_user_callable("skill_4") == False
    assert agent_a.skill_exposure.is_hub_callable("skill_4") == True


@pytest.mark.asyncio
async def test_health_check():
    """Test health check"""
    hub = TestHub()
    
    # Not initialized
    health = await hub.health_check()
    assert health["status"] == "not_initialized"
    
    # After initialization
    await hub.initialize()
    health = await hub.health_check()
    
    assert health["status"] == "healthy"
    assert health["hub"] == "Test Hub"
    assert "agents" in health


def test_hub_config():
    """Test HubConfig"""
    config = HubConfig(
        name="My Hub",
        slug="my-hub",
        description="My description",
        version="2.0.0",
        theme=UITheme.DARK,
        course="CS 101"
    )
    
    assert config.name == "My Hub"
    assert config.theme == UITheme.DARK
    assert config.auth_required == True  # Default
    
    d = config.to_dict()
    assert d["theme"] == "dark"


def test_skill_exposure_class():
    """Test SkillExposure class"""
    exposure = SkillExposure(
        exposed=["a", "b"],
        hidden=["c"],
        internal=["d"]
    )
    
    assert exposure.is_user_callable("a") == True
    assert exposure.is_user_callable("c") == False
    assert exposure.is_user_callable("d") == False
    
    assert exposure.is_hub_callable("a") == True
    assert exposure.is_hub_callable("d") == True
    assert exposure.is_hub_callable("c") == False
    
    assert exposure.all_available() == ["a", "b", "d"]


def test_hub_action():
    """Test HubAction"""
    action = HubAction(
        id="test",
        label="Test Action",
        icon="🧪",
        agent="test_agent",
        skill="test_skill",
        precondition="check_something"
    )
    
    assert action.id == "test"
    assert action.precondition == "check_something"
    
    d = action.to_dict()
    assert d["id"] == "test"
    assert d["precondition"] == "check_something"

"""
HubCore Router
Routes user actions to appropriate agents via A2A protocol.
"""

from typing import Dict, List, Any, Optional
import httpx
import json
import logging
from datetime import datetime
import uuid

from .config import HubAction, AgentConnection

logger = logging.getLogger(__name__)


class HubRouter:
    """
    Routes hub actions to appropriate agents via A2A protocol.
    
    The router:
    1. Receives action requests from the hub
    2. Finds the appropriate agent
    3. Sends A2A message to invoke the skill
    4. Returns the result
    """
    
    def __init__(
        self, 
        agents: Dict[str, AgentConnection],
        actions: List[HubAction]
    ):
        self.agents = agents
        self.actions = actions
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def route_action(
        self,
        action: HubAction,
        user_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route an action to its target agent.
        
        Args:
            action: The HubAction to execute
            user_id: The user making the request
            params: Parameters for the skill
            
        Returns:
            Result from the agent
        """
        agent = self.agents.get(action.agent)
        if not agent:
            raise ValueError(f"Agent not found: {action.agent}")
        
        # Check if skill is callable
        if not agent.skill_exposure.is_hub_callable(action.skill):
            raise PermissionError(
                f"Skill {action.skill} is not available for agent {action.agent}"
            )
        
        logger.info(f"Routing action '{action.id}' to {action.agent}.{action.skill}")
        
        # Build A2A message
        message = self._build_a2a_message(action.skill, user_id, params)
        
        # Send to agent
        try:
            result = await self._send_to_agent(agent.url, message)
            logger.info(f"Action '{action.id}' completed successfully")
            return result
        except Exception as e:
            logger.error(f"Action '{action.id}' failed: {e}")
            raise
    
    async def check_precondition(
        self,
        precondition_skill: str,
        user_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check a precondition before allowing an action.
        
        Preconditions are skills that return {"satisfied": bool, "message": str}
        
        Args:
            precondition_skill: The skill to check (format: "agent.skill" or just "skill")
            user_id: The user to check for
            params: Additional parameters
            
        Returns:
            Dict with satisfied status and message
        """
        # Parse agent and skill from precondition
        if "." in precondition_skill:
            agent_name, skill_name = precondition_skill.split(".", 1)
        else:
            # Default to le_veilleur for precondition checks
            agent_name = "le_veilleur"
            skill_name = precondition_skill
        
        agent = self.agents.get(agent_name)
        if not agent:
            logger.warning(f"Precondition agent not found: {agent_name}")
            return {"satisfied": True}  # Fail open if agent not found
        
        # Build check message
        check_params = {
            "student_id": user_id,
            **params
        }
        
        message = self._build_a2a_message(skill_name, user_id, check_params)
        
        try:
            result = await self._send_to_agent(agent.url, message)
            
            # Interpret result as precondition check
            if "has_pending" in result:
                # check_pending skill
                return {
                    "satisfied": result.get("has_pending", False),
                    "message": result.get("message", "No pending worksheet found"),
                    "action_required": "generate_worksheet" if not result.get("has_pending") else None
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Precondition check failed: {e}")
            return {"satisfied": False, "message": str(e)}
    
    async def call_agent_skill(
        self,
        agent_name: str,
        skill_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Directly call an agent's skill (for internal hub use).
        
        This bypasses user-callable checks, allowing hub logic
        to call internal skills.
        
        Args:
            agent_name: Name of the agent
            skill_id: ID of the skill to invoke
            params: Parameters for the skill
            
        Returns:
            Result from the agent
        """
        agent = self.agents.get(agent_name)
        if not agent:
            raise ValueError(f"Agent not found: {agent_name}")
        
        message = self._build_a2a_message(skill_id, "hub", params)
        return await self._send_to_agent(agent.url, message)
    
    def _build_a2a_message(
        self,
        skill_id: str,
        user_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build an A2A protocol message.
        
        Uses JSON-RPC 2.0 format with message/send method.
        """
        message_id = str(uuid.uuid4())
        
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "data",
                            "data": {
                                "skill": skill_id,
                                "parameters": {
                                    "user_id": user_id,
                                    **params
                                }
                            }
                        }
                    ],
                    "messageId": message_id,
                    "kind": "message"
                }
            }
        }
    
    async def _send_to_agent(
        self,
        agent_url: str,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send A2A message to an agent.
        
        Args:
            agent_url: Agent's base URL
            message: A2A message to send
            
        Returns:
            Extracted result from agent response
        """
        try:
            response = await self.client.post(
                agent_url,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract result from A2A response
            if "result" in data:
                return self._extract_result(data["result"])
            elif "error" in data:
                raise Exception(f"Agent error: {data['error']}")
            else:
                return data
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling agent: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from agent: {e}")
            raise
    
    def _extract_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract meaningful result from A2A response.
        
        A2A responses have artifacts with parts containing data.
        """
        # If result has artifacts, extract data from first artifact
        if "artifacts" in result:
            artifacts = result["artifacts"]
            if artifacts and len(artifacts) > 0:
                parts = artifacts[0].get("parts", [])
                for part in parts:
                    if part.get("kind") == "data":
                        return part.get("data", {})
        
        # Otherwise return result as-is
        return result
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

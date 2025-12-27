"""
Training Hub - First Xmmersia Hub Implementation

This is a complete example of implementing a Hub using HubCore.
The Training Hub provides personalized derivative training for ECON 3010 students.
"""

from hubcore import (
    BaseHub,
    HubConfig,
    SkillExposure,
    HubAction,
    AuthConfig,
    ConsentConfig,
    UITheme
)
from hubcore.handlers import create_hub_app

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class TrainingHub(BaseHub):
    """
    Training Hub - Personalized derivative training for ECON 3010.
    
    Agents:
    - GASTON (Conductor): Orchestrates training, shows progress
    - LUMIÈRE (Specialist): Grades submissions
    - Le Marteau (Background): Generates worksheets
    - Le Veilleur (Background): Tracks progress, manages storage
    
    Skills exposed to users:
    - GASTON: request_worksheet, get_progress, download_work
    - LUMIÈRE: check_answers
    
    Skills hidden (but available):
    - GASTON: chatbot (used internally)
    - LUMIÈRE: rubric_grade, ocr_extract, annotate_pdf
    - Le Marteau: all (background only)
    - Le Veilleur: all (background only)
    """
    
    def configure(self) -> HubConfig:
        return HubConfig(
            name="Training Hub",
            slug="training",
            description="Personalized derivative training for ECON 3010",
            version="1.0.0",
            auth_required=True,
            consent_required=True,
            theme=UITheme.ORGANIC,
            tagline="Every student can grow with the right guidance",
            icon="🎓",
            course="ECON 3010",
            semester="26Sp"
        )
    
    def register_agents(self) -> Dict[str, str]:
        """Register the 4 Training Hub agents"""
        return {
            "gaston": "http://localhost:8020",
            "lumiere": "http://localhost:8021",
            "le_marteau": "http://localhost:8022",
            "le_veilleur": "http://localhost:8023"
        }
    
    def define_skill_exposure(self) -> Dict[str, SkillExposure]:
        """Define which skills are exposed in Training Hub"""
        return {
            "gaston": SkillExposure(
                exposed=["request_worksheet", "get_progress", "download_work"],
                hidden=[],
                internal=["chatbot"]  # Hub can use chatbot internally
            ),
            "lumiere": SkillExposure(
                exposed=["check_answers"],
                hidden=["rubric_grade", "annotate_pdf"],
                internal=["ocr_extract"]  # Used internally by check_answers
            ),
            "le_marteau": SkillExposure(
                exposed=[],  # Background agent
                hidden=[],
                internal=["generate_worksheet", "adapt_difficulty", "render_pdf"]
            ),
            "le_veilleur": SkillExposure(
                exposed=[],  # Background agent
                hidden=[],
                internal=[
                    "create_profile",
                    "log_session", 
                    "log_result",
                    "get_progress",
                    "check_pending",
                    "get_student_data",
                    "get_class_overview"
                ]
            )
        }
    
    def define_ui_actions(self) -> List[HubAction]:
        """Define the user-facing actions for Training Hub"""
        return [
            # GASTON actions
            HubAction(
                id="generate_worksheet",
                label="Generate New Worksheet",
                icon="📝",
                agent="gaston",
                skill="request_worksheet",
                description="Get personalized training problems based on your weak areas",
                primary=True,
                position=1,
                group="gaston"
            ),
            HubAction(
                id="view_progress",
                label="View My Progress",
                icon="📊",
                agent="gaston",
                skill="get_progress",
                description="See how you're doing (same view as TAs)",
                position=2,
                group="gaston"
            ),
            HubAction(
                id="download_work",
                label="Download All My Work",
                icon="📥",
                agent="gaston",
                skill="download_work",
                description="Download all your worksheets and reports",
                position=3,
                group="gaston"
            ),
            
            # LUMIÈRE actions
            HubAction(
                id="submit_work",
                label="Submit & Grade",
                icon="💡",
                agent="lumiere",
                skill="check_answers",
                description="Upload your completed worksheet for instant feedback",
                precondition="le_veilleur.check_pending",  # Must have pending worksheet
                primary=True,
                position=1,
                group="lumiere"
            )
        ]
    
    def configure_auth(self) -> AuthConfig:
        """Configure UVA email authentication"""
        return AuthConfig(
            method="magic_link",
            email_domain="virginia.edu",
            session_duration_hours=24
        )
    
    def configure_consent(self) -> ConsentConfig:
        """Configure consent for Training Hub"""
        return ConsentConfig(
            required=True,
            title="Training Hub Consent",
            text="""
This optional tool uses AI to:
• Generate personalized training problems
• Grade your work and provide feedback
• Track your progress over time

Your data is stored securely in UVA Box.
This is OPTIONAL training — not required for your grade.
            """.strip(),
            data_usage=[
                "Generate personalized training problems",
                "Grade submissions and provide feedback",
                "Track progress over time"
            ],
            data_shared_with=[
                "Your professor (Dr. Santugini)",
                "Course TAs",
                "AI services (OpenAI) for grading"
            ],
            revocable=True,
            optional_participation=True
        )
    
    # ─────────────────────────────────────────────────────────
    # Hub Lifecycle Hooks
    # ─────────────────────────────────────────────────────────
    
    async def on_initialize(self):
        """Called after hub initialization"""
        logger.info("Training Hub initialized")
        logger.info(f"Course: {self.config.course}")
        logger.info(f"Semester: {self.config.semester}")
    
    async def on_user_consent(self, user_id: str):
        """
        Called when a user gives consent.
        Create their profile in Le Veilleur.
        """
        logger.info(f"Creating profile for {user_id}")
        
        # Call Le Veilleur to create student profile
        await self.router.call_agent_skill(
            "le_veilleur",
            "create_profile",
            {
                "student_id": user_id,
                "course": self.config.course,
                "semester": self.config.semester
            }
        )
    
    async def on_action_start(self, action_id: str, user_id: str, params: dict):
        """Log action start"""
        logger.info(f"Action '{action_id}' started by {user_id}")
    
    async def on_action_complete(self, action_id: str, user_id: str, result: dict):
        """Log action completion"""
        logger.info(f"Action '{action_id}' completed for {user_id}")


# ─────────────────────────────────────────────────────────────
# Run the Hub
# ─────────────────────────────────────────────────────────────

async def main():
    """Run Training Hub as standalone server"""
    from fastapi import FastAPI
    import uvicorn
    
    # Create hub
    hub = TrainingHub()
    await hub.initialize()
    
    # Create FastAPI app
    app = FastAPI(
        title="Training Hub",
        description="Personalized derivative training for ECON 3010",
        version="1.0.0"
    )
    
    # Add hub routes
    app.include_router(create_hub_app(hub), prefix="/api")
    
    # Add static files / frontend here in production
    
    # Health check at root
    @app.get("/")
    async def root():
        return {"hub": "Training Hub", "status": "running"}
    
    # Run server
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

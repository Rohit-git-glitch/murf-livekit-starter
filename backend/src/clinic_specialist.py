import asyncio
import json
import logging
from typing import Any

from livekit.agents import Agent, function_tool
from health_access import find_nearby_health_facilities
from prompt import CLINIC_SPECIALIST_PROMPT

logger = logging.getLogger("clinic_specialist")


class ClinicSpecialistAgent(Agent):
    """Specialist agent dedicated to clinic and appointment assistance."""

    def __init__(
        self,
        caller_user_id: str | None = None,
        initial_caller_memory: dict | None = None,
        caller_info: dict | None = None,
        handoff_context: str | dict | None = None,
        call_outcome_tracker: Any = None,
    ) -> None:
        self.caller_user_id = caller_user_id
        self.caller_info = caller_info or {}
        self.handoff_context = handoff_context
        self.call_outcome_tracker = call_outcome_tracker

        lookercaller = (
            self.caller_info.get("lookercaller")
            or self.caller_info.get("lookup_caller")
            or initial_caller_memory
        )

        context_parts = [
            "\n\n========================",
            "SPECIALIST SESSION & CALLER CONTEXT",
            "========================",
            f"Caller User ID: `{caller_user_id or 'Unknown'}`",
        ]

        if lookercaller:
            memory_json = json.dumps(lookercaller, ensure_ascii=False)
            context_parts.append(f"Stored Caller Record: {memory_json}")
        else:
            context_parts.append("Stored Caller Record: None")

        if handoff_context:
            if isinstance(handoff_context, dict):
                ctx_str = json.dumps(handoff_context, ensure_ascii=False)
            else:
                ctx_str = str(handoff_context)
            context_parts.extend([
                "\n========================",
                "HANDOFF CONTEXT FROM MAIN AGENT",
                "========================",
                f"Transfer Details & Reason: {ctx_str}",
                "Instructions: Continue assisting the user with this clinic/appointment request naturally. Do NOT ask the caller to repeat their medical issue or basic facts already listed above.",
            ])

        instructions = CLINIC_SPECIALIST_PROMPT + "\n".join(context_parts)
        super().__init__(instructions=instructions)

    @function_tool
    async def find_nearby_health_facilities(
        self, location: str, limit: int = 3
    ) -> dict:
        """Find nearby PHCs, clinics, doctors, and hospitals from live OpenStreetMap data. Use when the caller asks where to find a clinic or requests nearby healthcare options."""
        return await asyncio.to_thread(find_nearby_health_facilities, location, limit)

    @function_tool
    async def handoff_to_main_agent(
        self, reason: str = "User requested general health assistance"
    ) -> dict:
        """Transfer the conversation back to Anisha (main Health Access agent) when the request is outside clinic/appointment scope (e.g. general health questions or symptom triage)."""
        logger.info("Transferring back to main agent Anisha: %s", reason)
        if hasattr(self, "session") and self.session:
            session_room = getattr(self.session, "room", None)
            if session_room and getattr(session_room, "local_participant", None):
                try:
                    asyncio.create_task(
                        session_room.local_participant.set_attributes({
                            "active_agent": "anisha",
                            "agent_name": "Anisha",
                            "agent_role": "Health Access Assistant",
                        })
                    )
                except Exception:
                    logger.exception("Failed to set participant attributes for Anisha")

            # Lazy import to prevent circular dependency
            from agent import Assistant
            main_agent = Assistant(
                caller_user_id=self.caller_user_id,
                caller_info=self.caller_info,
                call_outcome_tracker=self.call_outcome_tracker,
            )
            self.session.update_agent(main_agent)
            return {
                "status": "transferred",
                "agent": "Anisha",
                "message": "Connected back to Anisha, main Health Access agent.",
            }
        return {"status": "error", "message": "No active session available for transfer."}

    def _is_current_caller(self, user_id: str) -> bool:
        return bool(self.caller_user_id and user_id == self.caller_user_id)


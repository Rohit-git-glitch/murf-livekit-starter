import asyncio
import pytest
from dotenv import load_dotenv
from livekit.agents import AgentSession, llm
from livekit.plugins import google

from agent import Assistant
from clinic_specialist import ClinicSpecialistAgent
from prompt import CLINIC_SPECIALIST_PROMPT

load_dotenv(".env.local")


def _llm() -> llm.LLM:
    return google.LLM(model="gemini-3.5-flash-lite")


@pytest.mark.asyncio
async def test_main_agent_path_handles_symptoms_without_handoff() -> None:
    """TEST 1: Main agent Anisha handles symptom questions directly without handoff."""
    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        main_agent = Assistant(caller_user_id="user_symptom_test")
        await session.start(main_agent)

        result = await session.run(
            user_input="I have a headache and mild fever. What should I do?"
        )

        # Ensure active agent remains Anisha
        assert isinstance(session.current_agent, Assistant)
        assert not isinstance(session.current_agent, ClinicSpecialistAgent)


@pytest.mark.asyncio
async def test_specialist_path_triggers_handoff_on_clinic_request() -> None:
    """TEST 2: Main agent Anisha hands off conversation to ClinicSpecialistAgent on appointment request."""
    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        caller_info = {
            "lookup_caller": {
                "name": "Rahul",
                "language_preference": "English",
                "facts": {"age_band": "adult"},
            }
        }
        main_agent = Assistant(
            caller_user_id="user_rahul_123",
            caller_info=caller_info,
        )
        await session.start(main_agent)

        # Trigger clinic appointment booking
        result = await session.run(
            user_input="I want to book an appointment at a clinic."
        )

        # Agent should have transferred to ClinicSpecialistAgent
        assert isinstance(session.current_agent, ClinicSpecialistAgent)
        assert session.current_agent.caller_user_id == "user_rahul_123"


@pytest.mark.asyncio
async def test_handoff_tool_execution_directly() -> None:
    """Verify handoff tool logic switches agent on session directly."""
    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        caller_info = {
            "lookercaller": {
                "name": "Priya",
                "language_preference": "Hindi",
            }
        }
        main_agent = Assistant(
            caller_user_id="user_priya_456",
            caller_info=caller_info,
        )
        await session.start(main_agent)

        res = await main_agent.handoff_to_clinic_specialist(
            request_summary="Priya wants to visit an eye clinic tomorrow morning.",
            preferred_clinic="Vision Eye Care",
            preferred_date="Tomorrow",
            preferred_time="10:00 AM",
        )

        assert res["status"] == "transferred"
        assert res["specialist"] == "Clinic and Appointment Specialist"
        assert isinstance(session.current_agent, ClinicSpecialistAgent)
        assert session.current_agent.caller_user_id == "user_priya_456"
        assert "Priya" in session.current_agent._instructions
        assert "Vision Eye Care" in session.current_agent._instructions


def test_specialist_context_and_identity_preservation() -> None:
    """TEST 3: Verify specialist receives caller identity, memory, and handoff context."""
    caller_info = {
        "lookercaller": {
            "name": "Rahul",
            "language_preference": "English",
            "facts": {"age_band": "adult"},
        }
    }
    handoff_context = {
        "request_summary": "Rahul has had a fever for two days and needs a clinic appointment.",
        "preferred_clinic": "City Health Clinic",
    }

    specialist = ClinicSpecialistAgent(
        caller_user_id="user_rahul_123",
        caller_info=caller_info,
        handoff_context=handoff_context,
    )

    instructions = specialist._instructions
    assert "user_rahul_123" in instructions
    assert "Rahul" in instructions
    assert "fever for two days" in instructions
    assert "City Health Clinic" in instructions


def test_session_and_caller_isolation() -> None:
    """TEST 4: Verify caller isolation is maintained by the specialist agent."""
    specialist_caller_a = ClinicSpecialistAgent(caller_user_id="caller_A")
    specialist_caller_b = ClinicSpecialistAgent(caller_user_id="caller_B")

    assert specialist_caller_a._is_current_caller("caller_A") is True
    assert specialist_caller_a._is_current_caller("caller_B") is False

    assert specialist_caller_b._is_current_caller("caller_B") is True
    assert specialist_caller_b._is_current_caller("caller_A") is False


@pytest.mark.asyncio
async def test_specialist_can_handoff_back_to_main_agent() -> None:
    """TEST 5: Specialist can transfer session back to main agent if requested."""
    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        specialist = ClinicSpecialistAgent(
            caller_user_id="user_transfer_back",
            handoff_context="Appointment inquiry",
        )
        await session.start(specialist)

        # Call handoff tool directly
        res = await specialist.handoff_to_main_agent(
            reason="Caller asked for general symptom advice"
        )
        assert res["status"] == "transferred"
        assert res["agent"] == "Anisha"
        assert isinstance(session.current_agent, Assistant)
        assert session.current_agent.caller_user_id == "user_transfer_back"

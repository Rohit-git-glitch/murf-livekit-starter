import asyncio
import json
import logging
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    UserInputTranscribedEvent,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from analytics_api import start_analytics_server
from call_analytics import CallAnalyticsStore, CallOutcomeTracker
from caller_memory import CallerMemoryStore
from escalation import EscalationStore
from health_access import assess_symptom_urgency, find_nearby_health_facilities
from prompt import SYSTEM_PROMPT

logger = logging.getLogger("agent")

load_dotenv(".env.local")

DEFAULT_MEMORY_DB = Path(__file__).resolve().parent.parent / "data" / "callers.sqlite3"
memory_store = CallerMemoryStore(os.getenv("CALLER_MEMORY_DB", DEFAULT_MEMORY_DB))
escalation_store = EscalationStore(os.getenv("CALLER_MEMORY_DB", DEFAULT_MEMORY_DB))
analytics_store = CallAnalyticsStore(os.getenv("CALLER_MEMORY_DB", DEFAULT_MEMORY_DB))


class Assistant(Agent):
    def __init__(
        self,
        caller_user_id: str | None = None,
        initial_caller_memory: dict | None = None,
        caller_info: dict | None = None,
        call_outcome_tracker: CallOutcomeTracker | None = None,
    ) -> None:
        self.caller_user_id = caller_user_id
        self.caller_info = caller_info or {}
        self.call_outcome_tracker = call_outcome_tracker

        # Extract lookup_caller memory and specific instructions for the caller
        lookercaller = (
            self.caller_info.get("lookercaller")
            or self.caller_info.get("lookup_caller")
            or initial_caller_memory
        )
        call_trigger = self.caller_info.get("call_trigger", "Health Access Outreach")
        instructions = self.caller_info.get("instructions", "")

        caller_context_parts = [
            "\n\n========================",
            "CALLER INFO & CALL INSTRUCTIONS",
            "========================",
            f"Caller User ID: `{caller_user_id or 'Unknown'}`",
            f"Health Access Trigger: {call_trigger}",
        ]

        if lookercaller:
            memory_json = json.dumps(lookercaller, ensure_ascii=False)
            caller_context_parts.extend([
                f"Lookup Caller Memory Record (lookercaller): {memory_json}",
                "Instructions for Memory: Welcome the caller naturally by name if present in stored memory. Use these facts only when relevant and do not claim anything beyond this record."
            ])
        else:
            caller_context_parts.append("Lookup Caller Memory Record (lookercaller): None (No prior consented memory record found)")

        if instructions:
            caller_context_parts.extend([
                "\nInstructions for the Caller:",
                instructions
            ])

        caller_context = "\n".join(caller_context_parts)

        super().__init__(
            instructions=SYSTEM_PROMPT + caller_context
        )

    @function_tool
    async def lookup_caller(self, user_id: str) -> dict:
        """Look up the current caller's consented structured memory by user ID."""
        if not self._is_current_caller(user_id):
            return {"status": "not_found"}
        try:
            record = memory_store.lookup(user_id)
        except sqlite3.Error:
            logger.exception("Caller memory lookup failed")
            return {"status": "unavailable"}
        return (
            {"status": "found", "caller": record} if record else {"status": "not_found"}
        )

    @function_tool
    async def save_caller_memory(
        self,
        user_id: str,
        consent_given: bool,
        name: str | None = None,
        language_preference: str | None = None,
        age_band: str | None = None,
        ongoing_conditions: str | None = None,
        last_triage_outcome: str | None = None,
    ) -> dict:
        """Save only consented, structured Health Access memory for the current caller."""
        if not consent_given:
            return {"status": "not_saved", "reason": "explicit_consent_required"}
        if not self._is_current_caller(user_id):
            return {"status": "not_saved", "reason": "invalid_caller"}
        try:
            caller = memory_store.save(
                user_id=user_id,
                name=name,
                language_preference=language_preference,
                age_band=age_band,
                ongoing_conditions=ongoing_conditions,
                last_triage_outcome=last_triage_outcome,
            )
        except (sqlite3.Error, ValueError):
            logger.exception("Caller memory save failed")
            return {"status": "not_saved"}
        return {"status": "saved", "caller": caller}

    @function_tool
    async def assess_symptom_urgency(
        self,
        symptoms: str,
        duration: str | None = None,
        age_band: str | None = None,
        pregnancy_or_high_risk: bool = False,
    ) -> dict:
        """Assess reported symptoms for a conservative, non-diagnostic urgency level. Use when a caller asks how urgently they should seek care or reports symptoms. Do not use for diagnosis, medicines, or emergencies requiring immediate escalation."""
        return await asyncio.to_thread(
            assess_symptom_urgency,
            symptoms,
            duration,
            age_band,
            pregnancy_or_high_risk,
        )

    @function_tool
    async def create_escalation(
        self,
        reason: str,
        current_issue: str,
        what_was_checked: str,
        urgency: str,
        language: str,
        caller_confirmed_sharing: bool,
        caller_name: str | None = None,
        preferred_follow_up: str | None = None,
    ) -> dict:
        """Create a concise human-help request for the current caller.

        Call this ONLY after the caller has clearly agreed to share the listed
        information. Set caller_confirmed_sharing to true only for that clear,
        current-turn consent. Valid reasons are red_flag_symptom and
        diagnosis_request; urgency is high, urgent, or normal. Do not include
        transcripts, passwords, OTPs, PINs, account numbers, or detailed notes.
        """
        if not self.caller_user_id:
            return {
                "success": False,
                "status": "not_created",
                "reason": "invalid_caller",
            }
        return await asyncio.to_thread(
            escalation_store.create,
            caller_id=self.caller_user_id,
            caller_name=caller_name,
            reason=reason,
            current_issue=current_issue,
            what_was_checked=what_was_checked,
            urgency=urgency,
            language=language,
            preferred_follow_up=preferred_follow_up,
            consent_given=caller_confirmed_sharing,
        )

    @function_tool
    async def record_safe_guidance_provided(self) -> dict:
        """Mark this call successful only when your current reply gives safe general guidance and a suitable next step. Do not call for greetings, incomplete conversations, or unanswered questions."""
        if self.call_outcome_tracker is None:
            return {"status": "unavailable"}
        self.call_outcome_tracker.mark_safe_guidance_provided()
        return {"status": "recorded"}

    @function_tool
    async def record_escalation_communicated(self) -> dict:
        """Mark this call successful only after you clearly direct the caller to appropriate emergency, medical, or human help. Do not call before communicating that direction."""
        if self.call_outcome_tracker is None:
            return {"status": "unavailable"}
        self.call_outcome_tracker.mark_escalation_communicated()
        return {"status": "recorded"}

    @function_tool
    async def find_nearby_health_facilities(
        self, location: str, limit: int = 3
    ) -> dict:
        """Find nearby PHCs, clinics, doctors, and hospitals from live OpenStreetMap data. Use only when the caller asks where to go or requests nearby care and has provided a PIN code, locality, town, or landmark. Results are map listings, not confirmed availability."""
        return await asyncio.to_thread(find_nearby_health_facilities, location, limit)

    def _is_current_caller(self, user_id: str) -> bool:
        return bool(self.caller_user_id and user_id == self.caller_user_id)


def lookup_startup_memory(user_id: str) -> dict | None:
    """Perform the same consented caller lookup before the agent's first reply."""
    try:
        record = memory_store.lookup(user_id)
    except sqlite3.Error:
        logger.exception("Caller memory startup lookup failed")
        return None
    logger.info("Caller memory startup lookup: %s", "found" if record else "not found")
    return record


server = AgentServer()


def prewarm(proc: JobProcess):
    # Load the VAD once per worker.  This is required to detect the end of a
    # user's turn and start the LLM/TTS response.
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    try:
        memory_store.initialize()
        escalation_store.initialize()
        analytics_store.initialize()
    except sqlite3.Error:
        logger.exception("Caller data database initialization failed")

    # Connect before reading participant identity; Room participants are not
    # available until the LiveKit context is connected.
    await ctx.connect()
    participant = await ctx.wait_for_participant()
    caller_user_id = participant.identity
    initial_caller_memory = lookup_startup_memory(caller_user_id)

    # Parse metadata passed during outbound/inbound call initiation
    metadata_payload = {}
    if participant.metadata:
        try:
            metadata_payload = json.loads(participant.metadata)
        except json.JSONDecodeError:
            metadata_payload = {"instructions": participant.metadata}
    elif ctx.room.metadata:
        try:
            metadata_payload = json.loads(ctx.room.metadata)
        except json.JSONDecodeError:
            metadata_payload = {"instructions": ctx.room.metadata}

    call_trigger = metadata_payload.get("call_trigger") or (
        participant.attributes.get("call_trigger")
        if participant.attributes
        else "Health Access Outreach"
    )
    instructions = metadata_payload.get("instructions") or (
        participant.attributes.get("instructions")
        if participant.attributes
        else ""
    )

    # Construct caller_info dictionary containing lookercaller/lookup_caller and instructions for caller
    caller_info = {
        "caller_user_id": caller_user_id,
        "lookup_caller": initial_caller_memory,
        "lookercaller": initial_caller_memory,
        "call_trigger": call_trigger,
        "instructions": instructions,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    call_outcome_tracker = CallOutcomeTracker()
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3", language="multi"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
            voice="hi-IN-anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        # VAD and turn detection determine when the user is done speaking.
        # Disabling both prevents voice replies from being generated.
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # Begin generating promptly once the end of a turn is detected.
        preemptive_generation=True,
    )

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev: UserInputTranscribedEvent):
        transcript = ev.transcript.strip().lower()

        if not transcript:
            return

        # Detect native Hindi (Devanagari)
        has_devanagari = any(0x0900 <= ord(c) <= 0x097F for c in transcript)

        words = set(transcript.split())

        hindi_keywords = {
            "kya", "hai", "haan", "mera", "meri", "mujhe",
            "hum", "aap", "tum", "ka", "ki", "ke",
            "mein", "main", "se", "aur", "par",
            "kyun", "kab", "kaise", "acha", "theek",
            "dhanyavaad", "shukriya"
        }

        marathi_keywords = {
            "namaskar", "majha", "majhi", "mala",
            "tumhi", "kay", "kasa", "kashi",
            "kuthe", "aahe", "ahe", "barobar",
            "krupaya"
        }

        health_keywords = {
            "fever", "cold", "cough", "headache",
            "pain", "stomach", "vomiting",
            "medicine", "doctor", "hospital",
            "blood", "pressure", "bp",
            "sugar", "diabetes", "heart",
            "chest", "breathing", "infection",
            "covid", "allergy", "stress",
            "anxiety", "depression"
        }

        hindi_health_keywords = {
            "bukhar", "khansi", "sardi",
            "dard", "sar", "pet",
            "dawai", "aspatal",
            "saans", "chakkar",
            "ulti", "kamjori",
            "tabiyat"
        }

        english_words = bool(words & health_keywords)
        hindi_words = bool(words & hindi_keywords)

        if has_devanagari:
            language = "Hindi"
        elif bool(words & marathi_keywords):
            language = "Marathi"
        elif english_words and hindi_words:
            language = "Hinglish"
        elif hindi_words:
            language = "Hindi"
        else:
            language = "English"

        logger.info(f"Detected Language: {language}")

        if english_words or bool(words & hindi_health_keywords):
            logger.info("Healthcare query detected.")
        else:
            logger.info("General conversation detected.")

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(
            caller_user_id=caller_user_id,
            initial_caller_memory=initial_caller_memory,
            caller_info=caller_info,
            call_outcome_tracker=call_outcome_tracker,
        ),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    async def record_completed_call(_: str) -> None:
        """Persist one final outcome even when the caller disconnects unexpectedly."""
        try:
            analytics_store.record_call_outcome(
                call_id=ctx.room.name,
                outcome=call_outcome_tracker.outcome,
            )
        except (sqlite3.Error, ValueError):
            logger.exception("Call outcome storage failed for room %s", ctx.room.name)

    ctx.add_shutdown_callback(record_completed_call)

    # For outbound calls, the agent must speak first (patient is receiving the call).
    # Detect outbound calls by checking if a call_trigger was set via metadata.
    is_outbound = bool(
        metadata_payload.get("call_trigger")
        or (participant.attributes and participant.attributes.get("call_trigger"))
    )
    if is_outbound:
        logger.info(
            f"Outbound call detected (trigger: {call_trigger}). Agent speaking first."
        )
        await session.generate_reply(
            instructions="You are initiating an outbound call. Greet the patient warmly, introduce yourself as Anisha from Aarogya AI, and immediately proceed with your call trigger instructions (medication reminder, vaccination reminder, or triage follow-up). Keep the greeting brief and natural."
        )

if __name__ == "__main__":
    try:
        analytics_store.initialize()
        analytics_host = os.getenv("ANALYTICS_HOST", "127.0.0.1")
        analytics_port = int(os.getenv("ANALYTICS_PORT", "8081"))
        start_analytics_server(analytics_store, analytics_host, analytics_port)
    except (sqlite3.Error, ValueError):
        logger.exception("Call analytics API startup failed")
    cli.run_app(server)

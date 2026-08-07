import logging

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
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from prompt import SYSTEM_PROMPT

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
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
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
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
        agent=Assistant(),
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

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)

import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from livekit import api

# Load environment variables
load_dotenv(".env.local")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbound_call")

# SIP Trunk ID configuration for LiveKit SIP Outbound
sip_trunk_id = os.getenv("LIVEKIT_SIP_TRUNK_ID")


# Health Access Call Triggers & Default Instructions
HEALTH_ACCESS_TRIGGERS = {
    "medication_reminder": {
        "title": "Medication Reminder",
        "instructions": (
            "You are making an outbound call to remind the patient to take "
            "their prescribed medication on schedule. Warmly greet them, ask "
            "if they have taken their scheduled dose, check if they are "
            "experiencing any side effects, and encourage medication "
            "adherence. Do not alter dosages or prescribe medicines."
        ),
    },
    "vaccination_reminder": {
        "title": "Vaccination Reminder",
        "instructions": (
            "You are making an outbound call to remind the patient of an "
            "upcoming or due vaccination drive/dose. Warmly greet them, "
            "explain the general benefits and safety of the vaccine, check "
            "if they have scheduled an appointment, and offer to help them "
            "find a nearby health facility using "
            "`find_nearby_health_facilities` if needed."
        ),
    },
    "triage_followup": {
        "title": "Follow-up after Triage Escalation",
        "instructions": (
            "You are making an outbound follow-up call after a recent urgent "
            "triage escalation. Express empathy, check on their current "
            "symptoms and well-being, verify if they visited a clinic/doctor "
            "or received emergency care, and perform a symptom re-assessment "
            "using `assess_symptom_urgency` or trigger emergency escalation "
            "if critical symptoms persist."
        ),
    },
}


async def make_outbound_call(
    phone_number: str,
    room_name: str | None = None,
    call_trigger: str = "medication_reminder",
    caller_name: str | None = None,
    caller_user_id: str | None = None,
    custom_instructions: str | None = None,
) -> str:
    """Initiates an outbound SIP call using LiveKit SIP API.

    Args:
        phone_number: SIP URI or phone number to call.
        room_name: Optional LiveKit room name. If None, auto-generated.
        call_trigger: Trigger type.
        caller_name: Optional name of the recipient.
        caller_user_id: Optional user ID for memory lookup.
        custom_instructions: Optional override/additional instructions.

    Returns:
        The LiveKit room name created for the call.
    """

    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not livekit_url or not api_key or not api_secret:
        raise ValueError(
            "Missing LIVEKIT_URL, LIVEKIT_API_KEY, or LIVEKIT_API_SECRET "
            "in environment"
        )

    if not sip_trunk_id:
        raise ValueError(
            "Missing LIVEKIT_SIP_TRUNK_ID in environment"
        )

    if not phone_number:
        raise ValueError(
            "No SIP destination provided. Set LINPHONE_SIP_URI "
            "or provide --phone."
        )

    user_id = caller_user_id or phone_number

    if not room_name:
        sanitized_id = "".join(
            c for c in user_id if c.isalnum() or c in "-_"
        )
        room_name = f"health-outbound-{sanitized_id}"

    # Get trigger details
    trigger_info = HEALTH_ACCESS_TRIGGERS.get(
        call_trigger.lower(),
        {
            "title": call_trigger,
            "instructions": custom_instructions or "Health Access Outreach",
        },
    )

    instructions = custom_instructions or trigger_info["instructions"]

    # Build caller metadata
    caller_info = {
        "caller_user_id": user_id,
        "caller_name": caller_name,
        "call_trigger": trigger_info["title"],
        "instructions": instructions,
    }

    logger.info(
        "Initiating SIP outbound call using configured LiveKit SIP trunk "
        "in room '%s'",
        room_name,
    )
    logger.info(
        "Trigger: %s | Caller User ID: %s",
        trigger_info["title"],
        user_id,
    )

    lkapi = api.LiveKitAPI(
        url=livekit_url,
        api_key=api_key,
        api_secret=api_secret,
    )

    try:
        # LiveKit expects a phone number or SIP username.
        call_to = phone_number

        if call_to.lower().startswith("sip:"):
            call_to = call_to[4:]

        if "@" in call_to:
            call_to = call_to.split("@")[0]

        # 1. Dispatch the agent first so it is ready when the call connects.
        dispatch_req = api.CreateAgentDispatchRequest(
            agent_name="my-agent",
            room=room_name,
            metadata=json.dumps(caller_info),
        )

        await lkapi.agent_dispatch.create_dispatch(dispatch_req)

        logger.info(
            "Agent dispatched to room '%s'",
            room_name,
        )

        # 2. Create the SIP participant and initiate the call.
        req = api.CreateSIPParticipantRequest(
            sip_trunk_id=sip_trunk_id,
            sip_call_to=call_to,
            room_name=room_name,
            participant_identity=user_id,
            participant_name=caller_name or user_id,
            participant_metadata=json.dumps(caller_info),
        )

        sip_participant = await lkapi.sip.create_sip_participant(req)

        logger.info(
            "SIP participant created successfully: %s",
            sip_participant.participant_id,
        )

        return room_name

    finally:
        await lkapi.aclose()


def main():
    """CLI entrypoint for triggering an outbound call."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Trigger a Health Access outbound SIP call "
            "via LiveKit SIP API"
        )
    )

    parser.add_argument(
        "--phone",
        "-p",
        type=str,
        default=os.getenv("LINPHONE_SIP_URI"),
        help="SIP URI or phone number to call",
    )

    parser.add_argument(
        "--trigger",
        "-t",
        type=str,
        choices=[
            "medication_reminder",
            "vaccination_reminder",
            "triage_followup",
        ],
        default="medication_reminder",
        help="Health Access call trigger type",
    )

    parser.add_argument(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Caller/patient name",
    )

    parser.add_argument(
        "--user-id",
        "-u",
        type=str,
        default=None,
        help="Caller user ID",
    )

    parser.add_argument(
        "--instructions",
        "-i",
        type=str,
        default=None,
        help="Custom instructions for agent",
    )

    args = parser.parse_args()

    if not args.phone:
        parser.error(
            "No SIP destination provided. "
            "Set LINPHONE_SIP_URI or use --phone."
        )

    asyncio.run(
        make_outbound_call(
            phone_number=args.phone,
            call_trigger=args.trigger,
            caller_name=args.name,
            caller_user_id=args.user_id,
            custom_instructions=args.instructions,
        )
    )


if __name__ == "__main__":
    main()
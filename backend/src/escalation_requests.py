"""Local, authorised inspection command for open human-help requests.

Run from ``backend`` with ``uv run python src/escalation_requests.py``.
This prints only the concise fields stored for the support workflow.
"""

import os
from pathlib import Path

from escalation import EscalationStore


def main() -> None:
    default_db = Path(__file__).resolve().parent.parent / "data" / "callers.sqlite3"
    store = EscalationStore(os.getenv("CALLER_MEMORY_DB", default_db))
    store.initialize()
    requests = store.list_open()
    if not requests:
        print("No open escalation requests.")
        return
    for request in requests:
        print(
            f"{request['escalation_id']} | {request['urgency']} | "
            f"{request['language']} | {request['status']} | {request['created_at']}"
        )
        print(f"  {request['summary']}")


if __name__ == "__main__":
    main()

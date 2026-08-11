import asyncio
from livekit import api

async def main():
    a = api.LiveKitAPI("wss://x", "k", "s")
    print(type(a.agent_dispatch))
    print([m for m in dir(a.agent_dispatch) if not m.startswith("_")])
    await a.aclose()

asyncio.run(main())

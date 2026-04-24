import asyncio
import sys


def configure_windows_event_loop_policy() -> bool:
    if not sys.platform.startswith("win"):
        return False

    selector_policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if selector_policy is None:
        return False

    asyncio.set_event_loop_policy(selector_policy())
    return True

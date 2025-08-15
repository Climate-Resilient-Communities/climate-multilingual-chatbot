import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

logger = logging.getLogger(__name__)


def create_event_loop():
    """Create and configure a new event loop.

    Matches the behavior previously embedded in app_nova.py, but isolated for reuse.
    """
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.set_debug(False)
        return loop
    except Exception as e:
        st.error(f"Failed to create event loop: {str(e)}")
        raise


def run_async(coro):
    """Helper function to run coroutines in a dedicated event loop.

    Ensures proper cleanup of pending tasks after execution.
    """
    loop = None
    try:
        loop = create_event_loop()

        with ThreadPoolExecutor() as pool:
            future = pool.submit(lambda: loop.run_until_complete(coro))
            return future.result()
    except Exception as e:
        st.error(f"Async execution error: {str(e)}")
        raise
    finally:
        if loop and not loop.is_closed():
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                loop.run_until_complete(
                    asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=2.0)
                )
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Task cleanup warning: {str(e)}")
            finally:
                try:
                    loop.stop()
                    loop.close()
                except Exception:
                    pass



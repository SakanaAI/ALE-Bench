import asyncio
import atexit
import logging
import threading
from concurrent.futures import Future, TimeoutError
from typing import Coroutine, TypeVar

T = TypeVar("T")


class SharedAsyncLoop:
    """Background event loop shared across threads for async-only providers like Google GenAI."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        atexit.register(self.shutdown)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _drain_pending(self) -> None:
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def run(self, coroutine: Coroutine[object, object, T], timeout: float | None = None) -> T:
        future: Future[T] = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            return future.result(timeout=timeout)
        except TimeoutError as exc:
            if not future.cancelled():
                future.cancel()
            raise asyncio.TimeoutError(f"Timed out waiting for coroutine result after {timeout}s") from exc
        except BaseException:
            if not future.cancelled():
                future.cancel()
            raise

    def shutdown(self) -> None:
        if self._loop.is_closed():
            return
        if self._loop.is_running():
            drain_future = asyncio.run_coroutine_threadsafe(self._drain_pending(), self._loop)
            try:
                drain_future.result(timeout=5)
            except TimeoutError:
                logging.getLogger(__name__).warning("Timed out cancelling pending tasks on shared async loop")
            self._loop.call_soon_threadsafe(self._loop.stop)
            if threading.current_thread() is not self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
                if self._thread.is_alive():
                    logging.getLogger(__name__).warning("Shared async loop thread did not stop within 5s")
        if not self._loop.is_closed():
            self._loop.close()
        global SHARED_ASYNC_LOOP
        with SHARED_ASYNC_LOOP_LOCK:
            if SHARED_ASYNC_LOOP is self:
                SHARED_ASYNC_LOOP = None

    def is_closed(self) -> bool:
        return self._loop.is_closed()


SHARED_ASYNC_LOOP: SharedAsyncLoop | None = None
SHARED_ASYNC_LOOP_LOCK = threading.Lock()


def shared_async_loop() -> SharedAsyncLoop:
    global SHARED_ASYNC_LOOP
    if SHARED_ASYNC_LOOP is None or SHARED_ASYNC_LOOP.is_closed():
        with SHARED_ASYNC_LOOP_LOCK:
            if SHARED_ASYNC_LOOP is None or SHARED_ASYNC_LOOP.is_closed():
                SHARED_ASYNC_LOOP = SharedAsyncLoop()
    return SHARED_ASYNC_LOOP

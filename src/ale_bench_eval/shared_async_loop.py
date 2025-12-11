import asyncio
import atexit
import logging
import threading
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from typing import Coroutine, TypeVar

T = TypeVar("T")


class SharedAsyncLoop:
    """Background event loop shared across threads for async-only providers.

    This class is intended for use cases where synchronous code needs to execute asynchronous coroutines,
    such as when interacting with async-only providers (e.g., Google GenAI) from synchronous contexts.
    """

    SHUTDOWN_TIMEOUT = 5

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._atexit_cb = self.shutdown
        self._thread.start()
        try:
            atexit.register(self._atexit_cb)
        except Exception:
            # Ensure the background thread is cleaned up if registration fails.
            self.shutdown()
            raise

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _drain_pending(self) -> None:
        tasks = [t for t in asyncio.all_tasks(self._loop) if t is not asyncio.current_task(self._loop)]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def run(self, coroutine: Coroutine[object, object, T], timeout: float | None = None) -> T:
        """Execute a coroutine on the shared event loop from any thread and return its result.

        Args:
            coroutine (Coroutine): The coroutine to execute.
            timeout (float, optional): Maximum time in seconds to wait for the result. If None, wait indefinitely.
        Returns:
            T: The result returned by the coroutine.
        Raises:
            asyncio.TimeoutError: If the coroutine does not complete within the specified timeout.
            Exception: Any exception raised by the coroutine will be propagated.
        Note:
            On exception, this method requests cancellation of the underlying coroutine via the returned Future.
            If the coroutine ignores cancellation, it may continue running briefly.
        """
        future: Future[T] = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError as exc:
            future.cancel()
            raise asyncio.TimeoutError(f"Timed out waiting for coroutine result after {timeout}s") from exc
        except Exception:
            future.cancel()
            raise

    def shutdown(self) -> None:
        global SHARED_ASYNC_LOOP
        with SHARED_ASYNC_LOOP_LOCK:
            if self._loop.is_closed():
                if SHARED_ASYNC_LOOP is self:
                    SHARED_ASYNC_LOOP = None
                return
            if self._loop.is_running():
                drain_future = asyncio.run_coroutine_threadsafe(self._drain_pending(), self._loop)
                try:
                    drain_future.result(timeout=self.SHUTDOWN_TIMEOUT)
                except FutureTimeoutError:
                    logging.getLogger(__name__).warning("Timed out cancelling pending tasks on shared async loop")
                self._loop.call_soon_threadsafe(self._loop.stop)
                if threading.current_thread() is not self._thread and self._thread.is_alive():
                    self._thread.join(timeout=self.SHUTDOWN_TIMEOUT)
                    if self._thread.is_alive():
                        logging.getLogger(__name__).warning(
                            f"Shared async loop thread did not stop within {self.SHUTDOWN_TIMEOUT}s"
                        )
            if not self._loop.is_closed():
                self._loop.close()
            try:
                atexit.unregister(self._atexit_cb)
            except Exception:
                # During interpreter shutdown unregister may fail; ignore.
                pass
            if SHARED_ASYNC_LOOP is self:
                SHARED_ASYNC_LOOP = None

    def is_closed(self) -> bool:
        return self._loop.is_closed()


SHARED_ASYNC_LOOP: SharedAsyncLoop | None = None
SHARED_ASYNC_LOOP_LOCK = threading.Lock()


def shared_async_loop() -> SharedAsyncLoop:
    """Returns a singleton instance of SharedAsyncLoop, creating a new instance if None or the previous one is closed.

    This function is thread-safe and ensures only one SharedAsyncLoop instance is active at a time.

    Returns:
        SharedAsyncLoop: The shared async event loop instance.
    """
    global SHARED_ASYNC_LOOP
    with SHARED_ASYNC_LOOP_LOCK:
        if SHARED_ASYNC_LOOP is None or SHARED_ASYNC_LOOP.is_closed():
            SHARED_ASYNC_LOOP = SharedAsyncLoop()
        return SHARED_ASYNC_LOOP

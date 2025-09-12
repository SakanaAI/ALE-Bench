import datetime as dt

from docker.errors import NotFound
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

import ale_bench
from ale_bench.session import Session

SESSION_DURATION_HOURS = 240


@retry(
    retry=retry_if_exception_type(NotFound),  # Retry only on 404 errors
    stop=stop_after_attempt(3),  # Maximally 3 retries
    wait=wait_fixed(5),  # Wait 5 seconds each time
    reraise=True,  # Raise the exception at the end
)
def start_ale_bench_session(problem_id: str, lite_version: bool, num_workers: int) -> Session:
    return ale_bench.start(
        problem_id=problem_id,
        lite_version=lite_version,
        num_workers=num_workers,
        run_visualization_server=False,
        session_duration=dt.timedelta(hours=SESSION_DURATION_HOURS),
    )

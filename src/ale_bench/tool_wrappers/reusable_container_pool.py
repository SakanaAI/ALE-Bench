"""Reusable Docker container pools for case execution."""

from __future__ import annotations

import os
import time
from contextlib import suppress
from queue import Queue
from typing import TYPE_CHECKING

import ale_bench.constants
from ale_bench.code_language import CodeLanguage, JudgeVersion, get_docker_image_name
from ale_bench.data import ProblemType
from ale_bench.utils import docker_client

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

    from docker import DockerClient
    from docker.models.containers import Container

REUSABLE_SUBMISSION_TMP_DIR = f"{ale_bench.constants.TMP_DIR}/ale-bench-run"
REUSABLE_TOOL_TMP_DIR = f"{ale_bench.constants.TMP_DIR}/ale-bench-tool"


def get_reusable_tool_volumes(
    scratch_dir: Path,
    tool_dir: Path,
) -> dict[str, dict[str, str]]:
    """Get volumes for a reusable judge/visualization tool container."""
    return {
        str(scratch_dir): {"bind": REUSABLE_TOOL_TMP_DIR, "mode": "rw"},
        str(tool_dir / "tools" / "target" / "release" / "tester"): {
            "bind": ale_bench.constants.TESTER_BIN,
            "mode": "ro",
        },
        str(tool_dir / "tools" / "target" / "release" / "vis"): {
            "bind": ale_bench.constants.VIS_BIN,
            "mode": "ro",
        },
    }


def get_reusable_submission_volumes(
    temp_dir: Path,
    scratch_dir: Path,
    tool_dir: Path,
    problem_type: ProblemType,
) -> dict[str, dict[str, str]]:
    """Get volumes for a reusable submission container.

    The compiled submission directory is mounted read-only at WORK_DIR. Per-case input,
    output, and profile files live in a separate read-write scratch mount.
    """
    volumes = {
        str(temp_dir): {"bind": ale_bench.constants.WORK_DIR, "mode": "ro"},
        str(scratch_dir): {"bind": REUSABLE_SUBMISSION_TMP_DIR, "mode": "rw"},
    }
    if problem_type == ProblemType.REACTIVE:
        volumes[str(tool_dir / "tools" / "target" / "release" / "tester")] = {
            "bind": ale_bench.constants.TESTER_BIN,
            "mode": "ro",
        }
    return volumes


class ReusableSubmissionContainerPool:
    """A fixed-size pool of long-lived submission execution containers."""

    def __init__(
        self,
        code_language: CodeLanguage,
        judge_version: JudgeVersion,
        temp_dir: Path,
        scratch_dir: Path,
        tool_dir: Path,
        problem_type: ProblemType,
        num_workers: int,
    ) -> None:
        """Initialize the reusable container pool configuration."""
        self.code_language = code_language
        self.judge_version = judge_version
        self.temp_dir = temp_dir
        self.scratch_dir = scratch_dir
        self.tool_dir = tool_dir
        self.problem_type = problem_type
        self.num_workers = num_workers
        self._client_context = docker_client()
        self._client: DockerClient | None = None
        self._containers: list[Container] = []
        self._available_containers: Queue[Container] = Queue()

    def __enter__(self) -> ReusableSubmissionContainerPool:  # noqa: PYI034
        """Create and start all worker containers."""
        self._client = self._client_context.__enter__()
        for _ in range(self.num_workers):
            self._available_containers.put(self._create_container())
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Remove all worker containers and close the Docker client."""
        for container in self._containers:
            self._remove_container(container)
        self._containers.clear()
        self._client_context.__exit__(exc_type, exc_value, traceback)
        self._client = None

    def container_path(self, host_path: Path) -> str:
        """Convert a scratch host path to its reusable-container path."""
        return f"{REUSABLE_SUBMISSION_TMP_DIR}/{host_path.relative_to(self.scratch_dir)}"

    def run(self, command: str) -> tuple[float, int, str]:
        """Run one command via docker exec in an available reusable container."""
        container = self._available_containers.get()
        should_replace = False
        try:
            start_at = time.perf_counter()
            exec_result = container.exec_run(
                cmd=["/bin/bash", "--noprofile", "--norc", "-c", command],
                demux=True,
                stderr=True,
                stdout=True,
                user=str(os.getuid()),
                workdir=ale_bench.constants.WORK_DIR,
            )
            end_at = time.perf_counter()
            _stdout_bytes, stderr_bytes = exec_result.output or (b"", b"")
            stderr = (stderr_bytes or b"").decode("utf-8", errors="replace").strip()
            return end_at - start_at, exec_result.exit_code, stderr
        except Exception:
            should_replace = True
            raise
        finally:
            self._release_container(container, should_replace)

    def _create_container(self) -> Container:
        if self._client is None:
            msg = "ReusableSubmissionContainerPool must be entered before creating containers."
            raise RuntimeError(msg)
        volumes = get_reusable_submission_volumes(
            self.temp_dir,
            self.scratch_dir,
            self.tool_dir,
            self.problem_type,
        )
        container = self._client.containers.run(
            image=get_docker_image_name(self.code_language, self.judge_version),
            command=["/bin/bash", "--noprofile", "--norc", "-c", "sleep infinity"],
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,  # 1 CPU
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        self._containers.append(container)
        return container

    def _release_container(self, container: Container, should_replace: bool) -> None:
        if should_replace or not self._is_container_running(container):
            self._remove_container(container)
            if container in self._containers:
                self._containers.remove(container)
            self._available_containers.put(self._create_container())
        else:
            self._available_containers.put(container)

    def _is_container_running(self, container: Container) -> bool:
        try:
            container.reload()
            attrs = container.attrs
            if not isinstance(attrs, dict):
                return False
            state = attrs.get("State", {})
            if not isinstance(state, dict):
                return False
            return bool(state.get("Running", False))
        except Exception:
            return False

    def _remove_container(self, container: Container) -> None:
        with suppress(Exception):
            container.remove(force=True)


class ReusableToolContainerPool:
    """A fixed-size pool of long-lived judge/visualization tool containers."""

    def __init__(
        self,
        scratch_dir: Path,
        tool_dir: Path,
        num_workers: int,
    ) -> None:
        """Initialize the reusable tool container pool configuration."""
        self.scratch_dir = scratch_dir
        self.tool_dir = tool_dir
        self.num_workers = num_workers
        self._client_context = docker_client()
        self._client: DockerClient | None = None
        self._containers: list[Container] = []
        self._available_containers: Queue[Container] = Queue()

    def __enter__(self) -> ReusableToolContainerPool:  # noqa: PYI034
        """Create and start all worker containers."""
        self._client = self._client_context.__enter__()
        for _ in range(self.num_workers):
            self._available_containers.put(self._create_container())
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Remove all worker containers and close the Docker client."""
        for container in self._containers:
            self._remove_container(container)
        self._containers.clear()
        self._client_context.__exit__(exc_type, exc_value, traceback)
        self._client = None

    def container_path(self, host_path: Path) -> str:
        """Convert a scratch host path to its reusable-container path."""
        return f"{REUSABLE_TOOL_TMP_DIR}/{host_path.relative_to(self.scratch_dir)}"

    def run(self, command: str, *, workdir: str = ale_bench.constants.WORK_DIR) -> tuple[float, int, str]:
        """Run one command via docker exec in an available reusable tool container."""
        container = self._available_containers.get()
        should_replace = False
        try:
            start_at = time.perf_counter()
            exec_result = container.exec_run(
                cmd=["/bin/bash", "--noprofile", "--norc", "-c", command],
                demux=True,
                stderr=True,
                stdout=True,
                user=str(os.getuid()),
                workdir=workdir,
            )
            end_at = time.perf_counter()
            _stdout_bytes, stderr_bytes = exec_result.output or (b"", b"")
            stderr = (stderr_bytes or b"").decode("utf-8", errors="replace").strip()
            return end_at - start_at, exec_result.exit_code, stderr
        except Exception:
            should_replace = True
            raise
        finally:
            self._release_container(container, should_replace)

    def _create_container(self) -> Container:
        if self._client is None:
            msg = "ReusableToolContainerPool must be entered before creating containers."
            raise RuntimeError(msg)
        container = self._client.containers.run(
            image=ale_bench.constants.RUST_TOOL_DOCKER_IMAGE,
            command=["/bin/bash", "--noprofile", "--norc", "-c", "sleep infinity"],
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,  # 1 CPU
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=get_reusable_tool_volumes(self.scratch_dir, self.tool_dir),
            working_dir=ale_bench.constants.WORK_DIR,
        )
        self._containers.append(container)
        return container

    def _release_container(self, container: Container, should_replace: bool) -> None:
        if should_replace or not self._is_container_running(container):
            self._remove_container(container)
            if container in self._containers:
                self._containers.remove(container)
            self._available_containers.put(self._create_container())
        else:
            self._available_containers.put(container)

    def _is_container_running(self, container: Container) -> bool:
        try:
            container.reload()
            attrs = container.attrs
            if not isinstance(attrs, dict):
                return False
            state = attrs.get("State", {})
            if not isinstance(state, dict):
                return False
            return bool(state.get("Running", False))
        except Exception:
            return False

    def _remove_container(self, container: Container) -> None:
        with suppress(Exception):
            container.remove(force=True)

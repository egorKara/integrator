from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Sequence, TypeVar

from scan import Project, _project_sort_key
from utils import _apply_limit

_T = TypeVar("_T")
_R = TypeVar("_R")


@dataclass(frozen=True, slots=True)
class WorkerError:
    exc_type: str
    message: str

    def to_text(self) -> str:
        msg = self.message.strip()
        if not msg:
            return self.exc_type
        return f"{self.exc_type}: {msg}"


def _git_projects(projects: Sequence[Project]) -> list[Project]:
    return [p for p in projects if (p.path / ".git").exists()]


def _agent_projects(projects: Sequence[Project]) -> list[Project]:
    from scan import _is_agent_project_dir

    return [p for p in projects if _is_agent_project_dir(p.path)]


def _parallel_map(items: Sequence[_T], func: Callable[[_T], _R], jobs: int) -> list[tuple[_T, _R | WorkerError]]:
    results: list[tuple[_T, _R | WorkerError]] = []
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = {ex.submit(func, item): item for item in items}
        for fut in as_completed(futures):
            item = futures[fut]
            try:
                results.append((item, fut.result()))
            except Exception as e:
                results.append((item, WorkerError(type(e).__name__, str(e))))
    return results


def _map_git_projects(
    projects: Sequence[Project],
    jobs: int,
    limit: int | None,
    func: Callable[[Project], _R],
) -> list[tuple[Project, _R | WorkerError]]:
    git_projects = _git_projects(projects)
    results = _parallel_map(git_projects, func, jobs)
    results.sort(key=lambda item: _project_sort_key(item[0]))
    return _apply_limit(results, limit)

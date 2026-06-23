"""Process / system self-vitals via ``psutil`` (``vitel[psutil]``, lazy import).

The agent's interoception: how the process under its own care is doing. ``source`` is ignored
(``"self"`` by convention). Returns single-point series for CPU, memory, threads and fds.
"""

from __future__ import annotations

from ..config import Settings
from ..errors import MissingDependencyError
from ..signals.series import TimeSeries


class SelfStatBackend:
    name = "psutil"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def available(self) -> bool:
        from importlib.util import find_spec

        return find_spec("psutil") is not None

    async def critique(self, series: list[TimeSeries], prompt: str) -> str:
        return ""

    async def fetch(self, source: str, *, window_s: float | None = None) -> list[TimeSeries]:
        try:
            import psutil
        except ImportError as e:
            raise MissingDependencyError("self-vitals need psutil; pip install vitel[psutil]") from e

        proc = psutil.Process()
        out: dict[str, float] = {}
        with proc.oneshot():
            out["cpu"] = proc.cpu_percent(interval=0.05) / 100.0  # ratio of one core
            mem = proc.memory_info()
            out["rss_bytes"] = float(mem.rss)
            out["num_threads"] = float(proc.num_threads())
            try:
                out["open_fds"] = float(proc.num_fds())
            except (AttributeError, NotImplementedError):  # not available on all platforms
                pass

        vm = psutil.virtual_memory()
        out["mem"] = vm.percent / 100.0
        out["system_cpu"] = psutil.cpu_percent(interval=0.05) / 100.0

        return [TimeSeries(name=k, points=[(0.0, v)]) for k, v in out.items()]

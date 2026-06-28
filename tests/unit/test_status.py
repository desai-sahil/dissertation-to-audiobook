from __future__ import annotations

import io
import threading
import time
from pathlib import Path

from thesis_audiobook.adapters.status import NoopReporter, TerminalReporter
from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document, DocumentMeta
from thesis_audiobook.pipeline import Pipeline


class _FakeStream:
    """A thread-safe in-memory stderr stand-in with a controllable isatty()."""

    def __init__(self, *, tty: bool) -> None:
        self._buf = io.StringIO()
        self._tty = tty
        self._lock = threading.Lock()

    def write(self, s: str, /) -> int:
        with self._lock:
            return self._buf.write(s)

    def flush(self) -> None:
        return

    def isatty(self) -> bool:
        return self._tty

    def value(self) -> str:
        with self._lock:
            return self._buf.getvalue()


class _RecordingReporter:
    def __init__(self) -> None:
        self.labels: list[str] = []

    def start(self) -> None:
        return

    def update(self, label: str) -> None:
        self.labels.append(label)

    def stop(self) -> None:
        return


class _PassStage:
    name = "passthrough"

    def run(self, doc: Document, ctx: Context) -> Document:
        return doc


def test_noop_reporter_is_callable_and_silent() -> None:
    reporter = NoopReporter()
    assert reporter.start() is None
    assert reporter.update("anything") is None
    assert reporter.stop() is None


def test_mock_context_status_defaults_to_noop(tiny_ir_path: Path) -> None:
    # The Context default keeps tests / dry-run byte-for-byte silent (determinism).
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    assert isinstance(ctx.status, NoopReporter)


def test_terminal_reporter_silent_when_not_a_tty() -> None:
    stream = _FakeStream(tty=False)
    reporter = TerminalReporter(stream=stream)
    reporter.start()
    reporter.update("QC audit (Opus)")
    time.sleep(0.05)
    reporter.stop()
    assert stream.value() == ""  # no spinner in pipes / CI / redirected logs


def test_terminal_reporter_animates_and_clears_on_tty() -> None:
    stream = _FakeStream(tty=True)
    reporter = TerminalReporter(stream=stream)
    reporter.start()
    reporter.update("QC confirm (Opus)")
    deadline = time.monotonic() + 2.0  # bounded wait for the daemon to draw a frame (not flaky)
    while "QC confirm (Opus)" not in stream.value() and time.monotonic() < deadline:
        time.sleep(0.02)
    reporter.stop()
    out = stream.value()
    assert "QC confirm (Opus)" in out  # the current label was drawn
    assert "\x1b[2K" in out  # each frame clears the line first
    assert out.endswith("\r\x1b[2K")  # stop() erased the bar for a clean stdout handoff


def test_pipeline_reports_each_stage(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    recorder = _RecordingReporter()
    ctx.status = recorder
    Pipeline([_PassStage()]).run(Document(meta=DocumentMeta(title="t")), ctx)
    assert recorder.labels == ["passthrough"]

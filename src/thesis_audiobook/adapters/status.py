"""Status reporter adapters: the effectful edge of the StatusReporter port.

NoopReporter does nothing and is the Context default, so tests and dry-run stay
byte-for-byte silent. TerminalReporter animates a one-line spinner on stderr so a
user can see which stage / agent loop is running during a slow LLM call. It is
gated on isatty(): in a pipe, a redirect, or CI it is a no-op, keeping logs clean.
The spinner runs on a daemon thread (it can never block process exit) and only
ever writes ephemeral stderr - it never reads or mutates the Document, so it
cannot change any output byte.

Caveat: the spinner shares stderr with anything else that writes there. The CLI
quiets the anthropic/httpx SDK loggers during a real run so their retry chatter
does not smear the line. In-process PDF parsing (--parser marker/mineru) prints
its own tqdm progress bars to stderr and WILL interleave with the spinner; the
recommended flow parses once as a separate step and feeds the result via
--markdown, where no parser progress bars run during `audiobook run`.
"""

from __future__ import annotations

import sys
import threading
import time
from typing import Protocol


class _Writable(Protocol):
    """The slice of a text stream the reporter needs (sys.stderr satisfies it)."""

    def write(self, s: str, /) -> int: ...
    def flush(self) -> None: ...
    def isatty(self) -> bool: ...


class NoopReporter:
    """A status reporter that does nothing. The Context default (tests, dry-run)."""

    def start(self) -> None:
        return

    def update(self, label: str) -> None:
        return

    def stop(self) -> None:
        return


class TerminalReporter:
    """A single-line spinner on stderr, animated by a background daemon thread.

    Off unless stderr is a TTY, so pipes / redirects / CI stay clean. `update`
    swaps the shown label (and resets its elapsed timer); the daemon redraws the
    current label with a spinner frame and elapsed seconds about ten times a
    second, so a long blocking LLM call still looks alive. `stop` halts the
    thread and erases the line so the next stdout write lands on a clean row.
    """

    _FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴",
               "⠦", "⠧", "⠇", "⠏")  # fmt: skip
    _ERASE = "\r\x1b[2K"  # carriage return + clear-to-end-of-line

    def __init__(self, stream: _Writable | None = None) -> None:
        self._stream: _Writable = stream if stream is not None else sys.stderr
        self._tty = self._stream.isatty()
        self._label = ""
        self._started_at = 0.0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self._tty or self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def update(self, label: str) -> None:
        if not self._tty:
            return
        with self._lock:
            self._label = label
            self._started_at = time.monotonic()

    def stop(self) -> None:
        if not self._tty:
            return
        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=0.3)
        self._thread = None
        self._stream.write(self._ERASE)
        self._stream.flush()

    def _spin(self) -> None:
        frame = 0
        while not self._stop_event.is_set():
            with self._lock:
                label = self._label
                started = self._started_at
            if label:
                glyph = self._FRAMES[frame % len(self._FRAMES)]
                elapsed = int(time.monotonic() - started)
                self._stream.write(f"{self._ERASE}{glyph} {label} ({elapsed}s)")
                self._stream.flush()
            frame += 1
            self._stop_event.wait(0.1)

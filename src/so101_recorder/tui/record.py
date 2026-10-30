"""The recording screen: which episode, how long is left, what lerobot says. → next, ← redo, esc stop."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import RichLog, Static

from .. import hub
from ..i18n import t
from ..session import Recording, State
from .theme import ACCENT, DIM, ERROR, FG, OK, RESET, SURFACE

FINISHED = ("done", "failed", "stopped")
BAR = 56


class RecordScreen(Screen):
    BINDINGS = [
        Binding("right", "key('next', True)", show=False),
        Binding("n", "key('next', False)", show=False),
        Binding("left", "key('redo', True)", show=False),
        Binding("r", "key('redo', False)", show=False),
        Binding("escape", "key('stop', True)", show=False),
        Binding("q", "key('stop', False)", show=False),
        Binding("enter", "home", show=False),
        Binding("o", "open('hub')", show=False),
        Binding("v", "open('viewer')", show=False),
    ]

    def __init__(self, args: list[str], *, earlier: int = 0, command: list[str] | None = None):
        super().__init__()
        self.args = args
        self.earlier = earlier  # episodes already in the dataset (resume)
        self._cmd = command
        self.state = State(planned=_arg(args, "dataset.num_episodes", int, 1))
        self.repo_id = _arg(args, "dataset.repo_id", str, "")
        self.task_text = _arg(args, "dataset.single_task", str, "")
        self.root = _arg(args, "dataset.root", str, "")
        self.aborting = False
        self.rec: Recording | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="rec"):
            yield Static(id="rec-head")
            yield Static(id="rec-phase")
            yield Static(id="rec-bar")
            yield Static(id="rec-dots")
            yield Static(id="rec-message")
            yield RichLog(id="rec-log", max_lines=1000, wrap=True, markup=False)
            yield Static(id="rec-keys", classes="keys")

    def on_mount(self) -> None:
        head = Text()
        head.append(self.repo_id, style=f"bold {FG}")
        head.append(f"\n“{self.task_text}”", style=DIM)
        self.query_one("#rec-head", Static).update(head)
        self.rec = Recording(
            self.args,
            on_event=lambda ev: self._from_thread(self._event, ev),
            on_log=lambda line: self._from_thread(self._log, line),
            on_exit=lambda code: self._from_thread(self._exited, code),
            global_keys=self.app.settings.global_keys,
            command=self._cmd,
        )
        self.rec.start()
        self.set_interval(0.1, self.draw)
        self.draw()

    def _from_thread(self, fn, arg) -> None:
        try:
            self.app.call_from_thread(fn, arg)
        except Exception:
            pass  # the app is closing

    # --- what comes from the runner -------------------------------------------------------------------------

    def _event(self, ev: dict) -> None:
        self.state.apply(ev)
        if ev.get("event") == "retry":
            self._log(f"connect failed ({ev.get('message')}); retrying {ev.get('attempt')}/{ev.get('tries')}")
        self.draw()

    def _log(self, line: str) -> None:
        self.query_one("#rec-log", RichLog).write(Text(line, style=DIM))

    def _exited(self, code: int) -> None:
        if self.state.phase not in FINISHED:
            self.state.phase = "stopped" if self.aborting else "failed"
            if not self.state.error and not self.aborting:
                self.state.error = f"lerobot-record exited with code {code}"
        self.draw()

    # --- drawing --------------------------------------------------------------------------------------------

    def draw(self) -> None:
        st = self.state
        phase = Text()
        if st.phase in ("record", "reset", "saving") or (st.phase == "pushing" and st.saved):
            phase.append(t("episode", i=st.current, n=st.planned), style=f"bold {FG}")
            phase.append("    ")
        label = {
            "starting": t("ph starting"),
            "connecting": t("ph connecting", device=st.connecting or "arms"),
            "record": t("ph record"),
            "reset": t("ph reset"),
            "saving": t("ph saving"),
            "pushing": t("ph pushing"),
            "done": t("ph done"),
            "stopped": t("ph stopped"),
            "failed": t("ph failed"),
        }.get(st.phase, st.phase)
        color = {"record": ACCENT, "reset": RESET, "failed": ERROR, "done": OK}.get(st.phase, FG)
        phase.append(label, style=f"bold {color}")
        self.query_one("#rec-phase", Static).update(phase)
        self.query_one("#rec-bar", Static).update(self._bar(st, color))
        self.query_one("#rec-dots", Static).update(self._dots(st))
        self.query_one("#rec-message", Static).update(self._message(st))
        self.query_one("#rec-keys", Static).update(self._keys(st))

    def _bar(self, st: State, color: str) -> Text:
        bar = Text()
        if st.phase in ("record", "reset") and st.phase_duration:
            elapsed = min(st.elapsed(), st.phase_duration)
            filled = round(BAR * elapsed / st.phase_duration)
            bar.append("█" * filled, style=color)
            bar.append("█" * (BAR - filled), style=SURFACE)
            bar.append(f"  {_clock(elapsed)} / {_clock(st.phase_duration)}", style=FG)
        elif st.phase in ("starting", "connecting", "saving", "pushing"):
            pos = int(st.elapsed() * 12) % BAR
            bar.append("█" * pos, style=SURFACE)
            bar.append("███", style=color)
            bar.append("█" * max(0, BAR - pos - 3), style=SURFACE)
        return bar

    def _dots(self, st: State) -> Text:
        dots = Text()
        for i in range(st.planned):
            if i < len(st.saved):
                dots.append("● ", style=FG)
            elif i == len(st.saved) and st.phase not in FINISHED:
                dots.append("◉ ", style=ACCENT if st.phase == "record" else RESET)
            else:
                dots.append("○ ", style=DIM)
        extra = []
        if st.redone:
            extra.append(t("redone", n=st.redone))
        if self.earlier:
            extra.append(f"+{self.earlier} earlier")
        if extra:
            dots.append("  " + " · ".join(extra), style=DIM)
        return dots

    def _message(self, st: State) -> Text:
        msg = Text()
        if st.error:
            msg.append(st.error + "\n", style=ERROR)
            if st.hint:
                msg.append(st.hint + "\n", style=FG)
        if st.phase in ("done", "stopped") and st.saved:
            msg.append(t("saved n", n=len(st.saved), root=self.root) + "\n", style=FG)
        if st.url:
            msg.append(st.url, style=ACCENT)
        if self.aborting and st.phase not in FINISHED:
            msg.append(t("aborting"), style=ACCENT)
        return msg

    def _keys(self, st: State) -> Text:
        k = Text()

        def key(name, what):
            k.append(name, style=ACCENT)
            k.append(f" {what}   ", style=DIM)

        if st.phase in FINISHED:
            key("enter", t("k home"))
            if st.url:
                key("o", t("k open"))
                key("v", t("k viewer"))
            return k
        key("→ n", t("k next"))
        key("← r", t("k redo"))
        key("esc q", t("k stop"))
        key("ctrl+c", t("k abort"))
        if st.global_keys is not None:
            k.append(t("global yes") if st.global_keys else t("global no"), style=DIM)
        return k

    # --- keys -----------------------------------------------------------------------------------------------

    def action_key(self, word: str, global_key: bool) -> None:
        st = self.state
        if st.phase in FINISHED:
            if word == "stop":
                self.action_home()
            return
        if global_key and st.global_keys:
            return  # the runner hears this key itself (pynput); sending it too would count it twice
        if self.rec:
            self.rec.send(word)

    def on_ctrl_c(self) -> None:
        if not self.rec or not self.rec.running:
            self.action_home()
        elif self.aborting:
            self.rec.kill()
        else:
            self.aborting = True
            self.rec.interrupt()
            self.draw()

    def action_home(self) -> None:
        if self.state.phase in FINISHED or not (self.rec and self.rec.running):
            self.app.pop_screen()

    def action_open(self, which: str) -> None:
        if self.state.url:
            self.app.open_url(hub.dataset_url(self.repo_id) if which == "hub" else hub.viewer_url(self.repo_id))


def _arg(args: list[str], key: str, cast, default):
    prefix = f"--{key}="
    for a in args:
        if a.startswith(prefix):
            try:
                return cast(a[len(prefix):])
            except ValueError:
                return default
    return default


def _clock(s: float) -> str:
    s = int(s)
    return f"{s // 60:02d}:{s % 60:02d}"

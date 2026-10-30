"""The home screen: one sentence to fill in, then enter.

    Record [5] episodes of
    [put the red X in the middle right cell]
    on my [SO-101]
    into [fport] / [tic-tac-toe-x]  →
"""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.suggester import SuggestFromList
from textual.timer import Timer
from textual.widgets import Button, Input, Static

from .. import checks, command, devices, hub
from ..i18n import t
from .theme import ACCENT, DIM, ERROR

SLOTS = ["episodes", "task", "namespace", "dataset"]
MAX_WIDTH = {"task": 72, "dataset": 44, "namespace": 24, "episodes": 5}


class HomeScreen(Screen):
    BINDINGS = [
        Binding("ctrl+s", "setup", show=False),
        Binding("ctrl+l", "command", show=False),
        Binding("ctrl+t", "language", show=False),
        Binding("ctrl+q", "quit", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.hub_episodes: int | None = None
        self._hub_timer: Timer | None = None
        self._shown_problems = False

    @property
    def s(self):
        return self.app.settings

    def compose(self) -> ComposeResult:
        s = self.s
        with Vertical(id="home"):
            yield Static(id="topbar")
            with Vertical(id="sentence"):
                with Horizontal(classes="line"):
                    yield Static(t("record"), classes="word")
                    yield Input(str(s.episodes), id="episodes", classes="slot", restrict=r"[0-9]*", max_length=4)
                    yield Static(t("episodes of"), classes="word")
                with Horizontal(classes="line"):
                    yield Input(s.task, id="task", classes="slot", placeholder=t("task placeholder"),
                                suggester=SuggestFromList(s.recent_tasks, case_sensitive=False))
                with Horizontal(classes="line"):
                    yield Static(t("on my"), classes="word")
                    yield Button(t("arm ready"), id="arm", classes="chip")
                with Horizontal(classes="line"):
                    yield Static(t("into"), classes="word")
                    yield Input(s.namespace, id="namespace", classes="slot", placeholder=t("namespace placeholder"))
                    yield Static("/", classes="word")
                    yield Input(s.dataset, id="dataset", classes="slot", placeholder=t("dataset placeholder"),
                                restrict=r"[A-Za-z0-9._-]*")
                    yield Button("→", id="go", classes="chip")
                yield Static(id="summary")
                yield Static(id="problems")
            yield Static(self._keys(), classes="keys")

    def _keys(self) -> str:
        return (f"[{ACCENT}]enter[/] {t('k record')}   [{ACCENT}]ctrl+s[/] {t('k setup')}   "
                f"[{ACCENT}]ctrl+l[/] {t('k command')}   [{ACCENT}]ctrl+t[/] {t('k lang')}   "
                f"[{ACCENT}]ctrl+q[/] {t('k quit')}")

    def on_mount(self) -> None:
        for slot in SLOTS:
            self._fit(self.query_one(f"#{slot}", Input))
        first_empty = next((x for x in ("task", "dataset") if not getattr(self.s, x)), "task")
        self.query_one(f"#{first_empty}", Input).focus()
        self.refresh_view()
        self.load_dataset_names()

    def on_screen_resume(self) -> None:
        self.refresh_view()

    # --- the sentence ---------------------------------------------------------------------------------------

    def _fit(self, inp: Input) -> None:
        text = inp.value or inp.placeholder
        inp.styles.width = min(max(len(text), 2) + 3, MAX_WIDTH.get(inp.id or "", 40))

    @on(Input.Changed, ".slot")
    def slot_changed(self, event: Input.Changed) -> None:
        inp = event.input
        self._fit(inp)
        s = self.s
        if inp.id == "episodes":
            s.episodes = max(1, int(inp.value or 1))
        elif inp.id in ("task", "namespace", "dataset"):
            setattr(s, inp.id, inp.value.strip() if inp.id != "task" else inp.value)
        self.app.save()
        if inp.id in ("namespace", "dataset"):
            self.hub_episodes = None
            self._schedule_hub_check()
        self.refresh_view()

    @on(Input.Submitted, ".slot")
    def slot_submitted(self, event: Input.Submitted) -> None:
        i = SLOTS.index(event.input.id)
        needed = [x for x in SLOTS[i + 1:] if x != "namespace" or self.s.push]  # no push: "local/<name>"
        empty = [x for x in needed if not self.query_one(f"#{x}", Input).value.strip()]
        if event.input.id == "dataset" or not empty:
            self.action_record()
        else:
            self.query_one(f"#{empty[0]}", Input).focus()

    @on(Button.Pressed, "#arm")
    def arm_pressed(self) -> None:
        self.action_setup("arms")

    @on(Button.Pressed, "#go")
    def go_pressed(self) -> None:
        self.action_record()

    # --- what is shown under it -----------------------------------------------------------------------------

    def _check(self, ports: list[str] | None = None) -> checks.Check:
        root = self.s.root(self.app.cwd)
        ports = devices.list_ports() if ports is None else ports
        return checks.check(self.s, self.app.account, ports, hub.local(root), root, self.hub_episodes)

    def refresh_view(self) -> None:
        if not self.is_mounted:
            return
        s, acc = self.s, self.app.account
        if acc is None:
            who = t("hub checking")
        elif acc.ok:
            who = f"[{ACCENT}]●[/] {acc.user}"
        else:
            who = f"[{DIM}]○[/] {t('hub none')}"
        self.query_one("#topbar", Static).update(f"so101-recorder   {who}")
        if acc is not None and acc.ok:
            self.query_one("#namespace", Input).suggester = SuggestFromList(acc.namespaces, case_sensitive=False)

        c = self._check()
        arm = self.query_one("#arm", Button)
        arm.label = t("arm setup") if c.arm else t("arm ready")
        arm.set_class(c.arm, "-todo")

        root = s.root(self.app.cwd)
        local = hub.local(root)
        when = [t("each", s=_num(s.episode_s)), t("reset", s=_num(s.reset_s)), f"{s.fps} fps",
                " + ".join(c.name for c in s.cameras) or "no cameras"]
        where = [t("adds to", n=local.episodes) if local.valid else t("new dataset"), _rel(root, self.app.cwd),
                 (t("private hub") if s.private else t("public hub")) if s.push else t("local only")]
        if s.display:
            where.append(t("rerun"))
        self.query_one("#summary", Static).update("  ·  ".join(when) + "\n" + "  ·  ".join(where))

        lines = [f"[{ERROR}]✗[/] {e}" for e in c.errors] if self._shown_problems else []
        lines += [f"[{ACCENT}]![/] {w}" for w in c.warnings]
        self.query_one("#problems", Static).update("\n".join(lines))

    @work(thread=True, exclusive=True, group="names")
    def load_dataset_names(self) -> None:
        names = hub.local_datasets(self.s.root(self.app.cwd).parent)
        acc = self.app.account
        if acc is not None and acc.ok and self.s.namespace:
            try:
                names += [n for n in hub.hub_datasets(self.s.namespace) if n not in names]
            except Exception:
                pass
        self.app.call_from_thread(self._set_names, names)

    def _set_names(self, names: list[str]) -> None:
        if self.is_mounted:
            self.query_one("#dataset", Input).suggester = SuggestFromList(names, case_sensitive=False)

    def _schedule_hub_check(self) -> None:
        if self._hub_timer is not None:
            self._hub_timer.stop()
        self._hub_timer = self.set_timer(0.8, self._hub_check)

    def _hub_check(self) -> None:
        s, acc = self.s, self.app.account
        if not (s.push and s.dataset and s.namespace and acc is not None and acc.ok):
            return
        if hub.local(s.root(self.app.cwd)).exists:
            return
        self._fetch_hub_episodes(s.repo_id)

    @work(thread=True, exclusive=True, group="hub-check")
    def _fetch_hub_episodes(self, repo_id: str) -> None:
        n = hub.hub_episodes(repo_id)
        self.app.call_from_thread(self._set_hub_episodes, repo_id, n)

    def _set_hub_episodes(self, repo_id: str, n: int | None) -> None:
        if repo_id == self.s.repo_id:
            self.hub_episodes = n
            self.refresh_view()

    # --- actions --------------------------------------------------------------------------------------------

    def action_record(self) -> None:
        c = self._check()
        if not c.ok:
            self._shown_problems = True
            self.refresh_view()
            if c.focus == "arm":
                self.query_one("#arm", Button).focus()
            elif c.focus:
                self.query_one(f"#{c.focus}", Input).focus()
            return
        self._shown_problems = False
        if c.warnings:
            self.app.push_screen(ConfirmScreen("\n".join(c.warnings)), lambda yes: yes and self._start())
        else:
            self._start()

    def _start(self) -> None:
        from .record import RecordScreen

        s = self.s
        s.remember_task(s.task)
        self.app.save()
        root = s.root(self.app.cwd)
        local = hub.local(root)
        args = command.record_args(s, resume=local.valid, cwd=self.app.cwd)
        self.app.push_screen(RecordScreen(args, earlier=local.episodes if local.valid else 0))

    def action_setup(self, tab: str = "hub") -> None:
        from .setup import SetupScreen

        self.app.push_screen(SetupScreen(tab))

    def action_command(self) -> None:
        root = self.s.root(self.app.cwd)
        args = command.record_args(self.s, resume=hub.local(root).valid, cwd=self.app.cwd)
        self.app.push_screen(CommandScreen(command.shell(args)))

    async def action_language(self) -> None:
        self.app.toggle_language()
        await self.recompose()
        self.on_mount()

    def action_quit(self) -> None:
        self.app.exit()


class CommandScreen(ModalScreen):
    """The lerobot-record command this sentence runs, to read or copy."""

    BINDINGS = [Binding("escape", "dismiss", show=False), Binding("c", "copy", show=False)]

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(self.text, markup=False)
            yield Static(f"\n[{ACCENT}]c[/] {t('k copy')}   [{ACCENT}]esc[/] {t('k close')}", classes="dim")

    def action_copy(self) -> None:
        self.app.copy_to_clipboard(self.text)
        self.dismiss()


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "no", show=False), Binding("enter", "yes", show=False)]

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"[{ACCENT}]![/] {self.text}")
            yield Static(f"\n{t('confirm hub')}", classes="dim")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _rel(path, cwd) -> str:
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return checks.short(path)

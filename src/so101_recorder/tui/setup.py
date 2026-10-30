"""Setup: the Hugging Face login, which USB port is which arm, which camera is which, and the options."""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static, Switch, TabbedContent, TabPane

from .. import devices, hub
from ..checks import short
from ..i18n import t
from ..settings import Camera
from .theme import ACCENT, DIM, ERROR, OK

SWITCHES = [("push", "opt push"), ("private", "opt private"), ("display", "opt display"),
            ("sounds", "opt sounds"), ("streaming", "opt streaming"), ("global_keys", "opt global")]


class SetupScreen(Screen):
    BINDINGS = [Binding("escape", "close", show=False)]

    def __init__(self, tab: str = "hub"):
        super().__init__()
        self.tab = tab
        self.ports: list[str] = []
        self.port_event = ""
        self._polled = False
        self.preview: devices.Preview | None = None

    @property
    def s(self):
        return self.app.settings

    def compose(self) -> ComposeResult:
        s = self.s
        with Vertical(id="setup"):
            yield Static(t("setup"), classes="title")
            with TabbedContent(initial=self.tab):
                with TabPane(t("tab hub"), id="hub"):
                    yield Static(id="hub-status")
                    yield Static(t("hub token help"), classes="dim help")
                    with Horizontal(classes="row"):
                        yield Input(id="token", password=True, placeholder=t("token placeholder"))
                        yield Button(t("save token"), id="save-token")
                        yield Button(t("logout"), id="logout")
                with TabPane(t("tab arms"), id="arms"):
                    yield Static(id="ports")
                    for role in ("follower", "leader"):
                        with Horizontal(classes="row"):
                            yield Label(t(f"{role} port"))
                            yield Select([], id=f"{role}-port", allow_blank=True, prompt="—")
                            yield Label(t("id"), classes="short")
                            yield Input(getattr(s, f"{role}_id"), id=f"{role}-id", classes="small")
                    with Horizontal(classes="row"):
                        yield Label(t("calibration dir"))
                        yield Input(s.calibration_dir, id="calibration-dir", placeholder=t("calibration default"))
                    yield Static(id="cal-status")
                with TabPane(t("tab cameras"), id="cameras"):
                    with VerticalScroll():
                        yield Static(t("cam help"), classes="dim help")
                        with Horizontal(classes="row"):
                            yield Button(t("swap"), id="cam-swap")
                            yield Button(t("add camera"), id="cam-add")
                            yield Button(t("remove camera"), id="cam-remove")
                            yield Button(t("scan"), id="cam-scan")
                        with Horizontal(classes="row"):
                            yield Label(t("cam size"))
                            yield Input(_size(s.cameras), id="cam-size", classes="small")
                        yield Static(id="scan-result", classes="dim")
                        yield Horizontal(id="cam-grid")
                with TabPane(t("tab options"), id="options"):
                    with VerticalScroll():
                        for key, label, value in (("episode_s", "episode s", s.episode_s),
                                                  ("reset_s", "reset s", s.reset_s), ("fps", "fps", s.fps)):
                            with Horizontal(classes="row"):
                                yield Label(t(label))
                                yield Input(_num(value), id=f"opt-{key}", classes="small opt",
                                            restrict=r"[0-9.]*")
                        with Horizontal(classes="row"):
                            yield Label(t("data dir"))
                            yield Input(s.data_dir, id="opt-data_dir", classes="opt")
                        for key, label in SWITCHES:
                            with Horizontal(classes="row"):
                                yield Switch(getattr(s, key), id=f"opt-{key}")
                                yield Label(t(label))
            yield Static(f"[{ACCENT}]esc[/] {t('k home')}", classes="keys")

    async def on_mount(self) -> None:
        self.refresh_view()
        self.poll_ports()
        self.set_interval(1.0, self.poll_ports)
        await self._build_cameras()
        if self.tab == "cameras":
            self._start_preview()

    def refresh_view(self) -> None:
        acc = self.app.account
        if acc is None:
            text = t("hub checking")
        elif acc.ok:
            text = f"[{OK}]●[/] {t('hub as', user=acc.user)}"
            if acc.orgs:
                text += f"   [{DIM}]{t('hub orgs', orgs=', '.join(acc.orgs))}[/]"
        elif acc.error:
            text = f"[{ERROR}]●[/] {t('hub error', e=acc.error)}"
        else:
            text = f"[{DIM}]○[/] {t('hub none')}"
        self.query_one("#hub-status", Static).update(text)
        self._cal_status()

    # --- Hugging Face ---------------------------------------------------------------------------------------

    @on(Button.Pressed, "#save-token")
    @on(Input.Submitted, "#token")
    def save_token(self) -> None:
        token = self.query_one("#token", Input).value.strip()
        if token:
            self.query_one("#hub-status", Static).update(t("hub checking"))
            self._login(token)

    @work(thread=True, exclusive=True, group="login")
    def _login(self, token: str) -> None:
        try:
            acc = hub.login(token)
        except Exception as e:
            acc = hub.Account(error=str(e).splitlines()[0][:200])
        self.app.call_from_thread(self._logged_in, acc)

    def _logged_in(self, acc: hub.Account) -> None:
        if acc.ok:
            self.query_one("#token", Input).value = ""
        self.app.set_account(acc)

    @on(Button.Pressed, "#logout")
    def logout(self) -> None:
        hub.logout()
        self.app.set_account(hub.Account())

    # --- arms -----------------------------------------------------------------------------------------------

    def poll_ports(self) -> None:
        ports = devices.list_ports()
        if self._polled and ports == self.ports:
            return
        if self._polled:
            gone, new = sorted(set(self.ports) - set(ports)), sorted(set(ports) - set(self.ports))
            if gone:
                self.port_event = t("port unplugged", port=", ".join(gone))
            elif new:
                self.port_event = t("port plugged", port=", ".join(new))
        self._polled = True
        self.ports = ports
        lines = [f"  {p}" for p in ports] or [f"  {t('no ports')}"]
        text = "\n".join(lines) + f"\n[{DIM}]{t('ports help')}[/]"
        if self.port_event:
            text += f"\n[{ACCENT}]↳ {self.port_event}[/]"
        self.query_one("#ports", Static).update(text)
        for role in ("follower", "leader"):
            current = getattr(self.s, f"{role}_port")
            options = list(ports) + ([current] if current and current not in ports else [])
            sel = self.query_one(f"#{role}-port", Select)
            with self.prevent(Select.Changed):
                sel.set_options([(p if p in ports else f"{p}  (not plugged in)", p) for p in options])
                if current:
                    sel.value = current

    @on(Select.Changed)
    def port_changed(self, event: Select.Changed) -> None:
        role = (event.select.id or "").removesuffix("-port")
        if role in ("follower", "leader"):
            setattr(self.s, f"{role}_port", "" if event.value is Select.NULL else str(event.value))
            self.app.save()

    @on(Input.Changed, "#follower-id, #leader-id, #calibration-dir")
    def arm_text_changed(self, event: Input.Changed) -> None:
        key = {"follower-id": "follower_id", "leader-id": "leader_id", "calibration-dir": "calibration_dir"}
        setattr(self.s, key[event.input.id], event.value.strip())
        self.app.save()
        self._cal_status()

    def _cal_status(self) -> None:
        lines = []
        for role in ("follower", "leader"):
            path = self.s.calibration_file(role)
            if path.is_file():
                lines.append(f"[{OK}]{t('cal found', role=role, path=short(path))}[/]")
            else:
                lines.append(f"[{ERROR}]{t('cal missing', role=role, path=short(path))}[/]")
        self.query_one("#cal-status", Static).update("\n".join(lines))

    # --- cameras --------------------------------------------------------------------------------------------

    async def _build_cameras(self) -> None:
        grid = self.query_one("#cam-grid", Horizontal)
        await grid.remove_children()
        boxes = []
        for i, cam in enumerate(self.s.cameras):
            box = Vertical(
                Horizontal(
                    Input(cam.name, id=f"cam-name-{i}", classes="cam-name"),
                    Input(str(cam.index), id=f"cam-index-{i}", classes="cam-index small"),
                    classes="row",
                ),
                Static(t("no picture"), id=f"cam-preview-{i}", classes="preview"),
                classes="cam",
            )
            boxes.append(box)
        await grid.mount_all(boxes)

    def _start_preview(self) -> None:
        self._stop_preview(wait=False)
        indices = sorted({c.index for c in self.s.cameras if isinstance(c.index, int)})
        if not indices:
            return
        self.preview = devices.Preview(indices, self._frame_from_thread).start()

    def _stop_preview(self, wait: bool = True) -> None:
        if self.preview is not None:
            self.preview.stop(wait=wait)
            self.preview = None

    def _frame_from_thread(self, index: int, text) -> None:
        try:
            self.app.call_from_thread(self._frame, index, text)
        except Exception:
            pass

    def _frame(self, index: int, text) -> None:
        for i, cam in enumerate(self.s.cameras):
            if cam.index == index:
                for w in self.query(f"#cam-preview-{i}"):
                    w.update(text if text is not None else t("no picture"))

    @on(TabbedContent.TabActivated)
    def tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.pane.id == "cameras":
            self._start_preview()
        else:
            self._stop_preview(wait=False)

    @on(Input.Changed, ".cam-name, .cam-index")
    def cam_changed(self, event: Input.Changed) -> None:
        kind, i = event.input.id.rsplit("-", 1)[0], int(event.input.id.rsplit("-", 1)[1])
        if i >= len(self.s.cameras):
            return
        cam = self.s.cameras[i]
        value = event.value.strip()
        if kind == "cam-name":
            if value:
                cam.name = value
        else:
            if not value:
                return
            new = int(value) if value.isdigit() else value
            if new != cam.index:
                cam.index = new
                self._start_preview()
        self.app.save()

    @on(Input.Changed, "#cam-size")
    def size_changed(self, event: Input.Changed) -> None:
        parsed = _parse_size(event.value)
        if parsed:
            for cam in self.s.cameras:
                cam.width, cam.height, cam.fps = parsed
            self.app.save()

    @on(Button.Pressed, "#cam-swap")
    async def cam_swap(self) -> None:
        cams = self.s.cameras
        if len(cams) >= 2:
            cams[0].index, cams[1].index = cams[1].index, cams[0].index
            self.app.save()
            await self._build_cameras()
            self._start_preview()

    @on(Button.Pressed, "#cam-add")
    async def cam_add(self) -> None:
        used = {c.index for c in self.s.cameras}
        index = next(i for i in range(32) if i not in used)
        size = self.s.cameras[0] if self.s.cameras else Camera("x", 0)
        self.s.cameras.append(Camera(f"cam{len(self.s.cameras) + 1}", index, size.width, size.height, size.fps))
        self.app.save()
        await self._build_cameras()
        self._start_preview()

    @on(Button.Pressed, "#cam-remove")
    async def cam_remove(self) -> None:
        if self.s.cameras:
            self.s.cameras.pop()
            self.app.save()
            await self._build_cameras()
            self._start_preview()

    @on(Button.Pressed, "#cam-scan")
    def cam_scan(self) -> None:
        self._stop_preview(wait=False)
        self.query_one("#scan-result", Static).update(t("scanning"))
        self._scan()

    @work(thread=True, exclusive=True, group="scan")
    def _scan(self) -> None:
        if self.preview is not None:
            self.preview.stop()
        found = devices.scan_cameras()
        self.app.call_from_thread(self._scanned, found)

    def _scanned(self, found: list[int]) -> None:
        self.query_one("#scan-result", Static).update(t("scan found", found=", ".join(map(str, found)) or "—"))
        self._start_preview()

    # --- options --------------------------------------------------------------------------------------------

    @on(Input.Changed, ".opt")
    def option_changed(self, event: Input.Changed) -> None:
        key = event.input.id.removeprefix("opt-")
        value = event.value.strip()
        if key == "data_dir":
            if value:
                self.s.data_dir = value
        else:
            try:
                number = float(value)
            except ValueError:
                return
            if number <= 0:
                return
            setattr(self.s, key, int(number) if key == "fps" else number)
        self.app.save()

    @on(Switch.Changed)
    def switch_changed(self, event: Switch.Changed) -> None:
        key = (event.switch.id or "").removeprefix("opt-")
        if any(key == k for k, _ in SWITCHES):
            setattr(self.s, key, event.value)
            self.app.save()

    # --- leaving --------------------------------------------------------------------------------------------

    def action_close(self) -> None:
        self._stop_preview()  # the cameras must be free before lerobot-record opens them
        self.app.pop_screen()

    def on_unmount(self) -> None:
        self._stop_preview()


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _size(cams: list[Camera]) -> str:
    c = cams[0] if cams else Camera("x", 0)
    return f"{c.width}x{c.height}@{c.fps}"


def _parse_size(text: str) -> tuple[int, int, int] | None:
    try:
        wh, _, fps = text.strip().lower().partition("@")
        w, _, h = wh.partition("x")
        return int(w), int(h), int(fps or 30)
    except ValueError:
        return None

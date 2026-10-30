"""The Textual application: owns the settings and the Hugging Face account; screens read and change them."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App
from textual.binding import Binding

from .. import hub, i18n
from .. import settings as settings_mod
from .home import HomeScreen
from .theme import CSS


class RecApp(App):
    TITLE = "so101-recorder"
    CSS = CSS
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [Binding("ctrl+c", "ctrl_c", show=False, priority=True)]

    def __init__(self, *, settings_path: Path | None = None, cwd: Path | None = None, lang: str | None = None,
                 check_hub: bool = True):
        super().__init__()
        self.settings_path = settings_path
        self.settings = settings_mod.load(settings_path)
        self.cwd = cwd or Path.cwd()
        self.account: hub.Account | None = None  # None while it is being checked
        self.check_hub = check_hub
        i18n.set_lang(lang or self.settings.lang or i18n.detect())

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())
        if self.check_hub:
            self.refresh_account()
        else:
            self.account = hub.Account()

    def save(self) -> None:
        settings_mod.save(self.settings, self.settings_path)

    @work(thread=True, exclusive=True, group="account")
    def refresh_account(self) -> None:
        acc = hub.account()
        self.call_from_thread(self.set_account, acc)

    def set_account(self, acc: hub.Account) -> None:
        self.account = acc
        if acc.ok and (not self.settings.namespace or self.settings.namespace not in acc.namespaces):
            self.settings.namespace = acc.user
            self.save()
        refresh = getattr(self.screen, "refresh_view", None)
        if refresh:
            refresh()

    def toggle_language(self) -> None:
        lang = "en" if i18n.get_lang() == "tr" else "tr"
        i18n.set_lang(lang)
        self.settings.lang = lang
        self.save()

    def action_ctrl_c(self) -> None:
        handler = getattr(self.screen, "on_ctrl_c", None)
        if handler:
            handler()
        else:
            self.exit()

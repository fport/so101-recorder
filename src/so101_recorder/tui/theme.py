"""Colours and the stylesheet. The same graphite and orange as so101-calibrator: orange is what matters now."""

from __future__ import annotations

BG = "#0b0b0b"
SURFACE = "#1c1c1c"
RAISED = "#2a2a2a"
DIM = "#5e5e5e"
FG = "#ededed"
ACCENT = "#ff7a1a"
RESET = "#5aa2ff"  # the reset phase: not recording
ERROR = "#ff5f56"
OK = "#5fd068"

CSS = f"""
Screen {{ background: {BG}; color: {FG}; }}
* {{ scrollbar-color: {RAISED}; scrollbar-color-hover: {DIM}; scrollbar-color-active: {ACCENT};
    scrollbar-background: {BG}; scrollbar-background-hover: {BG}; scrollbar-background-active: {BG};
    scrollbar-size-vertical: 1; }}
.dim {{ color: {DIM}; }}
.keys {{ dock: bottom; height: 1; margin: 0 2 1 2; color: {DIM}; }}
.title {{ text-style: bold; margin: 0 0 1 0; }}

/* home: the sentence */
#home {{ height: 100%; padding: 1 2; }}
#topbar {{ height: 1; color: {DIM}; }}
#sentence {{ height: 1fr; align: center middle; }}
.line {{ height: 1; width: auto; margin: 0 0 1 0; }}
.word {{ width: auto; padding: 0 1 0 0; text-style: bold; }}
Input.slot {{
    border: none; height: 1; padding: 0 1; margin: 0 1 0 0; width: 12;
    background: {SURFACE}; color: {ACCENT}; text-style: bold;
}}
Input.slot:focus {{ background: {RAISED}; border: none; }}
Input.slot > .input--placeholder {{ color: {DIM}; text-style: italic; }}
Input.slot > .input--suggestion {{ color: {DIM}; }}
Input.slot > .input--cursor {{ background: {ACCENT}; color: {BG}; }}
Input > .input--selection {{ background: {ACCENT} 35%; }}
Button.chip {{
    border: none; height: 1; min-width: 4; width: auto; padding: 0 1; margin: 0 1 0 0;
    background: {SURFACE}; color: {FG}; text-style: bold;
}}
Button.chip:hover {{ background: {RAISED}; }}
Button.chip:focus {{ background: {RAISED}; color: {ACCENT}; text-style: bold; }}
Button.chip.-todo {{ color: {ACCENT}; }}
#go {{ background: {ACCENT}; color: {BG}; }}
#go:focus {{ background: {FG}; color: {BG}; }}
#summary {{ width: auto; height: auto; color: {DIM}; margin: 1 0 0 0; }}
#problems {{ width: auto; max-width: 100; height: auto; margin: 1 0 0 0; }}

/* recording */
#rec {{ height: 100%; padding: 1 2; }}
#rec-head {{ height: auto; }}
#rec-phase {{ height: 1; margin: 1 0 0 0; }}
#rec-bar {{ height: 1; margin: 1 0 0 0; }}
#rec-dots {{ height: 1; margin: 1 0 0 0; }}
#rec-message {{ height: auto; margin: 1 0 0 0; }}
#rec-log {{ height: 1fr; margin: 1 0 1 0; border: none; background: {BG}; color: {DIM}; scrollbar-size-vertical: 1; }}

/* modal */
CommandScreen, ConfirmScreen {{ align: center middle; background: {BG} 80%; }}
#dialog {{ width: auto; max-width: 110; height: auto; padding: 1 2; background: {SURFACE}; }}
#dialog Static {{ width: auto; }}

/* setup */
#setup {{ height: 100%; padding: 1 2; }}
TabbedContent {{ height: 1fr; }}
TabPane {{ padding: 1 0; }}
Tabs {{ background: {BG}; }}
Tab {{ color: {DIM}; }}
Tab.-active {{ color: {FG}; }}
Tabs:focus Tab.-active {{ background: {SURFACE}; color: {ACCENT}; text-style: bold; }}
Underline > .underline--bar {{ color: {ACCENT}; background: {SURFACE}; }}
.row {{ height: 3; width: 100%; margin: 0 0 0 0; }}
.row Label {{ width: 22; height: 3; content-align: left middle; color: {DIM}; }}
.row Label.short {{ width: 6; padding: 0 0 0 2; }}
.row Input {{ width: 1fr; max-width: 50; }}
.row Input.small {{ width: 16; }}
.row Select {{ width: 44; }}
.row Switch {{ margin: 0 2 0 0; }}
.row Button {{ margin: 0 1 0 0; min-width: 8; }}
Input {{ background: {SURFACE}; border: tall {SURFACE}; }}
Input:focus {{ border: tall {ACCENT}; }}
Select > SelectCurrent {{ background: {SURFACE}; border: tall {SURFACE}; }}
Select:focus > SelectCurrent {{ border: tall {ACCENT}; }}
Switch {{ background: {SURFACE}; border: tall {SURFACE}; }}
Switch:focus {{ border: tall {ACCENT}; }}
Switch > .switch--slider {{ color: {RAISED}; background: {SURFACE}; }}
Switch.-on > .switch--slider {{ color: {ACCENT}; }}
Button {{ background: {SURFACE}; border: tall {SURFACE}; color: {FG}; }}
Button:focus {{ border: tall {ACCENT}; text-style: bold; }}
Button:hover {{ background: {RAISED}; }}
.help {{ margin: 0 0 1 0; max-width: 100; height: auto; }}
#hub-status, #ports, #cal-status, #scan-result {{ height: auto; margin: 0 0 1 0; }}
#cam-grid {{ height: auto; }}
.cam {{ width: auto; height: auto; margin: 1 3 0 0; }}
.cam .row Input {{ width: 14; }}
.preview {{ width: 40; height: 15; background: {SURFACE}; color: {DIM}; content-align: center middle; }}
"""

# $Id$
#
# Author: Vasilis Vlachoudis
#  Email: vvlachoudis@gmail.com
#   Date: 18-Jun-2015

# import time
import math
import sys
from tkinter import (
    YES,
    N,
    S,
    W,
    E,
    NW,
    SW,
    NE,
    SE,
    EW,
    NSEW,
    CENTER,
    NONE,
    X,
    BOTH,
    LEFT,
    TOP,
    RIGHT,
    BOTTOM,
    HORIZONTAL,
    END,
    NORMAL,
    DISABLED,
    Entry,
    StringVar,
    IntVar,
    BooleanVar,
    Button,
    Checkbutton,
    Label,
    Scale,
    Spinbox,
    LabelFrame,
    messagebox,
)

import Camera
import CNCRibbon
import Ribbon
import tkExtra
import Utils
from CNC import CNC, Block
import os
from SurfAlignUtils import setup_blender_scene
from Helpers import N_

__author__ = Utils.__author__
__email__ = Utils.__email__

PROBE_CMD = [
    _("G38.2 stop on contact else error"),
    _("G38.3 stop on contact"),
    _("G38.4 stop on loss contact else error"),
    _("G38.5 stop on loss contact"),
]

TOOL_POLICY = [
    _("Send M6 commands"),  # 0
    _("Ignore M6 commands"),  # 1
    _("Manual Tool Change (WCS)"),  # 2
    _("Manual Tool Change (TLO)"),  # 3
    _("Manual Tool Change (NoProbe)"),  # 4
]

TOOL_WAIT = [_("ONLY before probing"), _("BEFORE & AFTER probing")]

CAMERA_LOCATION = {
    "Gantry": NONE,
    "Top-Left": NW,
    "Top": N,
    "Top-Right": NE,
    "Left": W,
    "Center": CENTER,
    "Right": E,
    "Bottom-Left": SW,
    "Bottom": S,
    "Bottom-Right": SE,
}
CAMERA_LOCATION_ORDER = [
    "Gantry",
    "Top-Left",
    "Top",
    "Top-Right",
    "Left",
    "Center",
    "Right",
    "Bottom-Left",
    "Bottom",
    "Bottom-Right",
]


# =============================================================================
# Probe Tab Group
# =============================================================================
class ProbeTabGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, N_("SurfAlign"), app)

        self.tab = StringVar()
        # ---
        col, row = 0, 0
        b = Ribbon.LabelRadiobutton(
            self.frame,
            image=Utils.icons["probe32"],
            text=_("Probe"),
            compound=TOP,
            variable=self.tab,
            value="Probe",
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=5, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Simple probing along a direction"))

        # ---
        col += 1
        b = Ribbon.LabelRadiobutton(
            self.frame,
            image=Utils.icons["level32"],
            text=_("Autolevel"),
            compound=TOP,
            variable=self.tab,
            value="Autolevel",
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=5, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Autolevel Z surface"))

        # ---
        col += 1
        b = Ribbon.LabelRadiobutton(
            self.frame,
            image=Utils.icons["camera32"],
            text=_("Camera"),
            compound=TOP,
            variable=self.tab,
            value="Camera",
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=5, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Work surface camera view and alignment"))
        if Camera.cv is None:
            b.config(state=DISABLED)

        # ---
        col += 1
        b = Ribbon.LabelRadiobutton(
            self.frame,
            image=Utils.icons["endmill32"],
            text=_("Tool"),
            compound=TOP,
            variable=self.tab,
            value="Tool",
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=5, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Setup probing for manual tool change"))

        self.frame.grid_rowconfigure(0, weight=1)


# =============================================================================
# Autolevel Group
# =============================================================================
class AutolevelGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, "Probe:Autolevel", app)
        self.label["background"] = Ribbon._BACKGROUND_GROUP2
        self.grid3rows()

        # ---
        col, row = 0, 0
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<AutolevelMargins>>",
            image=Utils.icons["margins"],
            text=_("Margins"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Get margins from gcode file"))
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<AutolevelZero>>",
            image=Utils.icons["origin"],
            text=_("Zero"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b,
            _(
                "Set current XY location as autoleveling Z-zero (recalculate "
                + "probed data to be relative to this XY origin point)"
            ),
        )
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<AutolevelClear>>",
            image=Utils.icons["clear"],
            text=_("Clear"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Clear probe data"))
        self.addWidget(b)

        # ---
        row = 0
        col += 1
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<AutolevelScanMargins>>",
            image=Utils.icons["margins"],
            text=_("Scan"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Scan Autolevel Margins"))
        self.addWidget(b)

        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["level"],
            text=_("Autolevel"),
            compound=LEFT,
            anchor=W,
            command=lambda a=app: a.insertCommand("AUTOLEVEL", True),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Modify selected G-Code to match autolevel"))
        self.addWidget(b)

        # ---
        col, row = 2, 0
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<AutolevelScan>>",
            image=Utils.icons["gear32"],
            text=_("Scan"),
            compound=TOP,
            justify=CENTER,
            width=48,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
        self.addWidget(b)
        tkExtra.Balloon.set(
            b, _("Scan probed area for level information on Z plane"))


# =============================================================================
# Probe Common Offset
# =============================================================================
class ProbeCommonFrame(CNCRibbon.PageFrame):
    probeFeed = None
    tlo = None
    probeCmd = None

    def __init__(self, master, app):
        CNCRibbon.PageFrame.__init__(self, master, "ProbeCommon1", app)

        lframe = tkExtra.ExLabelFrame(
            self, text=_("Common"), foreground="DarkBlue")
        lframe.pack(side=TOP, fill=X)
        frame = lframe.frame

        # ----
        row = 0
        col = 0

        # ----
        # Fast Probe Feed
        Label(frame,
              text=_("Fast Probe Feed:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.fastProbeFeed = StringVar()
        self.fastProbeFeed.trace(
            "w", lambda *_: ProbeCommonFrame.probeUpdate())
        ProbeCommonFrame.fastProbeFeed = tkExtra.FloatEntry(
            frame,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            width=5,
            textvariable=self.fastProbeFeed,
        )
        ProbeCommonFrame.fastProbeFeed.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            ProbeCommonFrame.fastProbeFeed,
            _("Set initial probe feed rate for tool change and calibration"),
        )
        self.addWidget(ProbeCommonFrame.fastProbeFeed)

        # ----
        # Probe Feed
        row += 1
        col = 0
        Label(frame, text=_("Probe Feed:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.probeFeedVar = StringVar()
        self.probeFeedVar.trace("w", lambda *_: ProbeCommonFrame.probeUpdate())
        ProbeCommonFrame.probeFeed = tkExtra.FloatEntry(
            frame,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            width=5,
            textvariable=self.probeFeedVar,
        )
        ProbeCommonFrame.probeFeed.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            ProbeCommonFrame.probeFeed, _("Set probe feed rate"))
        self.addWidget(ProbeCommonFrame.probeFeed)

        # ----
        # Tool offset
        row += 1
        col = 0
        Label(frame, text=_("TLO")).grid(row=row, column=col, sticky=E)
        col += 1
        ProbeCommonFrame.tlo = tkExtra.FloatEntry(
            frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        ProbeCommonFrame.tlo.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            ProbeCommonFrame.tlo, _("Set tool offset for probing"))
        self.addWidget(ProbeCommonFrame.tlo)
        self.tlo.bind("<Return>", self.tloSet)
        self.tlo.bind("<KP_Enter>", self.tloSet)

        col += 1
        b = Button(frame, text=_("set"), command=self.tloSet, padx=2, pady=1)
        b.grid(row=row, column=col, sticky=EW)
        self.addWidget(b)

        # ---
        # feed command
        row += 1
        col = 0
        Label(frame,
              text=_("Probe Command")).grid(row=row, column=col, sticky=E)
        col += 1
        ProbeCommonFrame.probeCmd = tkExtra.Combobox(
            frame,
            True,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            width=16,
            command=ProbeCommonFrame.probeUpdate,
        )
        ProbeCommonFrame.probeCmd.grid(row=row, column=col, sticky=EW)
        ProbeCommonFrame.probeCmd.fill(PROBE_CMD)
        self.addWidget(ProbeCommonFrame.probeCmd)

        frame.grid_columnconfigure(1, weight=1)
        self.loadConfig()

    # ------------------------------------------------------------------------
    def tloSet(self, event=None):
        try:
            CNC.vars["TLO"] = float(ProbeCommonFrame.tlo.get())
            cmd = f"G43.1Z{ProbeCommonFrame.tlo.get()}"
            self.sendGCode(cmd)
        except Exception:
            pass
        self.app.mcontrol.viewParameters()

    # ------------------------------------------------------------------------
    @staticmethod
    def probeUpdate():
        try:
            CNC.vars["fastprbfeed"] = float(
                ProbeCommonFrame.fastProbeFeed.get())
            CNC.vars["prbfeed"] = float(ProbeCommonFrame.probeFeed.get())
            CNC.vars["prbcmd"] = str(
                ProbeCommonFrame.probeCmd.get().split()[0])
            return False
        except Exception:
            return True

    # ------------------------------------------------------------------------
    def updateTlo(self):
        try:
            if self.focus_get() is not ProbeCommonFrame.tlo:
                state = ProbeCommonFrame.tlo.cget("state")
                state = ProbeCommonFrame.tlo["state"] = NORMAL
                ProbeCommonFrame.tlo.set(str(CNC.vars.get("TLO", "")))
                state = ProbeCommonFrame.tlo["state"] = state
        except Exception:
            pass

    # -----------------------------------------------------------------------
    def saveConfig(self):
        Utils.setFloat("Probe",
                       "fastfeed", ProbeCommonFrame.fastProbeFeed.get())
        Utils.setFloat("Probe", "feed", ProbeCommonFrame.probeFeed.get())
        Utils.setFloat("Probe", "tlo", ProbeCommonFrame.tlo.get())
        Utils.setFloat("Probe", "cmd",
                       ProbeCommonFrame.probeCmd.get().split()[0])

    # -----------------------------------------------------------------------
    def loadConfig(self):
        ProbeCommonFrame.fastProbeFeed.set(Utils.getFloat("Probe", "fastfeed"))
        ProbeCommonFrame.probeFeed.set(Utils.getFloat("Probe", "feed"))
        ProbeCommonFrame.tlo.set(Utils.getFloat("Probe", "tlo"))
        cmd = Utils.getStr("Probe", "cmd")
        for p in PROBE_CMD:
            if p.split()[0] == cmd:
                ProbeCommonFrame.probeCmd.set(p)
                break


# =============================================================================
# Probe Frame
# =============================================================================
class ProbeFrame(CNCRibbon.PageFrame):
    def __init__(self, master, app):
        CNCRibbon.PageFrame.__init__(self, master, "ProbeCommon2", app)

        # ----------------------------------------------------------------
        # Record point
        # ----------------------------------------------------------------

        recframe = tkExtra.ExLabelFrame(
            self, text=_("Record"), foreground="DarkBlue")
        recframe.pack(side=TOP, expand=YES, fill=X)

        self.recz = IntVar()
        self.reczb = Checkbutton(
            recframe(),
            text=_("Z"),
            variable=self.recz,  # onvalue=1, offvalue=0,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        tkExtra.Balloon.set(self.reczb, _("Record Z coordinate?"))
        self.reczb.pack(side=LEFT, expand=YES, fill=X)
        self.addWidget(self.reczb)

        self.rr = Button(
            recframe(),
            text=_("RAPID"),
            command=self.recordRapid,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        self.rr.pack(side=LEFT, expand=YES, fill=X)
        self.addWidget(self.rr)

        self.rr = Button(
            recframe(),
            text=_("FEED"),
            command=self.recordFeed,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        self.rr.pack(side=LEFT, expand=YES, fill=X)
        self.addWidget(self.rr)

        self.rr = Button(
            recframe(),
            text=_("POINT"),
            command=self.recordPoint,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        self.rr.pack(side=LEFT, expand=YES, fill=X)
        self.addWidget(self.rr)

        self.rr = Button(
            recframe(),
            text=_("CIRCLE"),
            command=self.recordCircle,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        self.rr.pack(side=LEFT, expand=YES, fill=X)
        self.addWidget(self.rr)

        self.rr = Button(
            recframe(),
            text=_("FINISH"),
            command=self.recordFinishAll,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        self.rr.pack(side=LEFT, expand=YES, fill=X)
        self.addWidget(self.rr)

        self.recsiz = tkExtra.FloatEntry(
            recframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        tkExtra.Balloon.set(self.recsiz, _("Circle radius"))
        self.recsiz.set(10)
        self.recsiz.pack(side=BOTTOM, expand=YES, fill=X)
        self.addWidget(self.recsiz)

        # ----------------------------------------------------------------
        # Single probe
        # ----------------------------------------------------------------
        lframe = tkExtra.ExLabelFrame(
            self, text=_("Probe"), foreground="DarkBlue")
        lframe.pack(side=TOP, fill=X)

        row, col = 0, 0
        Label(lframe(), text=_("Probe:")).grid(row=row, column=col, sticky=E)

        col += 1
        self._probeX = Label(
            lframe(), foreground="DarkBlue", background="gray90")
        self._probeX.grid(row=row, column=col, padx=1, sticky=EW + S)

        col += 1
        self._probeY = Label(
            lframe(), foreground="DarkBlue", background="gray90")
        self._probeY.grid(row=row, column=col, padx=1, sticky=EW + S)

        col += 1
        self._probeZ = Label(
            lframe(), foreground="DarkBlue", background="gray90")
        self._probeZ.grid(row=row, column=col, padx=1, sticky=EW + S)

        # ---
        col += 1
        self.probeautogotonext = False
        self.probeautogoto = IntVar()
        self.autogoto = Checkbutton(
            lframe(),
            "",
            variable=self.probeautogoto,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )

        if self.probeautogoto.get() != 0:
            self.autogoto.select()
        tkExtra.Balloon.set(self.autogoto, _("Automatic GOTO after probing"))
        self.autogoto.grid(row=row, column=col, padx=1, sticky=EW)
        self.addWidget(self.autogoto)

        # ---
        col += 1
        b = Button(
            lframe(),
            image=Utils.icons["rapid"],
            text=_("Goto"),
            compound=LEFT,
            command=self.goto2Probe,
            padx=5,
            pady=0,
        )
        b.grid(row=row, column=col, padx=1, sticky=EW)
        self.addWidget(b)
        tkExtra.Balloon.set(b, _("Rapid goto to last probe location"))

        # ---
        row, col = row + 1, 0
        Label(lframe(), text=_("Pos:")).grid(row=row, column=col, sticky=E)

        col += 1
        self.probeXdir = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.probeXdir.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.probeXdir, _("Probe along X direction"))
        self.addWidget(self.probeXdir)

        col += 1
        self.probeYdir = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.probeYdir.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.probeYdir, _("Probe along Y direction"))
        self.addWidget(self.probeYdir)

        col += 1
        self.probeZdir = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.probeZdir.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.probeZdir, _("Probe along Z direction"))
        self.addWidget(self.probeZdir)

        # ---
        col += 2
        b = Button(
            lframe(),  # "<<Probe>>",
            image=Utils.icons["probe32"],
            text=_("Probe"),
            compound=LEFT,
            command=self.probe,
            padx=5,
            pady=0,
        )
        b.grid(row=row, column=col, padx=1, sticky=EW)
        self.addWidget(b)
        tkExtra.Balloon.set(b, _("Perform a single probe cycle"))

        lframe().grid_columnconfigure(1, weight=1)
        lframe().grid_columnconfigure(2, weight=1)
        lframe().grid_columnconfigure(3, weight=1)

        # ----------------------------------------------------------------
        # Center probing
        # ----------------------------------------------------------------
        lframe = tkExtra.ExLabelFrame(
            self, text=_("Center"), foreground="DarkBlue")
        lframe.pack(side=TOP, expand=YES, fill=X)

        Label(lframe(), text=_("Diameter:")).pack(side=LEFT)
        self.diameter = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.diameter.pack(side=LEFT, expand=YES, fill=X)
        tkExtra.Balloon.set(
            self.diameter, _("Probing ring internal diameter"))
        self.addWidget(self.diameter)

        # ---
        b = Button(
            lframe(),
            image=Utils.icons["target32"],
            text=_("Center"),
            compound=TOP,
            command=self.probeCenter,
            width=48,
            padx=5,
            pady=0,
        )
        b.pack(side=RIGHT)
        self.addWidget(b)
        tkExtra.Balloon.set(b, _("Center probing using a ring"))

        # ----------------------------------------------------------------
        # Align / Orient / Square ?
        # ----------------------------------------------------------------
        lframe = tkExtra.ExLabelFrame(
            self, text=_("Orient"), foreground="DarkBlue")
        lframe.pack(side=TOP, expand=YES, fill=X)

        # ---
        row, col = 0, 0

        Label(lframe(), text=_("Markers:")).grid(row=row, column=col, sticky=E)
        col += 1

        self.scale_orient = Scale(
            lframe(),
            from_=0,
            to_=0,
            orient=HORIZONTAL,
            showvalue=1,
            state=DISABLED,
            command=self.changeMarker,
        )
        self.scale_orient.grid(row=row, column=col, columnspan=2, sticky=EW)
        tkExtra.Balloon.set(self.scale_orient, _("Select orientation marker"))

        # Add new point
        col += 2
        b = Button(
            lframe(),
            text=_("Add"),
            image=Utils.icons["add"],
            compound=LEFT,
            command=lambda s=self: s.event_generate("<<AddMarker>>"),
            padx=1,
            pady=1,
        )
        b.grid(row=row, column=col, sticky=NSEW)
        self.addWidget(b)
        tkExtra.Balloon.set(
            b,
            _(
                "Add an orientation marker. "
                "Jog first the machine to the marker position "
                "and then click on canvas to add the marker."
            ),
        )

        # ----
        row += 1
        col = 0
        Label(lframe(), text=_("Gcode:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.x_orient = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.x_orient.grid(row=row, column=col, sticky=EW)
        self.x_orient.bind("<FocusOut>", self.orientUpdate)
        self.x_orient.bind("<Return>", self.orientUpdate)
        self.x_orient.bind("<KP_Enter>", self.orientUpdate)
        tkExtra.Balloon.set(
            self.x_orient, _("GCode X coordinate of orientation point"))

        col += 1
        self.y_orient = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.y_orient.grid(row=row, column=col, sticky=EW)
        self.y_orient.bind("<FocusOut>", self.orientUpdate)
        self.y_orient.bind("<Return>", self.orientUpdate)
        self.y_orient.bind("<KP_Enter>", self.orientUpdate)
        tkExtra.Balloon.set(
            self.y_orient, _("GCode Y coordinate of orientation point"))

        # Buttons
        col += 1
        b = Button(
            lframe(),
            text=_("Delete"),
            image=Utils.icons["x"],
            compound=LEFT,
            command=self.orientDelete,
            padx=1,
            pady=1,
        )
        b.grid(row=row, column=col, sticky=EW)
        self.addWidget(b)
        tkExtra.Balloon.set(b, _("Delete current marker"))

        # ---
        row += 1
        col = 0

        Label(lframe(), text=_("WPos:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.xm_orient = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.xm_orient.grid(row=row, column=col, sticky=EW)
        self.xm_orient.bind("<FocusOut>", self.orientUpdate)
        self.xm_orient.bind("<Return>", self.orientUpdate)
        self.xm_orient.bind("<KP_Enter>", self.orientUpdate)
        tkExtra.Balloon.set(
            self.xm_orient, _("Machine X coordinate of orientation point")
        )

        col += 1
        self.ym_orient = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.ym_orient.grid(row=row, column=col, sticky=EW)
        self.ym_orient.bind("<FocusOut>", self.orientUpdate)
        self.ym_orient.bind("<Return>", self.orientUpdate)
        self.ym_orient.bind("<KP_Enter>", self.orientUpdate)
        tkExtra.Balloon.set(
            self.ym_orient, _("Machine Y coordinate of orientation point")
        )

        # Buttons
        col += 1
        b = Button(
            lframe(),
            text=_("Clear"),
            image=Utils.icons["clear"],
            compound=LEFT,
            command=self.orientClear,
            padx=1,
            pady=1,
        )
        b.grid(row=row, column=col, sticky=EW)
        self.addWidget(b)
        tkExtra.Balloon.set(b, _("Delete all markers"))

        # ---
        row += 1
        col = 0
        Label(lframe(), text=_("Angle:")).grid(row=row, column=col, sticky=E)

        col += 1
        self.angle_orient = Label(
            lframe(), foreground="DarkBlue", background="gray90", anchor=W
        )
        self.angle_orient.grid(
            row=row, column=col, columnspan=2, sticky=EW, padx=1, pady=1
        )

        # Buttons
        col += 2
        b = Button(
            lframe(),
            text=_("Orient"),
            image=Utils.icons["setsquare32"],
            compound=TOP,
            command=lambda a=app: a.insertCommand("ORIENT", True),
            padx=1,
            pady=1,
        )
        b.grid(row=row, rowspan=3, column=col, sticky=EW)
        self.addWidget(b)
        tkExtra.Balloon.set(b, _("Align GCode with the machine markers"))

        # ---
        row += 1
        col = 0
        Label(lframe(), text=_("Offset:")).grid(row=row, column=col, sticky=E)

        col += 1
        self.xo_orient = Label(
            lframe(), foreground="DarkBlue", background="gray90", anchor=W
        )
        self.xo_orient.grid(row=row, column=col, sticky=EW, padx=1)

        col += 1
        self.yo_orient = Label(
            lframe(), foreground="DarkBlue", background="gray90", anchor=W
        )
        self.yo_orient.grid(row=row, column=col, sticky=EW, padx=1)

        # ---
        row += 1
        col = 0
        Label(lframe(), text=_("Error:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.err_orient = Label(
            lframe(), foreground="DarkBlue", background="gray90", anchor=W
        )
        self.err_orient.grid(
            row=row, column=col, columnspan=2, sticky=EW, padx=1, pady=1
        )

        lframe().grid_columnconfigure(1, weight=1)
        lframe().grid_columnconfigure(2, weight=1)

        # ----------------------------------------------------------------
        self.warn = True
        self.loadConfig()

    # -----------------------------------------------------------------------
    def loadConfig(self):
        self.probeXdir.set(Utils.getStr("Probe", "x"))
        self.probeYdir.set(Utils.getStr("Probe", "y"))
        self.probeZdir.set(Utils.getStr("Probe", "z"))
        self.diameter.set(Utils.getStr("Probe", "center"))
        self.warn = Utils.getBool("Warning", "probe", self.warn)
        self.probeautogoto.set(Utils.getBool("Probe", "autogoto"))

    # -----------------------------------------------------------------------
    def saveConfig(self):
        Utils.setFloat("Probe", "x", self.probeXdir.get())
        Utils.setFloat("Probe", "y", self.probeYdir.get())
        Utils.setFloat("Probe", "z", self.probeZdir.get())
        Utils.setFloat("Probe", "center", self.diameter.get())
        Utils.setBool("Warning", "probe", self.warn)
        Utils.setInt("Probe", "autogoto", self.probeautogoto.get())

    # -----------------------------------------------------------------------
    def updateProbe(self):
        try:
            self._probeX["text"] = CNC.vars.get("prbx")
            self._probeY["text"] = CNC.vars.get("prby")
            self._probeZ["text"] = CNC.vars.get("prbz")
        except Exception:
            return

        if self.probeautogotonext:
            self.probeautogotonext = False
            self.goto2Probe()

    # -----------------------------------------------------------------------
    def warnMessage(self):
        if self.warn:
            ans = messagebox.askquestion(
                _("Probe connected?"),
                _(
                    "Please verify that the probe is connected.\n\n"
                    + "Show this message again?"
                ),
                icon="warning",
                parent=self.winfo_toplevel(),
            )
            if ans != YES:
                self.warn = False

    # -----------------------------------------------------------------------
    # Probe one Point
    # -----------------------------------------------------------------------
    def probe(self, event=None):
        if self.probeautogoto.get() == 1:
            self.probeautogotonext = True

        if ProbeCommonFrame.probeUpdate():
            messagebox.showerror(
                _("Probe Error"),
                _("Invalid probe feed rate"),
                parent=self.winfo_toplevel(),
            )
            return
        self.warnMessage()

        cmd = str(CNC.vars["prbcmd"])
        ok = False

        v = self.probeXdir.get()
        if v != "":
            cmd += f"X{v}"
            ok = True

        v = self.probeYdir.get()
        if v != "":
            cmd += f"Y{v}"
            ok = True

        v = self.probeZdir.get()
        if v != "":
            cmd += f"Z{v}"
            ok = True

        v = ProbeCommonFrame.probeFeed.get()
        if v != "":
            cmd += f"F{v}"

        if ok:
            self.sendGCode(cmd)
        else:
            messagebox.showerror(
                _("Probe Error"),
                _("At least one probe direction should be specified")
            )

    # -----------------------------------------------------------------------
    # Rapid move to the last probed location
    # -----------------------------------------------------------------------
    def goto2Probe(self, event=None):
        try:
            cmd = "G53 G0 X{:g} Y{:g} Z{:g}\n".format(
                CNC.vars["prbx"],
                CNC.vars["prby"],
                CNC.vars["prbz"],
            )
        except Exception:
            return
        self.sendGCode(cmd)

    # -----------------------------------------------------------------------
    # Probe Center
    # -----------------------------------------------------------------------
    def probeCenter(self, event=None):
        self.warnMessage()

        cmd = f"G91 {CNC.vars['prbcmd']} F{CNC.vars['prbfeed']}"
        try:
            diameter = abs(float(self.diameter.get()))
        except Exception:
            diameter = 0.0

        if diameter < 0.001:
            messagebox.showerror(
                _("Probe Center Error"),
                _("Invalid diameter entered"),
                parent=self.winfo_toplevel(),
            )
            return

        lines = []
        lines.append(f"{cmd} x-{diameter}")
        lines.append("%wait")
        lines.append("tmp=prbx")
        lines.append(f"g53 g0 x[prbx+{diameter / 10.0:g}]")
        lines.append("%wait")
        lines.append(f"{cmd} x{diameter}")
        lines.append("%wait")
        lines.append("g53 g0 x[0.5*(tmp+prbx)]")
        lines.append("%wait")
        lines.append(f"{cmd} y-{diameter}")
        lines.append("%wait")
        lines.append("tmp=prby")
        lines.append(f"g53 g0 y[prby+{diameter / 10.0:g}]")
        lines.append("%wait")
        lines.append(f"{cmd} y{diameter}")
        lines.append("%wait")
        lines.append("g53 g0 y[0.5*(tmp+prby)]")
        lines.append("%wait")
        lines.append("g90")
        self.app.run(lines=lines)

    # -----------------------------------------------------------------------
    # Solve the system and update fields
    # -----------------------------------------------------------------------
    def orientSolve(self, event=None):
        try:
            phi, xo, yo = self.app.gcode.orient.solve()
            self.angle_orient["text"] = "%*f" % (CNC.digits, math.degrees(phi))
            self.xo_orient["text"] = "%*f" % (CNC.digits, xo)
            self.yo_orient["text"] = "%*f" % (CNC.digits, yo)

            minerr, meanerr, maxerr = self.app.gcode.orient.error()
            self.err_orient["text"] = "Avg:%*f  Max:%*f  Min:%*f" % (
                CNC.digits,
                meanerr,
                CNC.digits,
                maxerr,
                CNC.digits,
                minerr,
            )

        except Exception:
            self.angle_orient["text"] = sys.exc_info()[1]
            self.xo_orient["text"] = ""
            self.yo_orient["text"] = ""
            self.err_orient["text"] = ""

    # -----------------------------------------------------------------------
    # Delete current orientation point
    # -----------------------------------------------------------------------
    def orientDelete(self, event=None):
        marker = self.scale_orient.get() - 1
        if marker < 0 or marker >= len(self.app.gcode.orient):
            return
        self.app.gcode.orient.clear(marker)
        self.orientUpdateScale()
        self.changeMarker(marker + 1)
        self.orientSolve()
        self.event_generate("<<DrawOrient>>")

    # -----------------------------------------------------------------------
    # Clear all markers
    # -----------------------------------------------------------------------
    def orientClear(self, event=None):
        if self.scale_orient.cget("to") == 0:
            return
        ans = messagebox.askquestion(
            _("Delete all markers"),
            _("Do you want to delete all orientation markers?"),
            parent=self.winfo_toplevel(),
        )
        if ans != messagebox.YES:
            return
        self.app.gcode.orient.clear()
        self.orientUpdateScale()
        self.event_generate("<<DrawOrient>>")

    # -----------------------------------------------------------------------
    # Update orientation scale
    # -----------------------------------------------------------------------
    def orientUpdateScale(self):
        n = len(self.app.gcode.orient)
        if n:
            self.scale_orient.config(state=NORMAL, from_=1, to_=n)
        else:
            self.scale_orient.config(state=DISABLED, from_=0, to_=0)

    # -----------------------------------------------------------------------
    def orientClearFields(self):
        self.x_orient.delete(0, END)
        self.y_orient.delete(0, END)
        self.xm_orient.delete(0, END)
        self.ym_orient.delete(0, END)
        self.angle_orient["text"] = ""
        self.xo_orient["text"] = ""
        self.yo_orient["text"] = ""
        self.err_orient["text"] = ""

    # -----------------------------------------------------------------------
    # Update orient with the current marker
    # -----------------------------------------------------------------------
    def orientUpdate(self, event=None):
        marker = self.scale_orient.get() - 1
        if marker < 0 or marker >= len(self.app.gcode.orient):
            self.orientClearFields()
            return
        xm, ym, x, y = self.app.gcode.orient[marker]
        try:
            x = float(self.x_orient.get())
        except Exception:
            pass
        try:
            y = float(self.y_orient.get())
        except Exception:
            pass
        try:
            xm = float(self.xm_orient.get())
        except Exception:
            pass
        try:
            ym = float(self.ym_orient.get())
        except Exception:
            pass
        self.app.gcode.orient.markers[marker] = xm, ym, x, y

        self.orientUpdateScale()
        self.changeMarker(marker + 1)
        self.orientSolve()
        self.event_generate("<<DrawOrient>>")

    # -----------------------------------------------------------------------
    # The index will be +1 to appear more human starting from 1
    # -----------------------------------------------------------------------
    def changeMarker(self, marker):
        marker = int(marker) - 1
        if marker < 0 or marker >= len(self.app.gcode.orient):
            self.orientClearFields()
            self.event_generate("<<OrientChange>>", data=-1)
            return

        xm, ym, x, y = self.app.gcode.orient[marker]
        d = CNC.digits
        self.x_orient.set("%*f" % (d, x))
        self.y_orient.set("%*f" % (d, y))
        self.xm_orient.set("%*f" % (d, xm))
        self.ym_orient.set("%*f" % (d, ym))
        self.orientSolve()
        self.event_generate("<<OrientChange>>", data=marker)

    # -----------------------------------------------------------------------
    # Select marker
    # -----------------------------------------------------------------------
    def selectMarker(self, marker):
        self.orientUpdateScale()
        self.scale_orient.set(marker + 1)

    def recordAppend(self, line):
        hasblock = None
        for bid, block in enumerate(self.app.gcode):
            if block._name == "recording":
                hasblock = bid
                eblock = block

        if hasblock is None:
            hasblock = -1
            eblock = Block("recording")
            self.app.gcode.insBlocks(hasblock, [eblock], "Recorded point")

        eblock.append(line)
        self.app.refresh()
        self.app.setStatus(_("Pointrec"))

    def recordCoords(self, gcode="G0", point=False):
        x = CNC.vars["wx"]
        y = CNC.vars["wy"]
        z = CNC.vars["wz"]

        coords = f"X{x} Y{y}"
        if self.recz.get() == 1:
            coords += f" Z{z}"

        if point:
            self.recordAppend(f"G0 Z{CNC.vars['safe']}")
        self.recordAppend(f"{gcode} {coords}")
        if point:
            self.recordAppend("G1 Z0")

    def recordRapid(self):
        self.recordCoords()

    def recordFeed(self):
        self.recordCoords("G1")

    def recordPoint(self):
        self.recordCoords("G0", True)

    def recordCircle(self):
        r = float(self.recsiz.get())
        x = CNC.vars["wx"] - r
        y = CNC.vars["wy"]
        z = CNC.vars["wz"]

        coords = f"X{x} Y{y}"
        if self.recz.get() == 1:
            coords += f" Z{z}"

        self.recordAppend(f"G0 {coords}")
        self.recordAppend(f"G02 {coords} I{r}")

    def recordFinishAll(self):
        for bid, block in enumerate(self.app.gcode):
            if block._name == "recording":
                self.app.gcode.setBlockNameUndo(bid, "recorded")
        self.app.refresh()
        self.app.setStatus(_("Finished recording"))



# =============================================================================
# Probe Common Offset
# =============================================================================
class GenGcodeFrame(CNCRibbon.PageFrame):
    probeFeed = None
    tlo = None
    probeCmd = None

    def __init__(self, master, app):
        CNCRibbon.PageFrame.__init__(self, master, "GenGcode", app)

        lframe = tkExtra.ExLabelFrame(
            self, text=_("GCode"), foreground="DarkBlue")
        lframe.pack(side=TOP, fill=X)
        frame = lframe.frame

        # ----
        row = 0
        col = 0

        # ----
        # Fast Probe Feed
        Label(frame,
              text=_("Engrave Text:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.engraveText = StringVar()
        GenGcodeFrame.engraveText = Entry(
            frame,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            width=5,
            textvariable=self.engraveText,
        )
        GenGcodeFrame.engraveText.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            GenGcodeFrame.engraveText,
            _("Set initial probe feed rate for tool change and calibration"),
        )
        self.addWidget(GenGcodeFrame.engraveText)
        
        
        # ----
        # Size (Height, Width)
        row += 1
        col = 0
        Label(lframe(), text=_("Size (H, W):")).grid(row=row, column=col, sticky=E)
        col += 1
        self.height = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.height.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            self.height, _("Engrave Text Height"))

        col += 1
        self.width = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.width.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            self.width, _("Engrave Text Width"))
        
        # ----
        # Pos (X, Y)
        row, col = row + 1, 0
        Label(lframe(), text=_("Pos:")).grid(row=row, column=col, sticky=E)

        col += 1
        self.posX = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.posX.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.posX, _("Position X"))
        self.addWidget(self.posX)

        col += 1
        self.posY = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.posY.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.posY, _("Position Y"))
        self.addWidget(self.posY)
        
        # ----
        # Engrave Depth
        row += 1
        col = 0
        Label(frame, text=_("Depth:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.engraveDepth = tkExtra.FloatEntry(
            frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.engraveDepth.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            self.engraveDepth, _("Engrave Depth"))
        self.addWidget(self.engraveDepth)
        
        # ----
        # Layer Height
        row += 1
        col = 0
        Label(frame, text=_("Layer Height:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.layerHeight = tkExtra.FloatEntry(
            frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.layerHeight.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            self.layerHeight, _("Layer Height"))
        self.addWidget(self.layerHeight)
        
        
        # ----
        # Safe Height
        row += 1
        col = 0
        Label(frame, text=_("Safe Height:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.safeHeight = tkExtra.FloatEntry(
            frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.safeHeight.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            self.safeHeight, _("Safe Height"))
        self.addWidget(self.safeHeight)
        
        col += 1
        generate_b = Button(frame, text=_("Generate"), command=self.generateGcode, padx=2, pady=1)
        generate_b.grid(row=row, column=col, sticky=EW)
        self.addWidget(generate_b)



        frame.grid_columnconfigure(1, weight=1)
        self.loadConfig()
        
    def generateGcode(self):
        print("Generate Gcode")
        engrave_text = self.engraveText.get()
        text_height_mm, text_width_mm = 25, 50
        text_position_mm = (30, 20, -5)
        layer_height_mm = 10
        safe_height_mm = 5
        save_dir = os.path.dirname(__file__)

        gcode_file_path = setup_blender_scene(engrave_text, text_width_mm, text_height_mm, text_position_mm, layer_height_mm, safe_height_mm, save_dir)
        
        
        print("Generated Gcode file path:", gcode_file_path)
        self.app.load(gcode_file_path)
        print("Loaded Gcode file:", self.app.gcode.filename)




    # # -----------------------------------------------------------------------
    # def saveConfig(self):
    #     Utils.setFloat("Probe",
    #                    "fastfeed", GenGcodeFrame.fastProbeFeed.get())
    #     Utils.setFloat("Probe", "feed", GenGcodeFrame.probeFeed.get())
    #     Utils.setFloat("Probe", "tlo", GenGcodeFrame.tlo.get())
    #     Utils.setFloat("Probe", "cmd",
    #                    GenGcodeFrame.probeCmd.get().split()[0])

    # # -----------------------------------------------------------------------
    # def loadConfig(self):
    #     GenGcodeFrame.engraveText.set(Utils.getFloat("Probe", "engraveText"))
    #     GenGcodeFrame.probeFeed.set(Utils.getFloat("Probe", "feed"))
    #     GenGcodeFrame.tlo.set(Utils.getFloat("Probe", "tlo"))
    #     cmd = Utils.getStr("Probe", "cmd")
    #     for p in PROBE_CMD:
    #         if p.split()[0] == cmd:
    #             GenGcodeFrame.probeCmd.set(p)
    #             break


class MultiPointProbe(CNCRibbon.PageFrame):
    def __init__(self, master, app):
        """Initialize the MultiPointProbe class for polynomial surface probing."""
        CNCRibbon.PageFrame.__init__(self, master, "MultiPointProbe", app)
        
        
        self.probe_points = [(10, 20), (30, 40), (50, 60)]  # Dummy list of (X, Y) coordinates
        
        # UI Elements
        lframe = tkExtra.ExLabelFrame(self, text=_("Multi-Point Surface Probe"), foreground="DarkBlue")
        lframe.pack(side=TOP, fill=X)
        frame = lframe.frame
        
        
        
        # --- Input Fields ---
        row, col = 0, 0
        self.x_entry = StringVar()
        Entry(frame, textvariable=self.x_entry, width=10).grid(row=row, column=col, sticky=W)

        col += 1
        self.y_entry = StringVar()
        Entry(frame, textvariable=self.y_entry, width=10).grid(row=row, column=col, sticky=W)


        # --- Button to Show Probe Points ---
        col += 1
        show_button = Button(frame, text=_("Show Probe Points"), command=self.show_probe_points)
        show_button.grid(row=row, column=col, sticky=W)
        self.addWidget(show_button)


        frame.grid_columnconfigure(1, weight=1)
    
    def show_probe_points(self):
        """Display a popup window with the probe points."""
        popup = tkExtra.ExLabelFrame(self, text=_("Probe Points"), foreground="DarkBlue")
        popup.pack(side=TOP, fill=X)

        # Create a label for each probe point
        for point in self.probe_points:
            Label(popup.frame, text=f"Point: {point}").pack(anchor=W)

        # Add a close button
        close_button = Button(popup.frame, text=_("Close"), command=popup.destroy)
        close_button.pack(side=BOTTOM)


# =============================================================================
# Probe Page
# =============================================================================
class SurfAlignPage(CNCRibbon.Page):
    __doc__ = _("SurfAlign configuration and probing")
    _name_ = "SurfAlign"
    _icon_ = "measure"

    # -----------------------------------------------------------------------
    # Add a widget in the widgets list to enable disable during the run
    # -----------------------------------------------------------------------
    def register(self):
        self._register(
            (ProbeTabGroup,),
            (ProbeCommonFrame, ProbeFrame, GenGcodeFrame, MultiPointProbe),
        )

        self.tabGroup = CNCRibbon.Page.groups["Probe"]
        self.tabGroup.tab.set("Probe")
        self.tabGroup.tab.trace("w", self.tabChange)

    # -----------------------------------------------------------------------
    def tabChange(self, a=None, b=None, c=None):
        tab = self.tabGroup.tab.get()
        self.master._forgetPage()

        # Remove all page tabs with ":" and add the new ones
        self.ribbons = [x for x in self.ribbons if ":" not in x[0].name]
        self.frames = [x for x in self.frames if ":" not in x[0].name]

        try:
            self.addRibbonGroup(f"Probe:{tab}")
        except KeyError:
            pass
        try:
            self.addPageFrame(f"Probe:{tab}")
        except KeyError:
            pass

        self.master.changePage(self)

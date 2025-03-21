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
    Radiobutton,
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
        tkExtra.Balloon.set(self.posX, _("Engrave Text Center Position X"))
        self.addWidget(self.posX)

        col += 1
        self.posY = tkExtra.FloatEntry(
            lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.posY.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.posY, _("Engrave Text Center Position Y"))
        self.addWidget(self.posY)
        
        # ----  
        # Rotation
        row += 1
        col = 0
        Label(frame, text=_("Rotation:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.rotation = tkExtra.FloatEntry(
            frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.rotation.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            self.rotation, _("Engrave Text Rotation along Z axis (degrees)"))
        self.addWidget(self.rotation)
        
        # ----  
        # Feedrate
        row += 1
        col = 0
        Label(frame, text=_("Feedrate:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.feedrate = tkExtra.FloatEntry(
            frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.feedrate.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            self.feedrate, _("Feedrate (mm/min)"))
        self.addWidget(self.feedrate)
        
        # ----
        # Spindle RPM
        row += 1
        col = 0
        Label(frame, text=_("Spindle RPM:")).grid(row=row, column=col, sticky=E)    
        col += 1
        self.spindleRPM = tkExtra.FloatEntry(
            frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.spindleRPM.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            self.spindleRPM, _("Spindle RPM"))  
        self.addWidget(self.spindleRPM)

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
            self.engraveDepth, _("Engrave Depth (mm)"))
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
        
    def loadConfig(self):
        self.engraveText.set(Utils.getStr("SurfAlign", "engraveText"))
        self.height.set(Utils.getFloat("SurfAlign", "height"))
        self.width.set(Utils.getFloat("SurfAlign", "width"))
        self.posX.set(Utils.getFloat("SurfAlign", "posX"))
        self.posY.set(Utils.getFloat("SurfAlign", "posY"))
        self.rotation.set(Utils.getFloat("SurfAlign", "rotation"))
        self.feedrate.set(Utils.getFloat("SurfAlign", "feedrate"))
        self.spindleRPM.set(Utils.getFloat("SurfAlign", "spindleRPM"))
        self.engraveDepth.set(Utils.getFloat("SurfAlign", "engraveDepth"))
        self.layerHeight.set(Utils.getFloat("SurfAlign", "layerHeight"))
        self.safeHeight.set(Utils.getFloat("SurfAlign", "safeHeight"))
        
    def generateGcode(self):
        print("Generate Gcode")
        engrave_text = self.engraveText.get()
        text_height_mm, text_width_mm = float(self.height.get()), float(self.width.get())
        text_position_mm = (float(self.posX.get()), float(self.posY.get()), -float(self.engraveDepth.get()))
        layer_height_mm = float(self.layerHeight.get())
        safe_height_mm = float(self.safeHeight.get())
        save_dir = os.path.dirname(__file__)
        rotation_degrees = float(self.rotation.get())
        feedrate_mm = float(self.feedrate.get())
        spindle_rpm = float(self.spindleRPM.get())
        gcode_file_path = setup_blender_scene(engrave_text, text_width_mm, text_height_mm, text_position_mm,rotation_degrees, layer_height_mm, safe_height_mm, save_dir, feedrate_mm, spindle_rpm)
        
        
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
        
        
        self.probe_points = []  # Dummy list of (X, Y) coordinates
        
        # UI Elements
        lframe = tkExtra.ExLabelFrame(self, text=_("Multi-Point Surface Probe"), foreground="DarkBlue")
        lframe.pack(side=TOP, fill=X)
        frame = lframe.frame
        
        
        
        # --- Input Fields ---
        row, col = 0, 0
        Label(frame, text=_("No. of Points:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.n_probe_points = tkExtra.FloatEntry(
            frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.n_probe_points.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            self.n_probe_points, _("Number of probe points"))
        
        row += 1
        col = 0
        Label(frame, text=_("Z Min, Max:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.mp_z_min = tkExtra.FloatEntry(
            frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.mp_z_min.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            self.mp_z_min, _("Z minimum depth to scan"))
        
        col += 1
        self.mp_z_max = tkExtra.FloatEntry(
            frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.mp_z_max.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            self.mp_z_max, _("Z safe to move"))
        
        # feed command
        row += 1
        col = 0
        Label(frame,
              text=_("Probe Coverage Method")).grid(row=row, column=col, sticky=E)
        col += 1
        self.probe_coverage_methods = ["EvenCoverage", "AreaCoverage"]
        self.probe_coverage_method = tkExtra.Combobox(
            frame,
            True,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            width=16,
        )
        self.probe_coverage_method.grid(row=row, column=col, sticky=EW)
        self.probe_coverage_method.fill(self.probe_coverage_methods)
        self.probe_coverage_method.set("EvenCoverage")
        self.addWidget(self.probe_coverage_method)

        row += 1
        col = 0
        probe_generate_b = Button(frame, text=_("Generate Probe"), command=self.generate_probe)
        probe_generate_b.grid(row=row, column=col, sticky=W)
        self.addWidget(probe_generate_b)

        col = 1
        # --- Button to Show Probe Points ---
        show_button = Button(frame, text=_("Show Probe Points"), command=self.show_probe_points)
        show_button.grid(row=row, column=col, sticky=W)
        self.addWidget(show_button)

        col += 1
        probe_generate_b = Button(frame, text=_("Start Probing"), command=self.start_probing)
        probe_generate_b.grid(row=row, column=col, sticky=W)
        self.addWidget(probe_generate_b)

        frame.grid_columnconfigure(1, weight=1)
        self.loadConfig()
        
    def loadConfig(self):
        self.mp_z_min.set(Utils.getFloat("SurfAlign", "mp_z_min"))
        self.mp_z_max.set(Utils.getFloat("SurfAlign", "mp_z_max"))
        self.n_probe_points.set(Utils.getFloat("SurfAlign", "n_probe_points"))
        
    
    def generate_probe(self):
        
        no_of_points = int(float(self.n_probe_points.get()))
        if no_of_points < 3:
            messagebox.showwarning(_("Probe error"), _("Number of probe points must be greater than 2"))
            return

        self.probe_points = self.app.gcode.generate_and_plot_probing_points(method=self.probe_coverage_method.get(), k=no_of_points)
        
    def show_probe_points(self):
        """Display a popup window with the probe points."""
        if len(self.probe_points) == 0:
            messagebox.showwarning(_("Probe error"), _("No probe points found"))
            return
        popup = tkExtra.ExLabelFrame(self, text=_("Probe Points"), foreground="DarkBlue")
        popup.pack(side=TOP, fill=X)

        # Create a label for each probe point
        for point in self.probe_points:
            Label(popup.frame, text=f"Point: {point}").pack(anchor=W)

        # Add a close button
        close_button = Button(popup.frame, text=_("Close"), command=popup.destroy)
        close_button.pack(side=BOTTOM)

    def start_probing(self):
        if len(self.probe_points) == 0:
            messagebox.showwarning(_("Probe error"), _("No probe points found"))
            return
        print("Start Probing")
        lines = self.app.gcode.probe.multi_point_scan(self.probe_points)
        # self.app.run(lines)
        print("PROBE COMMAND:")
        print("\n".join(lines))


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
            (ProbeCommonFrame, GenGcodeFrame, MultiPointProbe),
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

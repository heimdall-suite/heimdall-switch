# Places the main heimdall-switch PCB from the schematic netlist (first
# layout iteration): loads every footprint, assigns pad nets, links it to
# its symbol, places it from the table below, draws the board outline.
# Usage (KiCad's python): python place_pcb.py NETLIST.xml OUT.kicad_pcb PRETTY_DIR
# Rebuilds the board from scratch: only for placement iterations before
# routing starts, never once the board has been edited in the GUI.
import sys, os, xml.etree.ElementTree as ET
import pcbnew

NETLIST, OUT, LOCAL = sys.argv[1], sys.argv[2], sys.argv[3]
STOCK = r"C:\Users\svefre\AppData\Local\Programs\KiCad\10.0\share\kicad\footprints"

# ref: (x, y, rotation, side)   board origin (100,100), 23mm tall
P = {
    # ===== TOP
    "J3": (117.0, 102.8, 270, "F"),   # BATT_IN pads (relief holes at the left edge)
    "J2": (117.0, 115.2, 270, "F"),   # LOAD_OUT pads
    "Q4": (124.2, 103.4, 180, "F"),
    "Q3": (124.2, 116.0, 180, "F"),
    "U1": (147.0, 108.0, 0, "F"),     # BT832 mid-board, antenna over the edge notch
    "Y1": (136.5, 108.5, 90, "F"),    # beside U1 pins 3/4
    "SW1": (143.5, 120.0, 0, "F"),    # strip under the module body
    "LED1": (149.0, 120.0, 0, "F"),
    "J4": (159.5, 109.5, 270, "F"),   # JST-XH to the daughter board
    # ===== BOTTOM, left section
    "D1": (131.0, 102.0, 0, "B"),     # Q4 gate
    "R1": (135.2, 102.0, 0, "B"),
    "R2": (122.2, 109.0, 90, "B"),    # regulator: R_IN, C_IN, U2, L1, C_OUT
    "C3": (125.3, 108.6, 180, "B"),
    "U2": (125.5, 106.0, 0, "B"),
    "L1": (129.5, 106.0, 180, "B"),
    "C4": (133.5, 106.0, 180, "B"),
    "R3": (122.0, 106.0, 270, "B"),
    "R11": (120.6, 112.2, 90, "B"),   # ADC divider top, at LOAD_OUT
    "C7": (124.0, 112.6, 0, "B"),     # Q3 gate network
    "D2": (129.6, 112.2, 0, "B"),
    "R8": (120.6, 116.0, 90, "B"),
    "Q2": (124.5, 116.0, 0, "B"),
    "R7": (134.0, 112.2, 0, "B"),
    "Q1": (130.0, 116.0, 0, "B"),
    "R5": (134.5, 116.0, 0, "B"),
    "R6": (130.4, 120.0, 0, "B"),
    "R9": (123.2, 120.0, 0, "B"),
    "R10": (126.6, 120.0, 0, "B"),
    "C1": (137.5, 107.25, 90, "B"),   # crystal load caps, behind Y1
    "C2": (137.5, 110.6, 90, "B"),
    # ===== BOTTOM, under the module body
    "J1": (147.0, 112.5, 0, "B"),     # ARM 10-pin debug header
    "R12": (140.8, 111.0, 90, "B"),   # ADC divider bottom + filter, at pin 5
    "C8": (140.8, 114.5, 90, "B"),
    "C6": (152.4, 114.3, 90, "B"),    # VDD decoupling at pin 9
    "C5": (152.4, 117.8, 90, "B"),
    "R4": (147.0, 118.0, 0, "B"),     # nRESET pull-up
    # ===== BOTTOM, right section
    "Q6": (133.0, 102.0, 0, "F"),     # LED driver
    "R13": (133.0, 104.8, 0, "F"),
    "R14": (133.0, 107.6, 0, "F"),
    "Q5": (133.0, 111.5, 0, "F"),
    "R15": (133.0, 114.3, 180, "F"),
    "R16": (157.0, 121.5, 180, "B"),    # button ESD resistor
}
# antenna notch in the top edge (no board, no copper under the antenna)
NOTCH = (139.5, 154.5, 106.3)
BOARD_X0, BOARD_Y0, BOARD_H = 100.0, 100.0, 23.0
# right edge = module body/antenna boundary (antenna overhangs)
BOARD_X1 = 163.5

def lib_dir(nick):
    return LOCAL if nick == "heimdall-switch" else os.path.join(STOCK, nick + ".pretty")

root = ET.parse(NETLIST).getroot()
board = pcbnew.NewBoard(OUT)
nets = {}
for n in root.iter("net"):
    name = n.get("name")
    name = name[0] + name[1:].replace("/", "{slash}") if name.startswith("/") else name.replace("/", "{slash}")
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    nets[name] = ni
padnet = {}
for n in root.iter("net"):
    for nd in n.iter("node"):
        nm = n.get("name"); nm = nm[0] + nm[1:].replace("/", "{slash}") if nm.startswith("/") else nm.replace("/", "{slash}")
        padnet[(nd.get("ref"), nd.get("pin"))] = nets[nm]

missing = []
for c in root.iter("comp"):
    ref = c.get("ref")
    nick, name = c.findtext("footprint").split(":")
    fp = pcbnew.FootprintLoad(lib_dir(nick), name)
    fp.SetFPIDAsString(f"{nick}:{name}")
    fp.SetReference(ref)
    fp.SetValue(c.findtext("value"))
    fp.SetPath(pcbnew.KIID_PATH("/" + c.findtext("tstamps")))
    fp.SetSheetname("/")
    fp.SetSheetfile("heimdall-switch.kicad_sch")
    for f in c.iter("field"):
        if f.get("name") in ("LCSC", "Function"):
            fp.SetField(f.get("name"), f.text or "")
            fld = fp.GetField(f.get("name"))
            fld.SetVisible(False)
            fld.SetLayer(pcbnew.F_Fab)
    fp.SetExcludedFromBOM(False)
    for pad in fp.Pads():
        k = (ref, pad.GetNumber())
        if k in padnet:
            pad.SetNet(padnet[k])
    board.Add(fp)
    if ref not in P:
        missing.append(ref)
        continue
    x, y, rot, side = P[ref]
    fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    fp.SetOrientationDegrees(rot)
    if side == "B":
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)

# board outline with the antenna notch
x0, y0, x1, y1 = BOARD_X0, BOARD_Y0, BOARD_X1, BOARD_Y0 + BOARD_H
nx0, nx1, ny = NOTCH
pts = [(x0, y0), (nx0, y0), (nx0, ny), (nx1, ny), (nx1, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
for (ax, ay), (bx, by) in zip(pts, pts[1:]):
    l = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    l.SetStart(pcbnew.VECTOR2I_MM(ax, ay)); l.SetEnd(pcbnew.VECTOR2I_MM(bx, by))
    l.SetLayer(pcbnew.Edge_Cuts); l.SetWidth(pcbnew.FromMM(0.05))
    board.Add(l)

pcbnew.SaveBoard(OUT, board)
print("placed; unplaced:", missing, "board %.1f x %.1f mm" % (BOARD_X1 - BOARD_X0, BOARD_H))

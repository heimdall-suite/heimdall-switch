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
    # --- wire entry (left end): relief holes at the edge, pads inboard
    "J3": (117.0, 102.8, 270, "F"),   # BATT_IN: pad1 BATT+ (117,102.8), pad2 GND (117,107.6)
    "J2": (117.0, 115.2, 270, "F"),   # LOAD_OUT: pad1 LOAD (117,115.2), pad2 GND (117,120.0)
    # --- power FETs, drains facing the wire pads, sources on the VBAT bar
    "Q4": (124.2, 103.4, 180, "F"),
    "Q3": (124.2, 116.0, 180, "F"),
    "R11": (121.8, 110.0, 90, "F"),   # ADC divider top, right at LOAD_OUT
    # --- Q4 gate (reverse polarity)
    "D1": (133.0, 104.0, 90, "F"),
    "R1": (135.7, 102.35, 0, "F"),
    # --- regulator
    "R2": (138.9, 103.75, 0, "F"),
    "C3": (142.5, 101.5, 0, "F"),
    "U2": (144.0, 104.0, 180, "F"),
    "R3": (142.2, 107.0, 270, "F"),
    "L1": (147.4, 103.25, 0, "F"),
    "C4": (150.6, 104.0, 270, "F"),
    # --- Q3 gate network (fail-on switching stage)
    "C7": (132.6, 111.6, 0, "F"),
    "D2": (135.0, 109.3, 0, "F"),
    "R9": (135.0, 116.4, 270, "F"),
    "R10": (137.0, 116.4, 270, "F"),
    "R8": (140.0, 114.1, 180, "F"),
    "Q2": (143.6, 114.1, 180, "F"),
    "R7": (146.4, 111.4, 0, "F"),
    "Q1": (147.6, 117.0, 0, "F"),
    "R5": (150.5, 115.5, 90, "F"),
    "R6": (150.5, 119.0, 90, "F"),
    # --- LED driver (high side)
    "R13": (154.6, 101.6, 0, "F"),
    "Q6": (158.3, 103.2, 0, "F"),
    "R14": (162.8, 103.2, 0, "F"),
    "Q5": (154.8, 106.0, 0, "F"),
    "R15": (154.8, 108.6, 0, "F"),
    "LED1": (159.6, 107.2, 0, "F"),
    # --- UI breakout + on-board button
    "J4": (155.2, 118.9, 0, "F"),
    "R16": (158.0, 113.5, 0, "F"),
    "SW1": (168.0, 116.6, 0, "F"),
    # --- debug header, MCU support
    "J1": (177.0, 115.8, 0, "F"),
    "R4": (177.0, 110.6, 0, "F"),
    "R12": (171.0, 106.8, 270, "F"),
    "C8": (173.0, 106.8, 270, "F"),
    "C5": (182.4, 119.2, 90, "F"),
    "C6": (184.2, 119.2, 90, "F"),
    # --- BT832, antenna overhanging the right end; crystal in the strip
    "U1": (194.0, 111.5, 270, "F"),
    "Y1": (193.0, 101.9, 0, "F"),
    "C1": (194.25, 101.9, 90, "B"),
    "C2": (191.75, 101.9, 90, "B"),
}
BOARD_X0, BOARD_Y0, BOARD_H = 100.0, 100.0, 23.0
# right edge = module body/antenna boundary (antenna overhangs)
BOARD_X1 = P["U1"][0] + 1.8

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

# board outline
r = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
r.SetStart(pcbnew.VECTOR2I_MM(BOARD_X0, BOARD_Y0))
r.SetEnd(pcbnew.VECTOR2I_MM(BOARD_X1, BOARD_Y0 + BOARD_H))
r.SetLayer(pcbnew.Edge_Cuts)
r.SetWidth(pcbnew.FromMM(0.05))
board.Add(r)

pcbnew.SaveBoard(OUT, board)
print("placed; unplaced:", missing, "board %.1f x %.1f mm" % (BOARD_X1 - BOARD_X0, BOARD_H))

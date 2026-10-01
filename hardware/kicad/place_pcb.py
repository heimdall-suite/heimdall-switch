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
    # ===== TOP: wires, power FETs, everything you see/touch/plug in
    "J3": (117.0, 102.8, 270, "F"),   # BATT_IN pads (relief holes at the left edge)
    "J2": (117.0, 115.2, 270, "F"),   # LOAD_OUT pads
    "Q4": (124.2, 103.4, 180, "F"),
    "Q3": (124.2, 116.0, 180, "F"),
    "J4": (135.5, 111.0, 270, "F"),   # JST-XH to the daughter board
    "LED1": (151.8, 120.2, 0, "F"),
    "SW1": (146.4, 119.6, 0, "F"),   # PTS810, next to LED1
    "J1": (157.0, 111.5, 0, "F"),     # ARM 10-pin debug
    "U1": (170.0, 111.5, 270, "F"),   # antenna overhangs the right end
    "Y1": (169.0, 101.9, 0, "F"),
    # ===== BOTTOM: small parts
    # Q4 gate (reverse polarity), under Q4
    "D1": (127.5, 102.2, 0, "B"),
    "R1": (127.5, 105.0, 0, "B"),
    # regulator
    "R2": (133.0, 101.5, 0, "B"),
    "C3": (133.5, 104.5, 0, "B"),
    "U2": (138.0, 103.5, 0, "B"),
    "R3": (138.0, 106.3, 0, "B"),
    "L1": (141.8, 103.0, 0, "B"),
    "C4": (145.0, 103.5, 90, "B"),
    # LED driver
    "R13": (148.5, 101.5, 0, "B"),
    "Q6": (152.0, 102.5, 0, "B"),
    "R14": (156.8, 102.5, 0, "B"),
    "Q5": (148.0, 105.4, 0, "B"),
    "R15": (152.0, 106.0, 0, "B"),
    # Q3 gate network (fail-on switching stage), under Q3 / beside J4
    "R11": (121.8, 110.0, 90, "B"),   # ADC divider top, at LOAD_OUT
    "C7": (127.0, 109.5, 0, "B"),
    "D2": (127.5, 112.0, 0, "B"),
    "R9": (127.0, 115.0, 0, "B"),
    "R10": (127.0, 117.0, 0, "B"),
    "R8": (131.5, 114.0, 90, "B"),
    "Q2": (140.0, 110.5, 0, "B"),
    "R7": (143.5, 110.5, 0, "B"),
    "Q1": (140.0, 114.5, 0, "B"),
    "R5": (143.5, 114.5, 0, "B"),
    "R6": (143.5, 116.5, 0, "B"),
    "R16": (139.5, 118.5, 0, "B"),    # button ESD resistor
    # MCU support
    "R4": (157.0, 117.5, 0, "B"),     # nRESET pull-up, under J1
    "C5": (163.8, 116.0, 90, "B"),    # VDD decoupling, under U1 pin 9
    "C6": (165.6, 116.0, 90, "B"),
    "R12": (166.4, 107.2, 90, "B"),   # ADC divider bottom + filter, under U1 pin 5
    "C8": (164.6, 107.2, 90, "B"),
    "C1": (170.25, 101.9, 90, "B"),   # crystal load caps, under Y1
    "C2": (167.75, 101.9, 90, "B"),
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

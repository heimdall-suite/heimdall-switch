# Builds the JLCPCB order package for the main board into gerber/:
#   heimdall-switch.zip            Gerbers (board plot settings) + Excellon drill (PTH/NPTH)
#   heimdall-switch-BOM[-bottom].csv   Comment, Designator, Footprint, LCSC
#   heimdall-switch-CPL[-bottom].csv   Designator, Mid X, Mid Y, Layer, Rotation
# The -bottom files are for one-sided ("Economic") assembly of the bottom side.
#
# Run with KiCad's bundled python from hardware/kicad/:
#   python jlc_export.py
#
# Rotation: JLCPCB's part models don't always share KiCad's zero angle.
# ROT_OFFSET adds degrees per footprint name (found by checking JLC's
# placement preview); check the preview again after every upload.
import csv, os, subprocess, sys, zipfile
import pcbnew

KICAD_CLI = r"C:\Users\svefre\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe"
BOARD, SCH, OUT = "heimdall-switch.kicad_pcb", "heimdall-switch.kicad_sch", "gerber"
ROT_OFFSET = {
    "D_SOD-123": 180,      # JLC's model has the cathode band on pad 2 (checked in their preview)
    "SOT-583-8": 90,       # U2: JLC preview needed it turned 90 deg counter-clockwise
}
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"

def cli(*args):
    subprocess.run([KICAD_CLI, *args], check=True, stdout=subprocess.DEVNULL)

os.makedirs(OUT, exist_ok=True)
cli("pcb", "export", "gerbers", "--board-plot-params", "-l", LAYERS, "-o", OUT + "/", BOARD)
cli("pcb", "export", "drill", "--format", "excellon", "--drill-origin", "absolute",
    "--excellon-units", "mm", "--excellon-separate-th", "-o", OUT + "/", BOARD)
name = os.path.splitext(BOARD)[0]
parts = [name + s for s in ("-F_Cu.gtl", "-B_Cu.gbl", "-F_Mask.gts", "-B_Mask.gbs", "-F_Silkscreen.gto",
                            "-B_Silkscreen.gbo", "-F_Paste.gtp", "-B_Paste.gbp", "-Edge_Cuts.gm1",
                            "-PTH.drl", "-NPTH.drl", "-job.gbrjob")]
with zipfile.ZipFile(os.path.join(OUT, name + ".zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for p in parts:
        z.write(os.path.join(OUT, p), p)

# BOM straight from the schematic (fields Value/Reference/Footprint/LCSC)
tmp = os.path.join(OUT, "_bom.csv")
cli("sch", "export", "bom", "--fields", "Value,Reference,Footprint,LCSC",
    "--labels", "Comment,Designator,Footprint,LCSC", "--group-by", "Value,Footprint,LCSC",
    "--exclude-dnp", "-o", tmp, SCH)
bom = list(csv.reader(open(tmp, encoding="utf8"))); os.remove(tmp)

# CPL from the board, with the rotation offsets applied
b = pcbnew.LoadBoard(BOARD)
cpl, side = [], {}
for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    if f.IsExcludedFromPosFiles() or f.IsDNP(): continue
    fp = f.GetFPID().GetLibItemName().wx_str()
    rot = (f.GetOrientationDegrees() + ROT_OFFSET.get(fp, 0)) % 360
    p = f.GetPosition()
    layer = "Bottom" if f.IsFlipped() else "Top"
    side[f.GetReference()] = layer
    cpl.append([f.GetReference(), "%.4fmm" % pcbnew.ToMM(p.x), "%.4fmm" % -pcbnew.ToMM(p.y), layer, "%.1f" % rot])

def write(fn, rows):
    with open(os.path.join(OUT, fn), "w", newline="", encoding="utf8") as fh:
        csv.writer(fh).writerows(rows)
write(name + "-BOM.csv", bom)
write(name + "-CPL.csv", [["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]] + cpl)
bot = {r for r, s in side.items() if s == "Bottom"}
bom_bot = [bom[0]] + [[r[0], ",".join(d for d in r[1].split(",") if d.strip() in bot), r[2], r[3]]
                      for r in bom[1:] if any(d.strip() in bot for d in r[1].split(","))]
write(name + "-BOM-bottom.csv", bom_bot)
write(name + "-CPL-bottom.csv", [["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]] + [c for c in cpl if c[3] == "Bottom"])
print("JLC package in %s/: zip, BOM (%d lines, %d bottom), CPL (%d parts, %d bottom)"
      % (OUT, len(bom) - 1, len(bom_bot) - 1, len(cpl), len(bot)))

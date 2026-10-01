# Places reference designators on silk so they're readable: 0.8mm text,
# tried at positions around each footprint, first one that clears pads,
# holes, other labels and the board edge (same side) wins. Values go to Fab.
# Usage: python silk.py IN.kicad_pcb OUT.kicad_pcb
import sys, pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
MM = pcbnew.FromMM
SIZE, TH, GAP, PADM = 0.8, 0.12, 0.25, 0.2   # text, stroke, gap to part, clearance to copper

def rect(bb, m=0.0):
    return (pcbnew.ToMM(bb.GetLeft()) - m, pcbnew.ToMM(bb.GetTop()) - m,
            pcbnew.ToMM(bb.GetRight()) + m, pcbnew.ToMM(bb.GetBottom()) + m)

def hit(a, c):
    return not (a[2] <= c[0] or c[2] <= a[0] or a[3] <= c[1] or c[3] <= a[1])

# board area (outer rect minus the antenna notch, read from Edge.Cuts)
edge = b.GetBoardEdgesBoundingBox()
X0, Y0, X1, Y1 = rect(edge)
notch = []
segs = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_SEGMENT]
xs = sorted({round(pcbnew.ToMM(p), 3) for s in segs for p in (s.GetStart().x, s.GetEnd().x)})
ys = sorted({round(pcbnew.ToMM(p), 3) for s in segs for p in (s.GetStart().y, s.GetEnd().y)})
inner_x = [x for x in xs if X0 < x < X1]
inner_y = [y for y in ys if Y0 < y < Y1 and any(abs(pcbnew.ToMM(s.GetStart().y) - y) < 1e-3 and abs(pcbnew.ToMM(s.GetEnd().y) - y) < 1e-3 for s in segs)]
if len(inner_x) == 2 and inner_y:
    notch.append((inner_x[0], Y0 - 1, inner_x[1], min(inner_y)))

def obstacles(side):
    obs = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            onside = p.IsOnLayer(pcbnew.F_Cu if side == "F" else pcbnew.B_Cu) or p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            if onside:
                obs.append(rect(p.GetBoundingBox(), PADM))
    for n in notch:
        obs.append(n)
    sl = pcbnew.F_SilkS if side == "F" else pcbnew.B_SilkS
    for fp in b.GetFootprints():
        for g in fp.GraphicalItems():
            if g.GetLayer() == sl and g.Type() != pcbnew.PCB_FIELD_T and g.Type() != pcbnew.PCB_TEXT_T:
                obs.append(rect(g.GetBoundingBox(), 0.15))
    return obs

placed = {"F": [], "B": []}
fails = []
fps = sorted(b.GetFootprints(), key=lambda f: -len(f.Pads()))
for fp in fps:
    side = "B" if fp.IsFlipped() else "F"
    silk = pcbnew.B_SilkS if side == "B" else pcbnew.F_SilkS
    fab = pcbnew.B_Fab if side == "B" else pcbnew.F_Fab
    v = fp.Value(); v.SetLayer(fab)
    t = fp.Reference()
    t.SetLayer(silk); t.SetVisible(True)
    t.SetTextSize(pcbnew.VECTOR2I(MM(SIZE), MM(SIZE))); t.SetTextThickness(MM(TH))
    t.SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
    t.SetKeepUpright(True)
    cy = fp.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd).BBox()
    if cy.GetWidth() == 0:
        cy = fp.GetBoundingBox(False)
    l, tp, r, bt = rect(cy)
    cx, cyy = (l + r) / 2, (tp + bt) / 2
    w = len(t.GetText()) * SIZE * 0.75 + 0.2
    h = SIZE + 0.2
    others = []
    for o in b.GetFootprints():
        if o is fp: continue
        if (o.IsFlipped() == fp.IsFlipped()) or any(pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for pd in o.Pads()):
            oc = o.GetCourtyard(pcbnew.B_CrtYd if o.IsFlipped() else pcbnew.F_CrtYd).BBox()
            if oc.GetWidth() > 0: others.append(rect(oc))
    def gap(a, c):
        dx = max(c[0] - a[2], a[0] - c[2], 0); dy = max(c[1] - a[3], a[1] - c[3], 0)
        return (dx * dx + dy * dy) ** 0.5
    cands = []
    for ang, ww, hh in ((0, w, h), (90, h, w)):
        cands += [(ang, ww, hh, cx, tp - GAP - hh / 2), (ang, ww, hh, cx, bt + GAP + hh / 2),
                  (ang, ww, hh, l - GAP - ww / 2, cyy), (ang, ww, hh, r + GAP + ww / 2, cyy),
                  (ang, ww, hh, l - GAP - ww / 2, tp + hh / 2), (ang, ww, hh, r + GAP + ww / 2, tp + hh / 2),
                  (ang, ww, hh, l - GAP - ww / 2, bt - hh / 2), (ang, ww, hh, r + GAP + ww / 2, bt - hh / 2)]
    obs = obstacles(side)
    best = None
    for (ang, ww, hh, x, y) in cands:
        box = (x - ww / 2, y - hh / 2, x + ww / 2, y + hh / 2)
        if box[0] < X0 + 0.3 or box[2] > X1 - 0.3 or box[1] < Y0 + 0.3 or box[3] > Y1 - 0.3:
            continue
        if any(hit(box, o) for o in obs) or any(hit(box, o) for o in placed[side]):
            continue
        own = gap(box, (l, tp, r, bt))
        near = min([gap(box, o) for o in others] + [3.0])
        score = own - min(near, 1.5) + (0.3 if ang else 0)   # prefer horizontal text
        if best is None or score < best[0]:
            best = (score, ang, x, y, box)
    if best is None:
        fails.append(fp.GetReference())
        continue
    _, ang, x, y, box = best
    t.SetTextAngle(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
    t.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    placed[side].append(box)

pcbnew.SaveBoard(sys.argv[2], b)
print("no room for:", fails)

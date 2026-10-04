# DC current flow in the main board's power copper, from the real board geometry.
#
# Each section of the load path is rasterised at 0.1mm (zone fills, tracks and pads of
# its net, per copper layer) and the steady current flow is solved on that sheet
# (Laplace, finite differences, conjugate gradient). Entry/exit pads are equipotential
# electrodes; layers are coupled through via barrels and plated pad holes.
# Output per section: resistance, drop and loss at 5A/10A, and the peak current per mm
# of copper width (IPC-2221, 1oz outer, ~20C rise: ~2A/mm for 5-10A).
#
# Run with KiCad's bundled python (needs numpy + Pillow, both bundled):
#   python copper.py [../kicad/heimdall-switch.kicad_pcb]
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw
import pcbnew

G = 0.1                                   # grid, mm
CU = 35e-6                                # 1oz copper, m
RHO = 1.72e-8                             # copper, ohm*m (20C)
RS = RHO / CU                             # sheet resistance, ohm/square (~0.49 mOhm)
VIA_PLATING = 25e-6                       # barrel plating, m
BOARD_T = 1.6e-3
mm = pcbnew.ToMM

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "kicad", "heimdall-switch.kicad_pcb")
b = pcbnew.LoadBoard(path)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
bb = b.GetBoardEdgesBoundingBox()
X0, Y0 = mm(bb.GetLeft()), mm(bb.GetTop())
NX, NY = int(mm(bb.GetWidth()) / G) + 2, int(mm(bb.GetHeight()) / G) + 2
LAYERS = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
fp = {f.GetReference(): f for f in b.GetFootprints()}

def px(x, y): return ((mm(x) - X0) / G, (mm(y) - Y0) / G)

def draw_polyset(dr, ps):
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        pts = [px(o.CPoint(k).x, o.CPoint(k).y) for k in range(o.PointCount())]
        if len(pts) > 2: dr.polygon(pts, fill=1)
        for h in range(ps.HoleCount(i)):
            hl = ps.Hole(i, h)
            hp = [px(hl.CPoint(k).x, hl.CPoint(k).y) for k in range(hl.PointCount())]
            if len(hp) > 2: dr.polygon(hp, fill=0)

def pad_poly(p, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    p.TransformShapeToPolygon(ps, layer, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
    return ps

def mask_of(polysets):
    im = Image.new("1", (NX, NY), 0); dr = ImageDraw.Draw(im)
    for ps in polysets: draw_polyset(dr, ps)
    return np.array(im, dtype=bool)

def copper(net, L):
    """Raster of all copper of `net` on layer L (zone fills, tracks, pads)."""
    im = Image.new("1", (NX, NY), 0); dr = ImageDraw.Draw(im)
    for z in b.Zones():
        if not z.GetIsRuleArea() and z.GetNetname() == net and z.IsOnLayer(L):
            draw_polyset(dr, z.GetFilledPolysList(L))
    for t in b.GetTracks():
        if t.GetNetname() != net: continue
        if t.Type() == pcbnew.PCB_VIA_T:
            x, y = px(t.GetPosition().x, t.GetPosition().y); r = mm(t.GetWidth(L)) / 2 / G
            dr.ellipse([x - r, y - r, x + r, y + r], fill=1)
        elif t.GetLayer() == L:
            w = max(1, int(round(mm(t.GetWidth()) / G)))
            a, c = px(t.GetStart().x, t.GetStart().y), px(t.GetEnd().x, t.GetEnd().y)
            dr.line([a, c], fill=1, width=w)
            for q in (a, c): dr.ellipse([q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2], fill=1)
    for p in b.GetPads():
        if p.GetNetname() == net and p.IsOnLayer(L): draw_polyset(dr, pad_poly(p, L))
    return np.array(im, dtype=bool)

def pads(refpins, L):
    ps = [pad_poly(p, L) for ref, pins in refpins for p in fp[ref].Pads() if p.GetNumber() in pins and p.IsOnLayer(L)]
    return mask_of(ps)

def solve(net, layers, src, dst, vias=True):
    """Resistance between electrode pad sets src and dst (lists of (ref, pins)), in ohms,
    plus the per-layer potential maps (for 1A total) and copper masks."""
    Ls = [LAYERS[l] for l in layers]
    cu = [copper(net, L) for L in Ls]
    es = [pads(src, L) & c for L, c in zip(Ls, cu)]
    ed = [pads(dst, L) & c for L, c in zip(Ls, cu)]
    n = len(Ls); shape = (n, NY, NX)
    C = np.stack(cu); S = np.stack(es); D = np.stack(ed)
    fixed = S | D
    V0 = np.where(S, 1.0, 0.0)
    # in-plane links (conductance 1 per square, sheet units)
    gx = C[:, :, 1:] & C[:, :, :-1]
    gy = C[:, 1:, :] & C[:, :-1, :]
    # layer links: vias and plated holes of this net (conductance in sheet units)
    links = []
    if n == 2 and vias:
        for t in b.GetTracks():
            if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == net:
                d = mm(t.GetDrill()) * 1e-3
                links.append((t.GetPosition(), mm(t.GetWidth(pcbnew.F_Cu)) / 2, RS / (RHO * BOARD_T / (math.pi * d * VIA_PLATING))))
        for p in b.GetPads():
            if p.GetNetname() == net and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and p.GetDrillSize().x > 0:
                d = mm(p.GetDrillSize().x) * 1e-3
                links.append((p.GetPosition(), mm(p.GetDrillSize().x) / 2 + 0.1, RS / (RHO * BOARD_T / (math.pi * d * VIA_PLATING))))
    # spread each barrel's conductance over the cells of its ring
    Z = np.zeros((NY, NX))
    for pos, r, g in links:
        cx, cy = px(pos.x, pos.y); R = int(math.ceil(r / G))
        cells = [(j, i) for j in range(int(cy) - R, int(cy) + R + 2) for i in range(int(cx) - R, int(cx) + R + 2)
                 if 0 <= j < NY and 0 <= i < NX and (i - cx) ** 2 + (j - cy) ** 2 <= (r / G) ** 2 and C[0, j, i] and C[1, j, i]]
        for j, i in cells: Z[j, i] += g / max(1, len(cells))

    def apply(V):                          # A*V for the conductance Laplacian
        out = np.zeros(shape)
        dx = (V[:, :, 1:] - V[:, :, :-1]) * gx
        out[:, :, 1:] += dx; out[:, :, :-1] -= dx
        dy = (V[:, 1:, :] - V[:, :-1, :]) * gy
        out[:, 1:, :] += dy; out[:, :-1, :] -= dy
        if n == 2:
            dz = (V[1] - V[0]) * Z
            out[0] += dz; out[1] -= dz
        return out                          # graph Laplacian: positive semidefinite
    free = C & ~fixed
    rhs = -apply(V0); rhs[~free] = 0
    x = np.zeros(shape); r = rhs.copy(); p = r.copy(); rr = (r * r).sum()
    for it in range(20000):
        Ap = apply(p); Ap[~free] = 0
        a = rr / (p * Ap).sum(); x += a * p; r -= a * Ap
        rn = (r * r).sum()
        if math.sqrt(rn) < 1e-9 * math.sqrt((rhs * rhs).sum()) + 1e-14: break
        p = r + (rn / rr) * p; rr = rn
    V = V0 + x
    # current leaving the source electrode (sheet units -> amps for 1V: / RS)
    I = (apply(V) * S).sum()
    Rohm = RS / I
    return Rohm, V, C, I, gx, gy, it

def report(name, net, layers, src, dst):
    R, V, C, I, gx, gy, it = solve(net, layers, src, dst)
    # current per mm of width at 1 A: |grad V| (V per cell, V scaled so total current = 1A)
    scale = 1.0 / (I / RS)                    # volts per (unit V) at 1A total
    jmax, where = 0, None
    for l in range(V.shape[0]):
        jx = np.abs(np.diff(V[l], axis=1)) * gx[l]; jy = np.abs(np.diff(V[l], axis=0)) * gy[l]
        # A per mm of width = (dV/cell * scale) / RS / G
        for J, ax in ((jx, 1), (jy, 0)):
            k = np.unravel_index(np.argmax(J), J.shape)
            val = J[k] * scale / RS / G
            if val > jmax: jmax, where = val, (layers[l], X0 + k[1] * G, Y0 + k[0] * G)
    # also the 99th percentile, so pad-corner crowding doesn't dominate
    allj = []
    for l in range(V.shape[0]):
        allj.append((np.abs(np.diff(V[l], axis=1)) * gx[l]).ravel()); allj.append((np.abs(np.diff(V[l], axis=0)) * gy[l]).ravel())
    allj = np.concatenate(allj); allj = allj[allj > 0] * scale / RS / G
    p99 = float(np.percentile(allj, 99))
    print("%-34s R = %5.2f mOhm | 5A: %5.1f mV %5.0f mW | 10A: %5.1f mV %5.0f mW | A/mm per A: max %.2f at %s(%.1f,%.1f), 99%% %.2f  [%d it]" % (
        name, R * 1e3, 5 * R * 1e3, 25 * R * 1e3, 10 * R * 1e3, 100 * R * 1e3, jmax, where[0], where[1], where[2], p99, it))
    return R, jmax, p99

if __name__ == "__main__":
    print("sheet resistance %.3f mOhm/sq (1oz, 20C), grid %.1fmm" % (RS * 1e3, G))
    rows = [
        ("BATT+  J3+ -> Q4 drain",           "/BATT+",    "B",  [("J3", {"1"})],              [("Q4", {"5", "6", "7", "8"})]),
        ("VBAT   Q4 source -> Q3 source",    "VBAT",      "B",  [("Q4", {"1", "2", "3"})],    [("Q3", {"1", "2", "3"})]),
        ("LOAD   Q3 drain -> J2+",           "/LOAD_OUT", "B",  [("Q3", {"5", "6", "7", "8"})], [("J2", {"1"})]),
        ("GND    J2- -> J3- (both layers)",  "GND",       "FB", [("J2", {"2"})],              [("J3", {"2"})]),
    ]
    tot = 0
    for name, net, layers, src, dst in rows:
        R, jmax, p99 = report(name, net, layers, src, dst); tot += R
    print("copper total %.2f mOhm -> %.0f mV / %.2f W at 5A, %.0f mV / %.2f W at 10A (plus Q3+Q4 R_DS(on))" % (
        tot * 1e3, 5 * tot * 1e3, 25 * tot, 10 * tot * 1e3, 100 * tot))

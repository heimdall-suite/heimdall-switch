# Routing pipeline for the main board (KiCad python + Freerouting).
# Steps used for the committed layout (see .docs/hardware.md, PCB layout):
#   prep IN OUT DSN --keep-gnd   power zones, keep-outs, hand-placed VBAT/gate pre-routes, DSN
#   (java -jar freerouting.jar -de DSN -do SES -mp 100 --gui.enabled=false)
#   finish IN SES OUT            import SES, GND pours both layers
#   gridstitch IN OUT 4.0        GND stitching vias
#   islandstitch IN OUT          via for every GND pour fragment
#   cleanup IN OUT               drop fragment/dangling vias, solid GND on J2/J3
# Only for re-running the flow from a fresh placement: it rebuilds all copper.
import sys, re, pcbnew

MM = pcbnew.FromMM
def V(x, y): return pcbnew.VECTOR2I_MM(x, y)

def zone(b, net, layer, pts, prio, clear=0.25, full=True, name=""):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNetCode(b.GetNetsByName()[net].GetNetCode())
    o = z.Outline(); o.NewOutline()
    for x, y in pts: o.Append(MM(x), MM(y))
    z.SetAssignedPriority(prio)
    z.SetLocalClearance(MM(clear))
    z.SetMinThickness(MM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if full else pcbnew.ZONE_CONNECTION_THT_THERMAL)
    z.SetThermalReliefGap(MM(0.3)); z.SetThermalReliefSpokeWidth(MM(0.4))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    if name: z.SetZoneName(name)
    b.Add(z)
    return z

def track(b, net, layer, x0, y0, x1, y1, w):
    t = pcbnew.PCB_TRACK(b); t.SetStart(V(x0, y0)); t.SetEnd(V(x1, y1))
    t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNetCode(b.GetNetsByName()[net].GetNetCode()); t.SetLocked(True); b.Add(t)

def via(b, net, x, y, d=0.8, drill=0.4):
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(MM(d)); v.SetDrill(MM(drill))
    v.SetNetCode(b.GetNetsByName()[net].GetNetCode()); v.SetLocked(True); b.Add(v)

def rect(x0, y0, x1, y1): return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

if sys.argv[1] == "prep":
    b = pcbnew.LoadBoard(sys.argv[2])
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    # 3A path on top: BATT+ (J3 -> Q4 drain), LOAD (Q3 drain -> J2), VBAT bar (Q4/Q3 sources)
    zone(b, "/BATT+", F, rect(115.4, 100.4, 123.0, 105.9), 10, name="BATT+")
    zone(b, "/LOAD_OUT", F, rect(115.4, 113.4, 123.0, 118.3), 10, name="LOAD_OUT")
    zone(b, "VBAT", F, [(125.6, 102.2), (130.6, 102.2), (130.6, 102.5), (132.75, 102.5), (132.75, 105.4), (130.6, 105.4), (130.6, 118.4), (125.6, 118.4)], 10, name="VBAT bar")
    # no copper on top under the BT832 body (its unused LGA pads sit there)
    ko = pcbnew.ZONE(b); ko.SetIsRuleArea(True); ko.SetLayer(F)
    o = ko.Outline(); o.NewOutline()
    for x, y in rect(141.1, 106.4, 152.9, 116.1): o.Append(MM(x), MM(y))
    ko.SetDoNotAllowTracks(True); ko.SetDoNotAllowVias(True); ko.SetDoNotAllowZoneFills(True)
    ko.SetDoNotAllowPads(False); ko.SetDoNotAllowFootprints(False); ko.SetZoneName("BT832 underside keep-out")
    b.Add(ko)
    # keep other nets' tracks from cutting the power copper in two (vias still allowed)
    for nm, (ax, ay, bx, by) in (("BATT+ area", (115.4, 100.4, 123.0, 105.9)), ("LOAD area", (115.4, 113.4, 123.0, 118.3)),
                                 ("VBAT bar upper", (125.6, 102.2, 130.6, 113.6)), ("VBAT bar lower", (125.6, 114.6, 130.6, 118.4))):
        k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetLayer(F)
        o = k.Outline(); o.NewOutline()
        for x, y in rect(ax, ay, bx, by): o.Append(MM(x), MM(y))
        k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(False); k.SetDoNotAllowZoneFills(False)
        k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False); k.SetZoneName(nm + " (no crossing tracks)")
        b.Add(k)
    # gate stubs: straight to a via, so nothing crosses the VBAT bar on top
    track(b, "Net-(D1-A)", F, 126.675, 101.495, 128.8, 101.3, 0.3); via(b, "Net-(D1-A)", 128.8, 101.3, 0.6, 0.3)
    track(b, "/Q3_GATE", F, 126.675, 114.095, 128.8, 114.095, 0.3); via(b, "/Q3_GATE", 128.8, 114.095, 0.6, 0.3)
    # VBAT down from the bar to the Q3 gate network / R_IN on the bottom (hand-placed: the
    # bottom under the bar is too crowded for the autorouter to find via spots)
    via(b, "VBAT", 129.6, 110.4); via(b, "VBAT", 126.2, 110.6); via(b, "VBAT", 131.6, 103.9)
    track(b, "VBAT", B, 131.6, 103.9, 132.65, 102.6, 0.3); track(b, "VBAT", B, 132.65, 102.6, 132.65, 102.0, 0.3)   # -> D1 K
    for (x0, y0, x1, y1) in ((129.6, 110.4, 131.25, 110.4), (131.25, 110.4, 131.25, 112.2),     # -> D2 K
                             (131.25, 110.4, 134.82, 110.4), (134.82, 110.4, 134.82, 112.2),    # -> R7
                             (126.2, 110.6, 124.95, 111.85), (124.95, 111.85, 124.95, 112.6),   # -> C7
                             (126.2, 110.6, 122.2, 110.6), (122.2, 110.6, 122.2, 109.83),       # -> R2 (R_IN)
                             (124.95, 112.6, 126.6, 113.3), (126.6, 113.3, 126.6, 116.95), (126.6, 116.95, 125.44, 116.95)):  # -> Q2 S
        track(b, "VBAT", B, x0, y0, x1, y1, 0.3)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(sys.argv[3], b)
    pcbnew.ExportSpecctraDSN(b, sys.argv[4])
    # leave GND to the pours: drop it from the autorouter's netlist
    d = open(sys.argv[4], encoding="utf-8").read()
    gsub = [a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--gnd-pins=")]
    if gsub:   # route GND only between these pins; the pours handle the rest
        d2 = re.sub(r'\(net GND\s*\(pins[^)]*\)\s*\)', '(net GND (pins ' + ' '.join(gsub[0]) + '))', d, count=1)
    else:
        d2 = d if "--keep-gnd" in sys.argv else re.sub(r'\(net GND\s*\(pins[^)]*\)\s*\)', '', d, count=1)
    print("GND removed from DSN:", d2 != d)
    open(sys.argv[4], "w", encoding="utf-8").write(d2)

elif sys.argv[1] == "finish":
    b = pcbnew.LoadBoard(sys.argv[2])
    ok = pcbnew.ImportSpecctraSES(b, sys.argv[3])
    print("SES imported:", ok)
    edge = b.GetBoardEdgesBoundingBox()
    x0, y0 = pcbnew.ToMM(edge.GetLeft()), pcbnew.ToMM(edge.GetTop())
    x1, y1 = pcbnew.ToMM(edge.GetRight()), pcbnew.ToMM(edge.GetBottom())
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone(b, "GND", layer, rect(x0, y0, x1, y1), 1, clear=0.3, full=False, name="GND")
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(sys.argv[4], b)

elif sys.argv[1] == "stitch":
    # stitch IN.kicad_pcb OUT.kicad_pcb REF:PAD ...  -> GND via beside each listed pad
    import math
    b = pcbnew.LoadBoard(sys.argv[2])
    gnd = b.GetNetsByName()["GND"].GetNetCode()
    VR, CL = 0.3, 0.25
    edge = b.GetBoardEdgesBoundingBox()
    X0, Y0, X1, Y1 = [pcbnew.ToMM(v) for v in (edge.GetLeft(), edge.GetTop(), edge.GetRight(), edge.GetBottom())]
    obst = []   # (kind, geometry, layers) for other-net copper
    for fp in b.GetFootprints():
        for pd in fp.Pads():
            if pd.GetNetCode() == gnd: continue
            bb = pd.GetBoundingBox()
            obst.append(("box", [pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]))
    for t in b.GetTracks():
        if t.GetNetCode() == gnd: continue
        if t.Type() == pcbnew.PCB_VIA_T:
            c = t.GetPosition(); r = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2
            obst.append(("circ", (pcbnew.ToMM(c.x), pcbnew.ToMM(c.y), r)))
        else:
            obst.append(("seg", (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y), pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y), pcbnew.ToMM(t.GetWidth()) / 2)))
    nogo = [z for z in b.Zones() if (z.GetIsRuleArea() and z.GetDoNotAllowVias()) or (not z.GetIsRuleArea() and z.GetNetCode() != gnd)]
    def segdist(px, py, ax, ay, bx, by):
        dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
        return math.hypot(px - ax - t * dx, py - ay - t * dy)
    def clear(x, y, r):
        if x - r < X0 + 0.5 or x + r > X1 - 0.5 or y - r < Y0 + 0.5 or y + r > Y1 - 0.5: return False
        if not b.GetBoardEdgesBoundingBox().Contains(pcbnew.VECTOR2I_MM(x, y)): return False
        for z in nogo:
            for dx, dy in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r)):
                if z.Outline().Contains(pcbnew.VECTOR2I_MM(x + dx, y + dy)): return False
        for k, g in obst:
            if k == "box":
                dx = max(g[0] - x, x - g[2], 0); dy = max(g[1] - y, y - g[3], 0)
                if math.hypot(dx, dy) < r + CL: return False
            elif k == "circ":
                if math.hypot(x - g[0], y - g[1]) < r + g[2] + CL: return False
            else:
                if segdist(x, y, *g[:4]) < r + g[4] + CL: return False
        return True
    def pathclear(ax, ay, bx, by, w):
        for i in range(1, 11):
            t = i / 10
            if not clear(ax + (bx - ax) * t, ay + (by - ay) * t, w / 2): return False
        return True
    added = 0
    for spec in sys.argv[4:]:
        ref, num = spec.split(":")
        fp = b.FindFootprintByReference(ref)
        pd = [p for p in fp.Pads() if p.GetNumber() == num][0]
        cx, cy = pcbnew.ToMM(pd.GetPosition().x), pcbnew.ToMM(pd.GetPosition().y)
        layer = pcbnew.B_Cu if pd.IsOnLayer(pcbnew.B_Cu) and not pd.IsOnLayer(pcbnew.F_Cu) else pcbnew.F_Cu
        done = False
        for rr in (1.0, 1.3, 1.6, 2.0, 2.5):
            for k in range(24):
                a = 2 * math.pi * k / 24
                x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
                if clear(x, y, VR) and pathclear(cx, cy, x, y, 0.3):
                    via(b, "GND", round(x, 3), round(y, 3), 0.6, 0.3)
                    track(b, "GND", layer, cx, cy, round(x, 3), round(y, 3), 0.3)
                    obst  # (GND items don't block other GND vias)
                    added += 1; done = True; break
            if done: break
        if not done: print("no spot for", spec)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(sys.argv[3], b)
    print("stitch vias added:", added)

elif sys.argv[1] == "gridstitch":
    # gridstitch IN OUT PITCH -> GND via wherever both GND pours have solid copper around it
    b = pcbnew.LoadBoard(sys.argv[2]); pitch = float(sys.argv[4])
    gz = [z for z in b.Zones() if z.GetNetname() == "GND" and not z.GetIsRuleArea()]
    def solid(z, x, y, r):
        L = z.GetLayer()
        pts = [(x, y)] + [(x + r * c, y + r * s) for c, s in ((1, 0), (-1, 0), (0, 1), (0, -1), (.7, .7), (-.7, .7), (.7, -.7), (-.7, -.7))]
        return all(z.HitTestFilledArea(L, pcbnew.VECTOR2I_MM(px, py)) for px, py in pts)
    edge = b.GetBoardEdgesBoundingBox()
    x0, y0, x1, y1 = [pcbnew.ToMM(v) for v in (edge.GetLeft(), edge.GetTop(), edge.GetRight(), edge.GetBottom())]
    n = 0; x = x0 + 1.5
    while x < x1 - 1:
        y = y0 + 1.5
        while y < y1 - 1:
            if all(solid(z, x, y, 0.3 + 0.35) for z in gz):
                via(b, "GND", round(x, 2), round(y, 2), 0.6, 0.3); n += 1
            y += pitch
        x += pitch
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(sys.argv[3], b)
    print("grid stitch vias:", n)

elif sys.argv[1] == "islandstitch":
    # islandstitch IN OUT -> every GND pour island gets a via to the other side's pour
    b = pcbnew.LoadBoard(sys.argv[2])
    gz = {z.GetLayer(): z for z in b.Zones() if z.GetNetname() == "GND" and not z.GetIsRuleArea()}
    gvias = [t.GetPosition() for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == "GND"]
    added = 0
    for L, z in gz.items():
        other = gz[pcbnew.B_Cu if L == pcbnew.F_Cu else pcbnew.F_Cu]
        OL = other.GetLayer()
        polys = z.GetFilledPolysList(L)
        for i in range(polys.OutlineCount()):
            ol = polys.Outline(i)
            if any(ol.PointInside(v) for v in gvias): continue
            allv = [t.GetPosition() for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
            bb = ol.BBox()
            x0, y0, x1, y1 = [pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]
            r = 0.3 + 0.2
            ring = [(1, 0), (-1, 0), (0, 1), (0, -1), (.7, .7), (-.7, .7), (.7, -.7), (-.7, -.7)]
            kos = [k for k in b.Zones() if k.GetIsRuleArea() and k.GetDoNotAllowVias()]
            spot = None
            y = y0
            while y <= y1 and not spot:
                x = x0
                while x <= x1:
                    pts = [(x, y)] + [(x + r * c, y + r * s) for c, s in ring]
                    if any(k.Outline().Contains(pcbnew.VECTOR2I_MM(x, y)) for k in kos) or                        any(abs(pcbnew.ToMM(v.x) - x) < 1.0 and abs(pcbnew.ToMM(v.y) - y) < 1.0 for v in allv):
                        x += 0.2; continue
                    if all(z.HitTestFilledArea(L, pcbnew.VECTOR2I_MM(px, py)) and other.HitTestFilledArea(OL, pcbnew.VECTOR2I_MM(px, py)) for px, py in pts):
                        spot = (round(x, 2), round(y, 2)); break
                    x += 0.2
                y += 0.2
            if spot:
                via(b, "GND", spot[0], spot[1], 0.6, 0.3); gvias.append(pcbnew.VECTOR2I_MM(*spot)); added += 1
            else:
                print("island without a spot on", b.GetLayerName(L), "bbox %.1f,%.1f-%.1f,%.1f" % (x0, y0, x1, y1))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(sys.argv[3], b)
    print("island vias:", added)

elif sys.argv[1] == "cleanup":
    # cleanup IN OUT: drop GND vias in pad-less pour fragments, drop vias with copper on
    # only one layer, solid zone connection for the wire-pad GND (3A return)
    b = pcbnew.LoadBoard(sys.argv[2])
    for ref in ("J2", "J3"):
        for pd in b.FindFootprintByReference(ref).Pads():
            if pd.GetNetname() == "GND": pd.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    gz = {z.GetLayer(): z for z in b.Zones() if z.GetNetname() == "GND" and not z.GetIsRuleArea()}
    pads = [p.GetPosition() for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == "GND"]
    # the main fragment on each layer = the one with the most GND pads
    removed = 0
    for L, z in gz.items():
        polys = z.GetFilledPolysList(L)
        counts = [sum(1 for p in pads if polys.Outline(i).PointInside(p)) for i in range(polys.OutlineCount())]
        for i in range(polys.OutlineCount()):
            if counts[i] > 0: continue
            ol = polys.Outline(i)
            for t in list(b.GetTracks()):
                if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == "GND" and ol.PointInside(t.GetPosition()) and not t.IsLocked():
                    b.Remove(t); removed += 1
    # vias touched by tracks on only one layer and not sitting in a same-net zone
    dang = 0
    for v in [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() != "GND"]:
        layers = set()
        for t in b.GetTracks():
            if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetCode() == v.GetNetCode() and (t.GetStart() == v.GetPosition() or t.GetEnd() == v.GetPosition()):
                layers.add(t.GetLayer())
        inzone = any(z.GetNetCode() == v.GetNetCode() and not z.GetIsRuleArea() and z.HitTestFilledArea(z.GetLayer(), v.GetPosition()) for z in b.Zones())
        if len(layers) < 2 and not inzone and not v.IsLocked():
            b.Remove(v); dang += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(sys.argv[3], b)
    print("removed fragment vias:", removed, "dangling vias:", dang)

elif sys.argv[1] == "jumper":
    # jumper IN OUT NET LAYER W x0,y0 x1,y1 ... : polyline track, refused if it hits other-net copper
    import math
    b = pcbnew.LoadBoard(sys.argv[2]); net, layer, w = sys.argv[4], b.GetLayerID(sys.argv[5]), float(sys.argv[6])
    pts = [tuple(map(float, a.split(","))) for a in sys.argv[7:]]
    nc = b.GetNetsByName()[net].GetNetCode()
    tr = pcbnew.PCB_TRACK(b); tr.SetWidth(MM(w)); tr.SetLayer(layer); tr.SetNetCode(nc)
    bad = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        tr.SetStart(V(ax, ay)); tr.SetEnd(V(bx, by))
        shp = tr.GetEffectiveShape(layer)
        for fp in b.GetFootprints():
            for pd in fp.Pads():
                if pd.GetNetCode() != nc and pd.IsOnLayer(layer) and pd.GetEffectiveShape(layer).Collide(shp, MM(0.2)):
                    bad.append(fp.GetReference() + ":" + pd.GetNumber())
        for t in b.GetTracks():
            if t.GetNetCode() != nc and t.IsOnLayer(layer) and t.GetEffectiveShape(layer).Collide(shp, MM(0.2)):
                bad.append("track " + t.GetNetname())
    if bad:
        print("jumper refused, hits:", sorted(set(bad)))
    else:
        for (ax, ay), (bx, by) in zip(pts, pts[1:]): track(b, net, layer, ax, ay, bx, by, w)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        print("jumper added")
    pcbnew.SaveBoard(sys.argv[3], b)

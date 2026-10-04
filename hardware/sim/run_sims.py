# Runs every power-side check on both model sets (datasheet fits, AOS vendor AO4407A)
# and prints the tables quoted in .docs/hardware.md "Simulation".
# Run with KiCad's bundled python (it ships ngspice.dll):  python run_sims.py
import spice, circuit as c

def series(d, *keys): return [d[k] for k in keys]
def q3_turn_on(d):
    t, vb, ld, i = series(d, "time", "vbat", "load", "vq3#branch")
    p = [abs((a - b) * x) for a, b, x in zip(vb, ld, i)]
    half_on = sum(t[k + 1] - t[k] for k in range(len(t) - 1) if abs(i[k]) > 0.2 and vb[k] - ld[k] > 0.5)
    t0 = next(t[k] for k in range(len(t)) if ld[k] > 0.2)
    return t0, max(p), half_on

def run(n, vendor): return spice.run(c.vendor(n) if vendor else n)[0]

for vendor in (False, True):
    print("\n==== models: %s ====" % ("AOS AO4407A (vendor)" if vendor else "datasheet fits"))
    print("-- plug-in, full 3S pack (Q3 must stay off, VBAT/U2 VIN peaks)")
    for lw in ("0.3u", "1u", "2u"):
        d = run(c.netlist(lw=lw), vendor)
        vgs3 = [a - b for a, b in zip(d["q3g"], d["vbat"])]
        print("  leads %-4s VBAT peak %5.2f V  U2 VIN peak %5.2f V  Q3 Vgs min %+5.2f V" % (lw, max(d["vbat"]), max(d["en"]), min(vgs3)))

    print("-- slow turn-on of Q3 into a load (1000uF + R), C7 = 220nF")
    for vb, rl in ((12.6, "2.5"), (8.4, "1.7"), (6.6, "1.3"), (12.6, "1.26")):
        d = run(c.netlist(vbatt=vb, rl=rl, cl="1000u", tran=".tran 10u 0.5 0 10u"), vendor)
        t0, pk, half = q3_turn_on(d)
        print("  %4.1f V %4.1f A  conducts at %5.1f ms  Q3 peak %5.1f W  half-on %4.1f ms" % (vb, vb / float(rl), t0 * 1e3, pk, half * 1e3))

    if not vendor:
        print("-- firmware window vs Q3 threshold spread (C7 220n / 100n), 5A load")
        for c7 in ("220n", "100n"):
            for vto in (-1.7, -3.0):
                m = c.FITTED.replace("(Vto=-2.3 Kp=14", "(Vto=%g Kp=14" % vto)
                for vb, rl in ((12.6, "2.5"), (8.4, "1.7")):
                    d = run(c.netlist(c7=c7, vbatt=vb, rl=rl, cl="1000u", tran=".tran 10u 0.4 0 10u", models=m), False)
                    t0, pk, half = q3_turn_on(d)
                    print("  C7 %-4s Vth %4.1f V  %4.1f V  conducts at %5.1f ms" % (c7, vto, vb, t0 * 1e3))

    print("-- OFF asserted at full current (battery lead kick, no bulk cap on VBAT)")
    for rl, lw in (("2.5", "1u"), ("2.5", "2u"), ("1.26", "2u")):
        d = run(c.netlist(plug=False, rl=rl, lw=lw, lload="0.5u", cl="1000u",
                          off="VOFF off 0 PWL(0 0 20u 0 20.1u 3.3)", tran=".tran 2n 150u"), vendor)
        t, vb, ld, i3, en = series(d, "time", "vbat", "load", "vq3#branch", "en")
        k = next(k for k in range(len(t)) if t[k] > 20e-6)
        toff = next((t[j] for j in range(k, len(t)) if abs(i3[j]) < 0.1 * abs(i3[k - 1])), t[-1])
        print("  %4.1f A leads %-3s  off in %4.1f us  VBAT peak %5.1f V  Q3 Vsd max %5.1f V  U2 VIN peak %5.2f V" % (
            abs(i3[k - 1]), lw, (toff - 20e-6) * 1e6, max(vb), max(a - b for a, b in zip(vb, ld)), max(en)))

    print("-- DC: fail-on, current while OFF, reverse polarity")
    for vb in (12.6, 8.4, 6.0):
        for name, off in (("MCU dead", ""), ("OFF high", "VOFF off 0 3.3")):
            d = run(c.netlist(plug=False, vbatt=vb, rl="2.5", off=off, vreg="1e12", tran=".op"), vendor)
            g = lambda k: d[k][0]
            iq = -g("vb#branch") - g("load") / 2.5 - g("load") / 133e3
            print("  %4.1f V %-8s Q3 Vgs %+6.2f V  LOAD %5.2f V  Rds(Q3) %s  pack current excl. load %5.1f uA" % (
                vb, name, g("q3g") - g("vbat"), g("load"),
                "%4.1f mOhm" % ((g("vbat") - g("load")) / abs(g("vq3#branch")) * 1e3) if abs(g("vq3#branch")) > 0.1 else "  off    ", iq * 1e6))
    d = run(c.netlist(plug=False, vbatt=-12.6, rl="2.5", tran=".op"), vendor)
    print("  reversed 3S pack: VBAT %.3f V  LOAD %.3f V  U2 VIN %.3f V  battery current %.2f uA" % (
        d["vbat"][0], d["load"][0], d["en"][0], abs(d["vb#branch"][0]) * 1e6))

# heimdall-switch power side (schematic blocks 1-5) as an ngspice netlist, plus models.
# Nets follow the KiCad netlist (kicad-cli sch export netlist); refs in comments.
import os, urllib.request

# Datasheet-fitted models (VDMOS = ngspice's power-MOSFET model, body diode included).
# Fits checked against the datasheets: AO4407A 10.0/26.1 mOhm at Vgs -10/-5V (ds 10/27).
FITTED = """
* AO4407A P-FET: Vth -2.3V, Rds 10mOhm@-10V / 27mOhm@-5V, Ciss 2060p, Crss 295p, Coss 370p, Qg 30nC
.model AO4407A VDMOS pchan (Vto=-2.3 Kp=14 Rd=0.5m Rs=0.3m Rg=2.4 Cgdmax=1.4n Cgdmin=0.2n a=0.4 Cgs=1.75n Cjo=0.5n m=0.5 Is=1e-11 N=1.1 Rb=5m Tt=20n Ksubthres=0.1 lambda=0.01)
* AO3400A N-FET: Vth 1.05V, Rds 19mOhm@4.5V, Ciss 630p, Crss 50p, Coss 75p
.model AO3400A VDMOS nchan (Vto=1.05 Kp=15 Rd=0.3m Rs=0.3m Rg=3 Cgdmax=0.3n Cgdmin=40p a=0.4 Cgs=0.58n Cjo=60p m=0.5 Is=1e-12 N=1.1 Ksubthres=0.1)
* BSS84 P-FET: Vth -1.7V, Rds ~6 Ohm@-10V, Ciss 25p, Crss 5p, Coss 15p
.model BSS84 VDMOS pchan (Vto=-1.7 Kp=0.012 Rd=0.5 Rs=0.5 Rg=10 Cgdmax=15p Cgdmin=3p a=0.4 Cgs=20p Cjo=12p m=0.5 Is=1e-13 N=1 Ksubthres=0.1)
* MMSZ5248B 18V zener: Zzt ~21 Ohm @ 7mA
.model DZ18 D (BV=18 IBV=7m Rs=10 Is=1e-14 N=1 Cjo=60p)
"""
MODELS = FITTED

# AOS's own AO4407A model (subcircuit HPA21C: drain gate source), downloaded on first use
AOS_URL = "https://www.aosmd.com/sites/default/files/res/spice_models/AO4407A.mod"
CACHE = os.path.join(os.path.dirname(__file__), "models", "AO4407A.mod")
def aos_ao4407a():
    if not os.path.exists(CACHE):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        req = urllib.request.Request(AOS_URL, headers={"User-Agent": "Mozilla/5.0"})
        open(CACHE, "wb").write(urllib.request.urlopen(req, timeout=30).read())
    return open(CACHE, encoding="latin-1").read().replace("\r", "")

def vendor(n):
    """Swap Q3/Q4 to AOS's AO4407A model."""
    n = n.replace("M4 battp g4 vbat AO4407A", "XM4 battp g4 vbat HPA21C")
    n = n.replace("M3 load q3g vq3s AO4407A", "XM3 load q3g vq3s HPA21C")
    return n.replace("\n.tran", "\n" + aos_ao4407a() + "\n.tran").replace("\n.op", "\n" + aos_ao4407a() + "\n.op")

def netlist(c7="220n", vbatt=12.6, lw="1u", rbat="20m", plug=True, tplug="10u", trise="50n",
            rl="1e6", cl="1p", lload=None, off="", tran=".tran 5n 300u", vreg="4k", models=None):
    """vbatt: pack; lw: loop inductance of both battery wires; plug: step the pack on at
    tplug (else DC); rl/cl/lload: load resistance, capacitance, wiring inductance;
    off: SPICE line driving node 'off' (P0.13 via R5), default floating (MCU dead/reset)."""
    src = f"VB bsrc 0 PWL(0 0 {tplug} 0 {{{tplug}+{trise}}} {vbatt})" if plug else f"VB bsrc 0 DC {vbatt}"
    load = f"Lld load ld2 {lload}\nRL ld2 0 {rl}\nCL ld2 0 {cl}" if lload else f"RL load 0 {rl}\nCL load 0 {cl}"
    return f"""heimdall-switch power side
{models or MODELS}
* battery + leads
{src}
Rbat bsrc b1 {rbat}
Lw b1 battp {lw}
* block 1: reverse polarity, Q4 ideal diode (J3+ = battp)
M4 battp g4 vbat AO4407A
R1 g4 0 100k
D1 g4 vbat DZ18
* block 2: load switch Q3, fail-on (R9||R10 pull the gate to GND, C7 = C_SS)
Vq3 vbat vq3s 0
M3 load q3g vq3s AO4407A
R9 q3g 0 2.2Meg
R10 q3g 0 2.2Meg
C7 vbat q3g {c7}
D2 q3g vbat DZ18
* block 3: switch-off chain (P0.13 -> R5 -> Q1 -> Q2 -> R8 -> Q3 gate)
R8 q2d q3g 100
M2 q2d q1d vbat BSS84
R7 vbat q1d 1Meg
M1 q1d q1g 0 AO3400A
R5 off q1g 100
R6 q1g 0 1Meg
{off or "Roff off 0 100Meg"}
* block 5 input: R2 (R_IN) + C3 (10uF 50V X7R 1206, ~5uF left at 12V); U2 as a light load
R2 vbat en 22
C3 en 0 5u
Rreg en 0 {vreg}
* block 4: load + ADC divider (J2+ = load)
R11 load adc 100k
R12 adc 0 33k
C8 adc 0 100n
{load}
{tran}
"""

# Minimal ngspice (shared library from KiCad) driver: run(netlist_text, analysis) -> {vector: list}
import ctypes, os, re
DLL = r"C:\Users\svefre\AppData\Local\Programs\KiCad\10.0\bin\ngspice.dll"
os.add_dll_directory(os.path.dirname(DLL))
ng = ctypes.CDLL(DLL)
LOG = []
PF = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
EF = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
_out = PF(lambda s, i, u: (LOG.append(s.decode(errors="replace")), 0)[1])
_stat = PF(lambda s, i, u: 0)
_exit = EF(lambda st, unl, q, i, u: 0)
ng.ngSpice_Init(_out, _stat, _exit, None, None, None, None)
class VecInfo(ctypes.Structure):
    _fields_ = [("name", ctypes.c_char_p), ("type", ctypes.c_int), ("flags", ctypes.c_short),
                ("realdata", ctypes.POINTER(ctypes.c_double)), ("compdata", ctypes.c_void_p), ("length", ctypes.c_int)]
ng.ngGet_Vec_Info.restype = ctypes.POINTER(VecInfo)
ng.ngSpice_CurPlot.restype = ctypes.c_char_p
ng.ngSpice_AllVecs.restype = ctypes.POINTER(ctypes.c_char_p)
def cmd(c): ng.ngSpice_Command(c.encode())
def run(netlist):
    LOG.clear(); cmd("destroy all"); cmd("remcirc")
    lines = [l for l in netlist.strip().splitlines()] + [".end"]
    arr = (ctypes.c_char_p * (len(lines) + 1))(*[l.encode() for l in lines], None)
    ng.ngSpice_Circ(arr)
    cmd("run")
    plot = ng.ngSpice_CurPlot().decode()
    names, i = [], 0
    vs = ng.ngSpice_AllVecs(plot.encode())
    while vs[i]: names.append(vs[i].decode()); i += 1
    out = {}
    for n in names:
        v = ng.ngGet_Vec_Info(("%s.%s" % (plot, n)).encode()).contents
        if v.realdata: out[n.lower()] = [v.realdata[k] for k in range(v.length)]
    errs = [l for l in LOG if re.search(r"error|warning", l, re.I)]
    return out, errs

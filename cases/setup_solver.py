#!/usr/bin/env python3
"""Этап B (решатель): поля, свойства, схемы и запуск foamRun для готовой сетки.
Пример:
    python3 setup_solver.py --case t1 --speed 3.5 --np 8 --iters 600
Берёт fvSchemes/fvSolution/physicalProperties из туториала pitzDailySteady (kEpsilon -> kOmegaSST).
"""
import argparse, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HDR = "FoamFile\n{\n    format ascii;\n    class %s;\n    object %s;\n}\n\n"
TUT = os.path.join(os.environ.get("FOAM_TUTORIALS", "/opt/openfoam14/tutorials"), "incompressibleFluid", "pitzDailySteady")


def wfile(path, cls, name, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write((HDR % (cls, name)) + body)


def patches(case):
    bp = os.path.join(case, "processor0", "constant", "polyMesh", "boundary")
    if not os.path.exists(bp):
        bp = os.path.join(case, "constant", "polyMesh", "boundary")
    txt = open(bp).read()
    out = []
    for m in re.finditer(r"^\s{4}(\w[\w.\-]*)\s*\n\s{4}\{(.*?)\n\s{4}\}", txt, re.S | re.M):
        t = re.search(r"\btype\s+(\w+)", m.group(2))
        out.append((m.group(1), t.group(1) if t else "?"))
    return out


def run(cmd, case, log):
    print(">>", cmd, flush=True)
    with open(os.path.join(case, log), "w") as f:
        r = subprocess.run(cmd, shell=True, cwd=case, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        print(f"ОШИБКА, смотри {case}/{log}")
        print("".join(open(os.path.join(case, log)).readlines()[-25:]))
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--speed", type=float, default=3.5)
    ap.add_argument("--np", type=int, default=8)
    ap.add_argument("--iters", type=int, default=600)
    ap.add_argument("--ti", type=float, default=0.05, help="интенсивность турбулентности на входе")
    ap.add_argument("--L", type=float, default=0.1, help="масштаб турбулентности на входе, м")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    case = os.path.join(HERE, a.case)
    V = a.speed
    k = 1.5 * (a.ti * V) ** 2
    om = (k ** 0.5) / (0.5477 * a.L)
    pl = patches(case)
    print("Патчи:", pl)
    walls = [n for n, t in pl if n not in ("inlet", "outlet", "sides") and not n.startswith(("processor", "procBoundary"))]

    def bf(inlet, outlet, sides, wall):
        s = "boundaryField\n{\n    #includeEtc \"caseDicts/setConstraintTypes\"\n\n"
        s += f"    inlet\n    {{\n{inlet}\n    }}\n    outlet\n    {{\n{outlet}\n    }}\n    sides\n    {{\n{sides}\n    }}\n"
        for n in walls:
            s += f"    {n}\n    {{\n{wall}\n    }}\n"
        return s + "}\n"

    ind = lambda s: "\n".join("        " + l for l in s.strip().split("\n"))
    dims = lambda d: f"dimensions {d};\n\n"
    wfile(f"{case}/0/U", "volVectorField", "U", dims("[0 1 -1 0 0 0 0]") + f"internalField uniform ({V} 0 0);\n\n" +
          bf(ind(f"type fixedValue;\nvalue uniform ({V} 0 0);"), ind("type zeroGradient;"),
             ind("type slip;"), ind("type noSlip;")))
    wfile(f"{case}/0/p", "volScalarField", "p", dims("[0 2 -2 0 0 0 0]") + "internalField uniform 0;\n\n" +
          bf(ind("type zeroGradient;"), ind("type fixedValue;\nvalue uniform 0;"),
             ind("type zeroGradient;"), ind("type zeroGradient;")))
    wfile(f"{case}/0/k", "volScalarField", "k", dims("[0 2 -2 0 0 0 0]") + f"internalField uniform {k:.6g};\n\n" +
          bf(ind(f"type fixedValue;\nvalue uniform {k:.6g};"), ind(f"type inletOutlet;\ninletValue uniform {k:.6g};\nvalue uniform {k:.6g};"),
             ind("type zeroGradient;"), ind(f"type kqRWallFunction;\nvalue uniform {k:.6g};")))
    wfile(f"{case}/0/omega", "volScalarField", "omega", dims("[0 0 -1 0 0 0 0]") + f"internalField uniform {om:.6g};\n\n" +
          bf(ind(f"type fixedValue;\nvalue uniform {om:.6g};"), ind(f"type inletOutlet;\ninletValue uniform {om:.6g};\nvalue uniform {om:.6g};"),
             ind("type zeroGradient;"), ind(f"type omegaWallFunction;\nvalue uniform {om:.6g};")))
    wfile(f"{case}/0/nut", "volScalarField", "nut", dims("[0 2 -1 0 0 0 0]") + "internalField uniform 0;\n\n" +
          bf(ind("type calculated;\nvalue uniform 0;"), ind("type calculated;\nvalue uniform 0;"),
             ind("type calculated;\nvalue uniform 0;"), ind("type nutkWallFunction;\nvalue uniform 0;")))

    shutil.copy(f"{TUT}/constant/physicalProperties", f"{case}/constant/physicalProperties")
    txt = open(f"{case}/constant/physicalProperties").read()
    txt = re.sub(r"(\bnu\s+(?:\[[^\]]*\]\s+)?)[0-9.eE+\-]+", r"\g<1>1.5e-05", txt)
    open(f"{case}/constant/physicalProperties", "w").write(txt)
    wfile(f"{case}/constant/momentumTransport", "dictionary", "momentumTransport",
          "simulationType RAS;\n\nRAS\n{\n    model kOmegaSST;\n}\n")

    for fn in ("fvSchemes", "fvSolution"):
        t = open(f"{TUT}/system/{fn}").read().replace("epsilon", "omega")
        if fn == "fvSchemes":
            t = re.sub(r"(div\(phi,(?:k|omega)\)\s+bounded Gauss )limitedLinear 1;", r"\1upwind;", t)
        else:
            def soften(m):
                return re.sub(r"\b0\.[89]\b", "0.7", m.group(0))
            t = re.sub(r"equations\s*\{.*?\}", soften, t, flags=re.S)
        open(f"{case}/system/{fn}", "w").write(t)
    cd = open(f"{case}/system/controlDict").read()
    cd = re.sub(r"endTime\s+\d+;", f"endTime {a.iters};", cd)
    open(f"{case}/system/controlDict", "w").write(cd)
    wfile(f"{case}/system/decomposeParDict", "dictionary", "decomposeParDict",
          f"numberOfSubdomains {a.np};\nmethod scotch;\n")
    print(f"U={V} м/с, k={k:.4g}, omega={om:.4g}, стенки: {walls}")
    if a.dry:
        return
    import glob
    for d in sorted(glob.glob(os.path.join(case, "processor*"))):
        shutil.rmtree(os.path.join(d, "0"), ignore_errors=True)
        shutil.copytree(os.path.join(case, "0"), os.path.join(d, "0"))
    run(f"mpirun --allow-run-as-root -np {a.np} foamRun -parallel", case, "log.foamRun")
    print(subprocess.run("grep -E 'SIMPLE solution|ExecutionTime|^End' log.foamRun | tail -3", shell=True, cwd=case, capture_output=True, text=True).stdout)


if __name__ == "__main__":
    main()

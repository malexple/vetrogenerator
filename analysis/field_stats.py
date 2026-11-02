import re, glob, sys, numpy as np
case, t = sys.argv[1], sys.argv[2]
for f in ("nut", "k", "omega"):
    v = []
    for p in sorted(glob.glob(f"{case}/processor*/{t}/{f}")):
        s_ = open(p).read()
        m = re.search(r"nonuniform List<scalar>\s*(\d+)\s*\(", s_)
        a = m.end(); e = s_.index("\n)\n;", a)
        v.append(np.fromstring(s_[a:e], sep=" "))
    v = np.concatenate(v)
    print(f, "min", v.min(), "mean", v.mean(), "max", v.max())

cd ~/vetrogenerator/analysis
python3 - <<'EOF'
p = 'metrics.py'
s = open(p).read()
a1 = '    ap.add_argument("--Rc", type=float, default=0.10)\n'
b1 = a1 + '    ap.add_argument("--Rtop", type=float, default=None, help="радиус полости при z=+0.5")\n    ap.add_argument("--Rbot", type=float, default=None, help="радиус полости при z=-0.5")\n'
a2 = '    sel = (r < a.Rc) & (np.abs(X[:, 2]) < a.zmax) & (r > 1e-6)\n'
b2 = ('    rt = a.Rtop if a.Rtop else a.Rc\n    rb = a.Rbot if a.Rbot else a.Rc\n'
      '    rcone = rb + (rt - rb) * (X[:, 2] + 0.5)\n'
      '    sel = (r < rcone) & (np.abs(X[:, 2]) < a.zmax) & (r > 1e-6)\n')
assert a1 in s and a2 in s
open(p, 'w').write(s.replace(a1, b1).replace(a2, b2))
EOF

#!/bin/bash
for pair in "t3:shell_open" "t4:shell_open_plug"; do
  n=${pair%%:*}; s=${pair##*:}
  python3 make_case.py --name $n --angle 0 --np 8 --stl ../geometry/out/$s.stl || exit 1
  python3 setup_solver.py --case $n --speed 3.5 --np 8 --iters 600 || exit 1
  (cd $n && mpirun --allow-run-as-root -np 8 foamPostProcess -parallel -func writeCellCentres -latestTime >/dev/null \
        && mpirun --allow-run-as-root -np 8 foamPostProcess -parallel -func writeCellVolumes -latestTime >/dev/null)
  python3 field_stats.py ../cases/$n 600 2>/dev/null
  python3 ../analysis/metrics.py --case $n --vinf 3.5 --append ../results/summary.csv
done

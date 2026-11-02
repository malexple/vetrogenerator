#!/bin/bash
# имя:lvl_min:lvl_max:cyl_level
for job in "t3_m3:3:4:4" "t3_m6:5:6:6"; do
  IFS=: read n l0 l1 lc <<< "$job"
  python3 make_case.py --name $n --angle 0 --np 8 --stl ../geometry/out/shell_open.stl --lvl $l0 $l1 --cyl-level $lc || exit 1
  python3 setup_solver.py --case $n --speed 3.5 --np 8 --iters 600 || exit 1
  (cd $n && mpirun --allow-run-as-root -np 8 foamPostProcess -parallel -func writeCellCentres -latestTime >/dev/null \
        && mpirun --allow-run-as-root -np 8 foamPostProcess -parallel -func writeCellVolumes -latestTime >/dev/null)
  python3 ../analysis/metrics.py --case $n --vinf 3.5 --append ../results/summary.csv
done

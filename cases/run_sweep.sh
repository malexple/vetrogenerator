#!/bin/bash
# имя:stl:угол:скорость
for job in "t3_a7:shell_open:7.5:3.5" "t3_a15:shell_open:15:3.5" \
           "t4_a7:shell_open_plug:7.5:3.5" "t4_a15:shell_open_plug:15:3.5" \
           "t3_v2:shell_open:0:2.0" "t3_v5:shell_open:0:5.0"; do
  IFS=: read n s ang v <<< "$job"
  python3 make_case.py --name $n --angle $ang --np 8 --stl ../geometry/out/$s.stl || exit 1
  python3 setup_solver.py --case $n --speed $v --np 8 --iters 600 || exit 1
  (cd $n && mpirun --allow-run-as-root -np 8 foamPostProcess -parallel -func writeCellCentres -latestTime >/dev/null \
        && mpirun --allow-run-as-root -np 8 foamPostProcess -parallel -func writeCellVolumes -latestTime >/dev/null)
  python3 ../analysis/metrics.py --case $n --vinf $v --append ../results/summary.csv
done

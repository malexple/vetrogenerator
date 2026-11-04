```bash
python3 make_shell.py && python3 make_shell.py --control
{
  "name": "shell",
  "control": false,
  "watertight": true,
  "winding_consistent": true,
  "volume_m3": 0.0988580421992607,
  "bodies": 1,
  "faces": 36008,
  "bounds": [
    [
      -0.44999998807907104,
      -0.44999998807907104,
      -0.49989795684814453
    ],
    [
      0.44999998807907104,
      0.44999998807907104,
      0.49495163559913635
    ]
  ],
  "symmetry_overlap": 0.9973823937734012
}
ПРОВЕРКА: OK
{
  "name": "control",
  "control": true,
  "watertight": true,
  "winding_consistent": true,
  "volume_m3": 0.023885235709707353,
  "bodies": 1,
  "faces": 9748,
  "bounds": [
    [
      -0.44999998807907104,
      -0.44999998807907104,
      -0.49989795684814453
    ],
    [
      0.44999998807907104,
      0.44999998807907104,
      0.49495163559913635
    ]
  ]
}
ПРОВЕРКА: OK
```

## Этап A закрыт

Теперь обе модели (полная и контрольная) замкнуты, состоят из одного куска и проходят проверку. Причиной сбоя в контроле была склейка вершин, и отключение `process=True` её устранило. Картинки сечений должны были построиться, потому что ошибка про `matplotlib` в этот раз не появилась. 

![shell_xy.png](geometry/out/shell_xy.png)
![shell_xz.png](geometry/out/shell_xz.png)



![image-20261102042349523](.assets/image-20261102042349523.png)


![image-20261102042428210](.assets/image-20261102042428210.png)

В сечении XY видны 12 спиральных рёбер и круглое отверстие, в XZ — полая труба с плитой внизу.


Этап G



```
root@cyclone2:~/vetrogenerator# cd ~/vetrogenerator/cases
root@cyclone2:~/vetrogenerator/cases# chmod +x run_channel.sh
root@cyclone2:~/vetrogenerator/cases# python3 make_channel.py --name g0
{
  "mesh": {
    "nPoints": 725109,
    "nCells": 691200,
    "nFaces": 2107104,
    "nInternal": 2040096,
    "patches": [
      [
        "inlet",
        "patch",
        2304
      ],
      [
        "ribB",
        "wall",
        21600
      ],
      [
        "ribA",
        "wall",
        21600
      ],
      [
        "floor",
        "wall",
        9600
      ],
      [
        "roof",
        "wall",
        9600
      ],
      [
        "outlet",
        "patch",
        768
      ],
      [
        "cone",
        "wall",
        1536
      ]
    ]
  },
  "quality": {
    "min_vol": 5.637490739592781e-18,
    "max_vol": 1.0951663189435232e-08,
    "neg_cells": 0,
    "max_nonorth_deg": 62.04198572653615,
    "mean_nonorth_deg": 16.0332113317902,
    "n_nonorth_gt70": 0
  }
}
ПРОВЕРКА СЕТКИ: OK
```

```
root@cyclone2:~/vetrogenerator/cases# python3 setup_channel.py --case g0 --speed 3.5 --np 8 --iters 800
V=3.5, p0=6.125 (кин.), k=0.04594, omega=78.27, направление входа (-0.884711 -0.466140 0)
>> checkMesh
    cells:            691200
 ***High aspect ratio cells found, Max aspect ratio: 6.10823e+06, number of cells 337550
    Mesh non-orthogonality Max: 170.132 average: 31.6232
   *Number of severely non-orthogonal (> 70 degrees) faces: 171507.
 ***Number of non-orthogonality errors: 27523.
 ***Max skewness = 446.762, 21 highly skew faces detected which may impair the quality of the results
Failed 4 mesh checks.

>> decomposePar -force
>> mpirun --allow-run-as-root -np 8 foamRun -parallel
ОШИБКА, смотри /root/vetrogenerator/cases/g0/log.foamRun
[cyclone2:23033] [ 9] /opt/openfoam14/platforms/linux64GccDPInt32Opt/lib/libincompressibleFluidSolver.so(_ZN4Foam8fvMatrixINS_6VectorIdEEE5solveEv+0x8d)[0x7f06328751ed]
[cyclone2:23033] [10] /opt/openfoam14/platforms/linux64GccDPInt32Opt/lib/libincompressibleFluidSolver.so(_ZN4Foam7solvers19incompressibleFluid17momentumPredictorEv+0x312)[0x7f06328447f2]
[cyclone2:23033] [11] foamRun(+0x539e)[0x559e995d539e]
[cyclone2:23033] [12] /lib/x86_64-linux-gnu/libc.so.6(+0x29d90)[0x7f063ce29d90]
[cyclone2:23033] [13] /lib/x86_64-linux-gnu/libc.so.6(__libc_start_main+0x80)[0x7f063ce29e40]
[cyclone2:23033] [14] foamRun(+0x59a5)[0x559e995d59a5]
[cyclone2:23033] *** End of error message ***
/opt/openfoam14/platforms/linux64GccDPInt32Opt/lib/libOpenFOAM.so(_ZNK4Foam22symGaussSeidelSmoother6smoothERNS_5FieldIdEERKS2_hi+0x2c)[0x7f58fd7f6d4c]
[cyclone2:23029] [ 6] /opt/openfoam14/platforms/linux64GccDPInt32Opt/lib/libOpenFOAM.so(_ZNK4Foam12smoothSolver5solveERNS_5FieldIdEERKS2_h+0x3b1)[0x7f58fd7ecc61]
[cyclone2:23029] [ 7] /opt/openfoam14/platforms/linux64GccDPInt32Opt/lib/libincompressibleFluidSolver.so(_ZN4Foam8fvMatrixINS_6VectorIdEEE15solveSegregatedERKNS_10dictionaryE+0x5ea)[0x7f58f837cbea]
[cyclone2:23029] [ 8] /opt/openfoam14/platforms/linux64GccDPInt32Opt/lib/libincompressibleFluidSolver.so(_ZN4Foam8fvMatrixINS_6VectorIdEEE5solveERKNS_10dictionaryE+0x2ab)[0x7f58f8383f2b]
[cyclone2:23029] [ 9] /opt/openfoam14/platforms/linux64GccDPInt32Opt/lib/libincompressibleFluidSolver.so(_ZN4Foam8fvMatrixINS_6VectorIdEEE5solveEv+0x8d)[0x7f58f83841ed]
[cyclone2:23029] [10] /opt/openfoam14/platforms/linux64GccDPInt32Opt/lib/libincompressibleFluidSolver.so(_ZN4Foam7solvers19incompressibleFluid17momentumPredictorEv+0x312)[0x7f58f83537f2]
[cyclone2:23029] [11] foamRun(+0x539e)[0x5582bd27339e]
[cyclone2:23029] [12] /lib/x86_64-linux-gnu/libc.so.6(+0x29d90)[0x7f58fca29d90]
[cyclone2:23029] [13] /lib/x86_64-linux-gnu/libc.so.6(__libc_start_main+0x80)[0x7f58fca29e40]
[cyclone2:23029] [14] foamRun(+0x59a5)[0x5582bd2739a5]
[cyclone2:23029] *** End of error message ***
--------------------------------------------------------------------------
Primary job  terminated normally, but 1 process returned
a non-zero exit code. Per user-direction, the job has been aborted.
--------------------------------------------------------------------------
--------------------------------------------------------------------------
mpirun noticed that process rank 6 with PID 0 on node cyclone2 exited on signal 8 (Floating point exception).
--------------------------------------------------------------------------
```


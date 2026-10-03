# NOMOI Gaussian-splat sample viewer

A static browser viewer for one sample scene, hosted on NOMOI infrastructure.
The scene is the `chili-salmon-bowl` from [promc/reconstruction-scenes](https://huggingface.co/datasets/promc/reconstruction-scenes), published by that dataset owner as CC0. It is not customer content. The source release supplies 43 image files, COLMAP pose data, and a Gaussian PLY; this repository contains the `.splat` converted from that supplied PLY by NOMOI's existing `.tools/ply-to-splat`. It does not claim NOMOI trained the PLY.

Viewer code is from [antimatter15/splat](https://github.com/antimatter15/splat), MIT; its licence is in `VIEWER-LICENSE.txt`.

The `/spz/` option uses the same source PLY as `scene.splat`. Its 4,839,014-byte SPZ v3 file omits spherical harmonics to match the original viewer’s degree-zero colour. It uses Spark 2.3.1 and Three.js 0.180.0, with MIT notices under `spz/vendor/`. The third picker slot remains disabled because a fresh trained scene has not been produced.

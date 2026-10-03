# NOMOI Gaussian-splat sample viewer

A static browser viewer for one sample scene, hosted on NOMOI infrastructure.
The scene is the `chili-salmon-bowl` from [promc/reconstruction-scenes](https://huggingface.co/datasets/promc/reconstruction-scenes), published by that dataset owner as CC0. It is not customer content. The source release supplies 43 image files, COLMAP pose data, and a Gaussian PLY; this repository contains the `.splat` converted from that supplied PLY by NOMOI's existing `.tools/ply-to-splat`. It does not claim NOMOI trained the PLY.

Viewer code is from [antimatter15/splat](https://github.com/antimatter15/splat), MIT; its licence is in `VIEWER-LICENSE.txt`.

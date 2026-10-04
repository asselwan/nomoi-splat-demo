# NOMOI Gaussian-splat sample viewer

A static browser viewer for the source sample, a NOMOI GPU-trained reconstruction, and comparison scenes, hosted on NOMOI infrastructure.
The scene is the `chili-salmon-bowl` from [promc/reconstruction-scenes](https://huggingface.co/datasets/promc/reconstruction-scenes), published by that dataset owner as CC0. It is not customer content. The source release supplies a Gaussian PLY and COLMAP data. `scene.splat` is converted from that supplied PLY. `trained.splat` was trained by NOMOI with Nerfstudio Splatfacto from 51 CC0 photos and the supplied COLMAP reconstruction, then converted from the exported PLY. Neither scene is customer content.

Viewer code is from [antimatter15/splat](https://github.com/antimatter15/splat), MIT; its licence is in `VIEWER-LICENSE.txt`.

The `/spz/` option uses the same source PLY as `scene.splat`. Its 4,839,014-byte SPZ v3 file omits spherical harmonics to match the original viewer’s degree-zero colour. It uses Spark 2.3.1 and Three.js 0.180.0, with MIT notices under `spz/vendor/`. The picker also links to the separately GPU-trained scene with `?scene=trained`.

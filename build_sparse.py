"""Generate the sparse failure probe using the existing static WebGL host."""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
ART = Path('/home/ainur/Apps/.ainur/review/splat/sparse-photos')
OUT = ROOT / 'sparse'
OUT.mkdir(exist_ok=True)
data = json.loads((ART / 'inference-metrics.json').read_text())
poses = []
for i, im in enumerate(data['images']):
    m = im['camera_to_world_cv']
    # antimatter15's projection looks along camera +Z, matching MapAnything's
    # OpenCV camera frame; the Three/Spark preview used a different convention.
    cv = [m[row][:3] for row in range(3)]
    poses.append({
        'id': i,
        'img_name': im['file'],
        'width': im['width'],
        'height': im['height'],
        'position': [m[row][3] for row in range(3)],
        'rotation': cv,
        'fy': im['intrinsics'][1][1],
        'fx': im['intrinsics'][0][0],
    })
js = (ROOT / 'main.js').read_text()
js, n = re.subn(r'let cameras = \[.*?\];(?=\s*let camera = cameras\[0\];)', 'let cameras = ' + json.dumps(poses, indent=2) + ';', js, count=1, flags=re.S)
assert n == 1
js, n = re.subn(r'let defaultViewMatrix = \[.*?\];', 'let defaultViewMatrix = getViewMatrix(cameras[0]);', js, count=1, flags=re.S)
assert n == 1
js = js.replace('let carousel = true;', 'let carousel = false;', 1)
(OUT / 'main.js').write_text(js)
html = (ROOT / 'index.html').read_text()
html = html.replace('NOMOI sample Gaussian splat — chili-salmon bowl', '20-photo sparse reconstruction failure probe')
html = re.sub(r'<strong>NOMOI technical sample</strong><br>.*?</aside>', '<strong>20-photo reconstruction probe — failed quality gate</strong><br>One skull photographed from 20 unposed views. The model estimated cameras and depth, but the resulting splat is not recognizable. Photos: <a href="https://gitlab.com/photogrammetry-test-sets/skull-cameramoves-weak-light-no-background" target="_blank" rel="noopener noreferrer">alansartlog, CC BY 4.0</a>. Viewer: <a href="https://github.com/antimatter15/splat" target="_blank" rel="noopener noreferrer">antimatter15/splat</a> (MIT). <a href="source-contact-sheet.jpg" target="_blank">Original views</a>.</aside>', html, count=1, flags=re.S)
assert 'failed quality gate' in html
html = html.replace('main.js?v=94c4b6f', 'main.js?v=sparse1')
(OUT / 'index.html').write_text(html)
shutil.copyfile(ART / 'mapanything-gaussians.splat', OUT / 'scene.splat')
shutil.copyfile(ART / 'input-contact-sheet.jpg', OUT / 'source-contact-sheet.jpg')
shutil.copyfile(ROOT / 'VIEWER-LICENSE.txt', OUT / 'VIEWER-LICENSE.txt')
docker = (ROOT / 'Dockerfile').read_text()
if 'COPY sparse/' not in docker:
    docker = docker.replace('COPY nginx.conf', 'COPY sparse/ /usr/share/nginx/html/sparse/\nCOPY nginx.conf')
    (ROOT / 'Dockerfile').write_text(docker)
print(f'{len(poses)} poses; {sum(p.stat().st_size for p in OUT.iterdir())} bytes')

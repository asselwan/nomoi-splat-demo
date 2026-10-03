import * as THREE from 'three';
import { SparkRenderer, SplatMesh } from '@sparkjsdev/spark';

const status = document.getElementById('status');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.01, 100);
const renderer = new THREE.WebGLRenderer({ antialias: false });
renderer.setPixelRatio(1);
renderer.setSize(innerWidth, innerHeight);
renderer.setClearColor(0x000000, 1);
document.body.appendChild(renderer.domElement);
const spark = new SparkRenderer({ renderer });
scene.add(spark);

const probe = window.__splatProbe || (window.__splatProbe = {
  firstDrawMs: null, firstPixelsMs: null, fullDrawMs: null,
  maxInstances: 0, drawCount: 0, loadedMs: null
});
const gl = renderer.getContext();
for (const name of ['drawArraysInstanced', 'drawElementsInstanced']) {
  const original = gl[name].bind(gl);
  gl[name] = (...args) => {
    const result = original(...args);
    const instances = args[name === 'drawArraysInstanced' ? 3 : 4];
    const now = performance.now();
    probe.drawCount++;
    probe.maxInstances = Math.max(probe.maxInstances, instances);
    if (probe.firstDrawMs === null) probe.firstDrawMs = now;
    if (instances >= 306831 && probe.fullDrawMs === null) probe.fullDrawMs = now;
    return result;
  };
}

const view = new URLSearchParams(location.search);
let yaw = Number(view.get('yaw') ?? '2.07');
let pitch = Number(view.get('pitch') ?? '0.105');
let radius = Number(view.get('radius') ?? '6.55');
let dragging = false;
let lastX = 0, lastY = 0;
function positionCamera() {
  camera.position.set(radius * Math.sin(yaw) * Math.cos(pitch), radius * Math.sin(pitch), radius * Math.cos(yaw) * Math.cos(pitch));
  camera.lookAt(0, 0, 0);
}
positionCamera();
renderer.domElement.addEventListener('pointerdown', e => { dragging = true; lastX = e.clientX; lastY = e.clientY; renderer.domElement.setPointerCapture(e.pointerId); });
renderer.domElement.addEventListener('pointerup', () => { dragging = false; });
renderer.domElement.addEventListener('pointermove', e => {
  if (!dragging) return;
  yaw -= (e.clientX - lastX) * 0.005;
  pitch = Math.max(-1.3, Math.min(1.3, pitch + (e.clientY - lastY) * 0.005));
  lastX = e.clientX; lastY = e.clientY;
  positionCamera();
});
renderer.domElement.addEventListener('wheel', e => { e.preventDefault(); radius = Math.max(1, Math.min(15, radius * Math.exp(e.deltaY * 0.001))); positionCamera(); }, { passive: false });
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });

const mesh = new SplatMesh({
  url: './scene.spz',
  onProgress: e => { if (e.lengthComputable) status.textContent = `Loading SPZ scene ${Math.min(100, Math.round(100 * e.loaded / e.total))}%`; },
  onLoad: () => { probe.loadedMs = performance.now(); status.textContent = 'Rendering SPZ scene…'; }
});
mesh.quaternion.set(1, 0, 0, 0);
scene.add(mesh);
mesh.initialized.catch(e => { status.textContent = `SPZ load failed: ${e.message}`; console.error(e); });

const pixels = new Uint8Array(128 * 128 * 4);
renderer.setAnimationLoop(() => {
  renderer.render(scene, camera);
  if (mesh.isInitialized && probe.firstPixelsMs === null) {
    const previousPackBuffer = gl.getParameter(gl.PIXEL_PACK_BUFFER_BINDING);
    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null);
    gl.readPixels(Math.floor((renderer.domElement.width - 128) / 2), Math.floor((renderer.domElement.height - 128) / 2), 128, 128, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, previousPackBuffer);
    for (let i = 0; i < pixels.length; i += 4) {
      if (pixels[i + 3] > 10 && (pixels[i] > 10 || pixels[i + 1] > 10 || pixels[i + 2] > 10)) {
        probe.firstPixelsMs = performance.now();
        status.style.display = 'none';
        break;
      }
    }
  }
});

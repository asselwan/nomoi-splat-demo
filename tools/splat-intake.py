#!/usr/bin/env python3
"""Manually poll a synced Drive/Dain drop directory and wrap the existing splat rail.

Each child directory contains images and submission.json. No network ingest is
implied: the operator supplies --inbox on the host where attachments are synced.
"""
import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

IMAGE_EXT = {'.jpg', '.jpeg', '.png'}
RIGHTS = ('owns_or_licensed_photos', 'may_reconstruct', 'may_publish_scene',
          'property_and_occupant_authority', 'no_phi', 'faces_and_plates_cleared')
TOOLS = Path('/home/ainur/Apps/.tools')


def run(*args):
    subprocess.run([str(x) for x in args], check=True)


def validate(drop):
    data = json.loads((drop / 'submission.json').read_text())
    if not isinstance(data, dict):
        raise ValueError('submission must be an object')
    for key in RIGHTS:
        if data.get(key) is not True:
            raise ValueError(f'confirmed {key}=true required before processing')
    if not isinstance(data.get('submitter'), str) or not data['submitter'].strip():
        raise ValueError('named submitter required')
    if not isinstance(data.get('name'), str) or not 1 <= len(data['name']) <= 80:
        raise ValueError('scene name required (1-80 characters)')
    if not isinstance(data.get('rights_statement'), str) or not data['rights_statement'].strip():
        raise ValueError('written rights statement required')
    photos = sorted(p for p in drop.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXT)
    if len(photos) < 15:
        raise ValueError(f'15 photos minimum; found {len(photos)}')
    for photo in photos:
        if photo.is_symlink() or photo.stat().st_size == 0:
            raise ValueError(f'invalid photo: {photo.name}')
    return data, photos


def prepare_source(drop, photos, work):
    source = work / 'source'
    images = source / 'images'
    images.mkdir(parents=True)
    for photo in photos:
        shutil.copy2(photo, images / photo.name)
    supplied = drop / 'sparse' / '0'
    if all((supplied / name).is_file() for name in ('cameras.bin', 'images.bin', 'points3D.bin')):
        shutil.copytree(drop / 'sparse', source / 'sparse')
    else:
        database = work / 'colmap.db'
        run('colmap', 'feature_extractor', '--database_path', database,
            '--image_path', images, '--ImageReader.single_camera', '1')
        run('colmap', 'exhaustive_matcher', '--database_path', database)
        sparse = source / 'sparse'
        sparse.mkdir()
        run('colmap', 'mapper', '--database_path', database, '--image_path', images,
            '--output_path', sparse)
    model = source / 'sparse' / '0'
    if not all((model / name).is_file() for name in ('cameras.bin', 'images.bin', 'points3D.bin')):
        raise RuntimeError('COLMAP did not produce one complete sparse/0 model')
    result = subprocess.run(['colmap', 'model_analyzer', '--path', str(model)],
                            check=True, capture_output=True, text=True)
    found = re.search(r'Registered images:\s*(\d+)', result.stdout + result.stderr)
    if not found or int(found.group(1)) < 8:
        raise RuntimeError('fewer than 8 registered camera views; stop before paid training')
    return source, int(found.group(1))


def process(drop, args):
    data, photos = validate(drop)
    slug = re.sub(r'[^a-z0-9-]+', '-', drop.name.lower()).strip('-')[:50]
    if not slug:
        raise ValueError('drop folder needs a usable name')
    scene_id = 'upload-' + slug
    manifest_path = args.repo / 'submitted-scenes.json'
    manifest = json.loads(manifest_path.read_text())
    if any(row['id'] == scene_id for row in manifest):
        print(json.dumps({'drop': str(drop), 'scene': scene_id, 'status': 'already_staged'}))
        return
    work = args.work / slug
    if work.exists():
        raise ValueError('work folder already exists; inspect prior run before retry')
    if args.check:
        print(json.dumps({'drop': str(drop), 'scene': scene_id, 'photos': len(photos),
                          'rights_confirmed': True, 'test': data.get('test_submission') is True}))
        return
    for tool in ('quincunx-run', 'ply-to-splat', 'runpod-gaussian-train', 'cred-resolve'):
        if not (TOOLS / tool).is_file():
            raise RuntimeError(f'existing Beelink tool missing: {TOOLS / tool}')
    work.mkdir(parents=True)
    source, registered = prepare_source(drop, photos, work)
    ply = work / 'trained.ply'
    spec = work / 'train.spec'
    spec.write_text('RUNPOD_TRAIN: ' + json.dumps({'source': str(source), 'cap_aed': 10,
                                                     'output': str(ply), 'dry_run': False}) + '\n')
    run(TOOLS / 'quincunx-run', 'splat-' + slug, spec)
    if not ply.is_file() or ply.stat().st_size < 1024:
        raise RuntimeError('trainer returned without a valid PLY')
    asset = args.repo / 'submitted' / (scene_id + '.splat')
    asset.parent.mkdir(exist_ok=True)
    run(TOOLS / 'ply-to-splat', ply, asset)
    if asset.stat().st_size < 32 or asset.stat().st_size % 32:
        raise RuntimeError('converted splat invalid')
    row = {'id': scene_id, 'name': data['name'], 'submitter': data['submitter'],
           'provenance': data['rights_statement'], 'trained_reconstruction': True,
           'test_submission': data.get('test_submission') is True,
           'photo_count': len(photos), 'registered_count': registered,
           'asset': 'submitted/' + asset.name, 'bytes': asset.stat().st_size,
           'created_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    manifest.append(row)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    (work / 'receipt.json').write_text(json.dumps(row, indent=2) + '\n')
    print(json.dumps({'scene_url': f'https://nomoi.ai/splat-demo/?scene={scene_id}',
                      'status': 'staged_in_repo; deploy required', 'receipt': str(work / 'receipt.json')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inbox', type=Path, required=True, help='local synced Drive/Dain drop folder')
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true', help='validate rights and count without copying or spending')
    args = parser.parse_args()
    args.inbox, args.work, args.repo = (p.resolve() for p in (args.inbox, args.work, args.repo))
    if not args.inbox.is_dir():
        parser.error('inbox does not exist')
    drops = sorted(p for p in args.inbox.iterdir() if p.is_dir() and (p / 'submission.json').is_file())
    if not drops:
        print('no submissions')
    failed = False
    for drop in drops:
        try:
            process(drop, args)
        except Exception as exc:
            print(json.dumps({'drop': str(drop), 'error': str(exc)}), file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())

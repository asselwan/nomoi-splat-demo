#!/usr/bin/env python3
"""Manually poll a synced Drive/Dain drop directory and wrap the existing splat rail.

Each child directory contains photos or one video and submission.json. No network ingest is
implied: the operator supplies --inbox on the host where attachments are synced.
"""
import argparse
import datetime as dt
import json
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from PIL import Image

IMAGE_EXT = {'.jpg', '.jpeg', '.png'}
VIDEO_EXT = {'.mp4', '.mov', '.m4v', '.mkv', '.webm'}
RIGHTS = ('may_reconstruct', 'may_publish_scene', 'property_and_occupant_authority',
          'no_phi', 'faces_and_plates_cleared')
TOOLS = Path('/home/ainur/Apps/.tools')
TOOL_HOST = 'ainur-shipleg'
SSH = ('ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=6', TOOL_HOST)
DAIN_ENV = Path('/home/ainur/twothumbs/ops/dainbot-deploy/dainbot-app.env')


def dain_token():
    token = os.environ.get('MCP_INTERNAL_SHARED_SECRET')
    if token:
        return token
    # Same local secret source used by the fleet's Dain ops-alert jobs.
    for line in DAIN_ENV.read_text().splitlines():
        if line.startswith('MCP_INTERNAL_SHARED_SECRET='):
            return line.partition('=')[2].strip().strip('"\'')
    raise RuntimeError('Dain ops-alert token unavailable')


def alert_real_submission(row, work, check=False):
    if row['test_submission'] or (work / 'dain-alert-sent.json').exists():
        return
    work.mkdir(parents=True, exist_ok=True)
    drill = row.get('alert_drill') is True
    title = ('DRILL: synthetic splat intake alert; no customer submission' if drill else
             ('Real splat submission ready for review' if check
              else 'Real splat submission staged for deployment'))
    payload = {'source': 'splat-intake', 'severity': 'warning',
               'title': title,
               'detail': ('Deliberate alert delivery test; no customer action or deployment. ' if drill else '') +
                         f"scene={row['id']}; " +
                         (f"video={row['source_video']}; frames={row.get('extracted_frame_count', 'pending')}; "
                          if row.get('input_kind') == 'video' else f"photos={row['photo_count']}; ") +
                         (f"drop={row['drop']}; manual full run required" if check
                          else f"receipt={work / 'receipt.json'}")}
    request = urllib.request.Request(
        os.environ.get('DAIN_OPS_ALERT_URL', 'https://app.dainbot.com/api/ops-alert'),
        data=json.dumps(payload).encode(), method='POST',
        headers={'Authorization': 'Bearer ' + dain_token(),
                 'Content-Type': 'application/json',
                 'User-Agent': 'nomoi-founder-broker/1.0'})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status != 200:
                raise RuntimeError(f'Dain ops-alert HTTP {response.status}')
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'Dain ops-alert failed for {row["id"]}: HTTP {exc.code}') from exc
    except Exception as exc:
        raise RuntimeError(f'Dain ops-alert failed for {row["id"]}: {type(exc).__name__}') from exc
    (work / 'dain-alert-sent.json').write_text(json.dumps({
        'scene': row['id'], 'sent_utc': dt.datetime.now(dt.timezone.utc).isoformat()}) + '\n')


def run(*args):
    subprocess.run([str(x) for x in args], check=True)


def remote(*args):
    """Run a fixed command on the configured Beelink SSH host."""
    command = ' '.join(shlex.quote(str(x)) for x in args)
    return subprocess.run([*SSH, command], check=True, capture_output=True, text=True).stdout.strip()


def check_remote_tools():
    for tool in ('quincunx-run', 'ply-to-splat', 'runpod-gaussian-train', 'cred-resolve'):
        try:
            remote('test', '-x', TOOLS / tool)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f'Beelink tool check failed over SSH ({TOOL_HOST}, {tool}): '
                f'{exc.stderr.strip() or f"exit {exc.returncode}"}'
            ) from exc


def validate(drop):
    submission = drop / 'submission.json'
    if submission.is_symlink() or not submission.is_file():
        raise ValueError('regular submission.json required')
    data = json.loads(submission.read_text())
    if not isinstance(data, dict):
        raise ValueError('submission must be an object')
    media = sorted(p for p in drop.iterdir() if p.suffix.lower() in IMAGE_EXT | VIDEO_EXT)
    photos = [p for p in media if p.suffix.lower() in IMAGE_EXT]
    videos = [p for p in media if p.suffix.lower() in VIDEO_EXT]
    if videos:
        if len(videos) != 1 or photos:
            raise ValueError('video submission requires exactly one media source')
        kind, sources = 'video', videos
        if data.get('owns_or_licensed_video') is not True:
            raise ValueError('confirmed owns_or_licensed_video=true required before processing')
        video = videos[0]
        if video.is_symlink() or not video.is_file() or video.stat().st_size == 0:
            raise ValueError(f'invalid video: {video.name}')
        try:
            with video.open('rb') as stream:
                if not stream.read(1):
                    raise ValueError('empty video')
        except OSError as exc:
            raise ValueError(f'unreadable video: {video.name}') from exc
    else:
        kind, sources = 'photos', photos
        if data.get('owns_or_licensed_photos') is not True:
            raise ValueError('confirmed owns_or_licensed_photos=true required before processing')
    for key in RIGHTS:
        if data.get(key) is not True:
            raise ValueError(f'confirmed {key}=true required before processing')
    if not isinstance(data.get('submitter'), str) or not data['submitter'].strip():
        raise ValueError('named submitter required')
    if not isinstance(data.get('name'), str) or not 1 <= len(data['name']) <= 80:
        raise ValueError('scene name required (1-80 characters)')
    if not isinstance(data.get('rights_statement'), str) or not data['rights_statement'].strip():
        raise ValueError('written rights statement required')
    if kind == 'photos':
        if len(photos) < 15:
            raise ValueError(f'15 photos minimum; found {len(photos)}')
        for photo in photos:
            if photo.is_symlink() or not photo.is_file() or photo.stat().st_size == 0:
                raise ValueError(f'invalid photo: {photo.name}')
            try:
                with Image.open(photo) as image:
                    image.verify()
            except Exception as exc:
                raise ValueError(f'unreadable photo: {photo.name}') from exc
    return data, kind, sources


def prepare_source(drop, kind, sources, work):
    source = work / 'source'
    images = source / 'images'
    images.mkdir(parents=True)
    if kind == 'video':
        run('ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', sources[0],
            '-vf', 'fps=2,scale=1280:-2', '-frames:v', '120', '-q:v', '3',
            images / '%04d.jpg')
        frame_count = len(list(images.glob('*.jpg')))
        if frame_count < 8:
            raise ValueError(f'Need at least 8 overlapping views; got {frame_count}')
    else:
        for photo in sources:
            shutil.copy2(photo, images / photo.name)
        frame_count = None
    supplied = drop / 'sparse' / '0'
    if kind == 'photos' and all((supplied / name).is_file() for name in ('cameras.bin', 'images.bin', 'points3D.bin')):
        shutil.copytree(drop / 'sparse', source / 'sparse')
    else:
        database = work / 'colmap.db'
        cpu_features = ('--SiftExtraction.use_gpu', '0') if kind == 'video' else ()
        cpu_matching = ('--SiftMatching.use_gpu', '0') if kind == 'video' else ()
        run('colmap', 'feature_extractor', '--database_path', database,
            '--image_path', images, '--ImageReader.single_camera', '1', *cpu_features)
        run('colmap', 'exhaustive_matcher', '--database_path', database, *cpu_matching)
        sparse = source / 'sparse'
        sparse.mkdir()
        mapper_threads = ('--Mapper.num_threads', '8') if kind == 'video' else ()
        run('colmap', 'mapper', '--database_path', database, '--image_path', images,
            '--output_path', sparse, *mapper_threads)
        if kind == 'video':
            names = ('cameras.bin', 'images.bin', 'points3D.bin')
            models = [p for p in sparse.iterdir() if p.is_dir() and
                      all((p / name).is_file() for name in names)]
            if not models:
                raise RuntimeError('COLMAP registered no complete model')
            best = max(models, key=lambda p: (p / 'points3D.bin').stat().st_size)
            if best.name != '0':
                zero = sparse / '0'
                if zero.exists():
                    shutil.rmtree(zero)
                best.rename(zero)
    model = source / 'sparse' / '0'
    if not all((model / name).is_file() for name in ('cameras.bin', 'images.bin', 'points3D.bin')):
        raise RuntimeError('COLMAP did not produce one complete sparse/0 model')
    # images.bin starts with COLMAP's little-endian uint64 registered-image count.
    # Supplied sparse models need no COLMAP executable on the dispatch host.
    with (model / 'images.bin').open('rb') as binary:
        header = binary.read(8)
    if len(header) != 8:
        raise RuntimeError('COLMAP images.bin is truncated')
    registered = struct.unpack('<Q', header)[0]
    if registered < 8:
        raise RuntimeError('fewer than 8 registered camera views; stop before paid training')
    return source, registered, frame_count


def process(drop, args):
    data, kind, sources = validate(drop)
    slug = re.sub(r'[^a-z0-9-]+', '-', drop.name.lower()).strip('-')[:50]
    if not slug:
        raise ValueError('drop folder needs a usable name')
    scene_id = 'upload-' + slug
    manifest_path = args.repo / 'submitted-scenes.json'
    manifest = json.loads(manifest_path.read_text())
    if any(row['id'] == scene_id for row in manifest):
        if not args.check:
            for row in manifest:
                if row['id'] == scene_id and (args.work / slug / 'receipt.json').exists():
                    alert_real_submission(row, args.work / slug)
        print(json.dumps({'drop': str(drop), 'scene': scene_id, 'status': 'already_staged'}))
        return
    work = args.work / slug
    if work.exists():
        raise ValueError('work folder already exists; inspect prior run before retry')
    if args.check:
        alert_real_submission({'id': scene_id, 'input_kind': kind,
                               'photo_count': len(sources) if kind == 'photos' else None,
                               'source_video': sources[0].name if kind == 'video' else None,
                               'test_submission': data.get('test_submission') is True,
                               'alert_drill': data.get('alert_drill') is True,
                               'drop': str(drop)}, args.work / 'check-alerts' / slug, check=True)
        check_remote_tools()
        print(json.dumps({'drop': str(drop), 'scene': scene_id,
                          **({'photos': len(sources)} if kind == 'photos' else
                             {'input_kind': 'video', 'source_video': sources[0].name}),
                          'rights_confirmed': True, 'test': data.get('test_submission') is True,
                          'remote_tools': TOOL_HOST}))
        return
    check_remote_tools()
    work.mkdir(parents=True)
    source, registered, frame_count = prepare_source(drop, kind, sources, work)
    remote_work = remote('mktemp', '-d', '/tmp/splat-intake-ssh-XXXXXXXX')
    remote_source = remote_work + '/source'
    remote_ply = remote_work + '/trained.ply'
    remote_asset = remote_work + '/trained.splat'
    run('scp', '-r', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=6',
        source, f'{TOOL_HOST}:{remote_source}')
    spec = work / 'train.spec'
    train_spec = {'source': remote_source, 'cap_aed': 10,
                  'output': remote_ply, 'dry_run': False}
    if args.data_center_ids:
        train_spec['data_center_ids'] = args.data_center_ids
    spec.write_text('RUNPOD_TRAIN: ' + json.dumps(train_spec) + '\n')
    run('scp', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=6',
        spec, f'{TOOL_HOST}:{remote_work}/train.spec')
    run(*SSH, ' '.join(shlex.quote(str(x)) for x in
                     (TOOLS / 'quincunx-run', 'splat-' + slug, remote_work + '/train.spec')))
    ply_bytes = remote('stat', '-c', '%s', remote_ply)
    if not ply_bytes.isdigit() or int(ply_bytes) < 1024:
        raise RuntimeError('trainer returned without a valid PLY')
    run(*SSH, ' '.join(shlex.quote(str(x)) for x in
                     (TOOLS / 'ply-to-splat', remote_ply, remote_asset)))
    asset = args.repo / 'submitted' / (scene_id + '.splat')
    asset.parent.mkdir(exist_ok=True)
    run('scp', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=6',
        f'{TOOL_HOST}:{remote_asset}', asset)
    if asset.stat().st_size < 32 or asset.stat().st_size % 32:
        raise RuntimeError('converted splat invalid')
    row = {'id': scene_id, 'name': data['name'], 'submitter': data['submitter'],
           'provenance': data['rights_statement'], 'trained_reconstruction': True,
           'test_submission': data.get('test_submission') is True,
           'alert_drill': data.get('alert_drill') is True,
           **({'photo_count': len(sources)} if kind == 'photos' else
              {'input_kind': 'video', 'source_video': sources[0].name,
               'extracted_frame_count': frame_count}),
           'registered_count': registered,
           'asset': 'submitted/' + asset.name, 'bytes': asset.stat().st_size,
           'created_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    manifest.append(row)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    (work / 'receipt.json').write_text(json.dumps(row, indent=2) + '\n')
    alert_real_submission(row, work)
    print(json.dumps({'scene_url': f'https://nomoi.ai/splat-demo/?scene={scene_id}',
                      'status': 'staged_in_repo; deploy required', 'receipt': str(work / 'receipt.json')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inbox', type=Path, required=True, help='local synced Drive/Dain drop folder')
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true', help='validate rights and count without copying or spending')
    parser.add_argument('--data-center-ids', help='explicit RunPod data center ID for this dispatch')
    args = parser.parse_args()
    if args.data_center_ids and not re.fullmatch(r'[A-Za-z0-9-]+', args.data_center_ids):
        parser.error('--data-center-ids must be one data center ID')
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

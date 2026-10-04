# Splat photo drop

This is a manual trigger for one locally synced Google Drive folder or a Dain WhatsApp attachment bundle. The sync/attachment bridge must first place each bundle in its own child directory under `--inbox`. No Google Drive or WhatsApp account is connected by this script.

The host needs Python Pillow for image decoding checks, COLMAP for unposed photos, and the existing Beelink `.tools` trainer, quincunx, credential and converter executables.

Put at least 15 overlapping JPG/PNG photos of one physical scene and `submission.json` in a new child folder. If a valid COLMAP `sparse/0/` binary model already exists, include it; otherwise the script runs the installed COLMAP pose solve. An example confirmation record:

```json
{
  "name": "My living room",
  "submitter": "Named photo owner",
  "rights_statement": "My own photos; I authorize this public reconstruction.",
  "owns_or_licensed_photos": true,
  "may_reconstruct": true,
  "may_publish_scene": true,
  "property_and_occupant_authority": true,
  "no_phi": true,
  "faces_and_plates_cleared": true,
  "test_submission": false
}
```

The submitter must personally confirm every rights field. Never republish someone else's listing photos without permission. Keep inputs free of PHI; confirm property and occupant authority; clear faces and licence plates before a public link. The check is an attestation gate, not an automated visual privacy review.

On the Beelink host with the existing `.tools` rail installed:

```sh
python3 tools/splat-intake.py --inbox /path/to/synced/splat-drops --work /path/to/splat-work --check
python3 tools/splat-intake.py --inbox /path/to/synced/splat-drops --work /path/to/splat-work
```

The second command invokes the existing `RUNPOD_TRAIN:` quincunx branch at 10 AED, converts its PLY with `.tools/ply-to-splat`, and stages a named picker entry in `submitted-scenes.json`. Commit and deploy the generated asset and manifest to make the URL public. Keep the receipt and rights record. The scene is labeled as a trained image-based reconstruction and as a test if `test_submission` is true. A failed work directory is held for inspection; use a fresh folder name for a new attempt so a paid job cannot be repeated accidentally.

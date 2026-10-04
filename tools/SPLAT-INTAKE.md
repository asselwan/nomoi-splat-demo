# Splat photo drop

The scheduled `--check` poll validates drops in a local inbox every 20 minutes once its schedule request is verified. A full training run remains an explicit dispatch. The sync/attachment bridge must first place each bundle in its own child directory under `--inbox`. No Google Drive or WhatsApp account is connected by this script.

The intake host needs Python Pillow for image decoding checks and COLMAP for unposed photos. Its SSH config must provide the existing `ainur-shipleg` alias for Beelink (`ainur@100.123.16.59`), with batch authentication. The trainer, quincunx, credential and converter executables run on Beelink, where the live `.tools` rail exists. Source files are copied there with `scp`; the converted asset is copied back to this checkout.

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

On a host that can reach the configured Beelink SSH alias:

```sh
python3 tools/splat-intake.py --inbox /path/to/synced/splat-drops --work /path/to/splat-work --check
python3 tools/splat-intake.py --inbox /path/to/synced/splat-drops --work /path/to/splat-work
```

The second command invokes the existing `RUNPOD_TRAIN:` quincunx branch at 10 AED, converts its PLY with `.tools/ply-to-splat`, and stages a named picker entry in `submitted-scenes.json`. Commit and deploy the generated asset and manifest to make the URL public. Keep the receipt and rights record. The scene is labeled as a trained image-based reconstruction and as a test if `test_submission` is true. A failed work directory is held for inspection; use a fresh folder name for a new attempt so a paid job cannot be repeated accidentally.

For a real (`test_submission` not true) full run, successful staging sends a Dain ops-alert naming the scene and receipt. The alert uses `MCP_INTERNAL_SHARED_SECRET` from the environment or the fleet's local Dain environment file. An alert failure makes the run fail visibly; rerunning a staged scene retries the alert without repeating training. A validated real drop found by `--check` also sends one deduplicated Dain alert asking for manual dispatch. Test submissions never page Dain.

The aule standing-poll request and current verification state are in [`SPLAT-INTAKE-CRON.md`](SPLAT-INTAKE-CRON.md). The inbox and local checkout paths in that request are durable, but there is no automatic attachment sync yet. `--check` does not train, convert, publish, or send a Dain completion alert; it sends a discovery alert for a new valid real drop.

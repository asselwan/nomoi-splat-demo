# Splat intake standing poll request

Status on 2026-10-04 UTC: **submitted to D-schedule-request-rail; installation unverified**. The rail validated the request and its doctrine lint, but returned `rejected` because it could not read the live aule crontab (`crontab -l`: `crontabs/ainur/: fopen: Permission denied`). Its line is present in the aule manifest; that alone is not proof it is scheduled. The same command was run manually and wrote a fresh successful outcome receipt with `no submissions`. The inbox has no attachment sync.

Request: `/home/ainur/Apps/.ainur/schedule-queue/splat-intake-check.json`  
Rail result: `/home/ainur/Apps/.ainur/schedule-queue/splat-intake-check.result.json`  
Outcome receipt: `/home/ainur/Apps/.ainur/outcome-logs/splat-intake-check.json`

Exact requested UTC cron line:

```cron
*/20 * * * * /usr/bin/flock -n /tmp/splat-intake-check.lock /usr/bin/nice -n 10 /home/ainur/Apps/.tools/schedule-receipt-run splat-intake-check -- /usr/bin/python3 /home/ainur/Apps/nomoi-splat-demo/tools/splat-intake.py --inbox /home/ainur/Apps/.ainur/splat-intake/inbox --work /home/ainur/Apps/.ainur/splat-intake/work --repo /home/ainur/Apps/nomoi-splat-demo --check >> /home/ainur/Apps/.ainur/outcome-logs/splat-intake-check.log 2>&1
```

The poll runs `tools/splat-intake.py --check` only. It validates rights and photos when a drop exists; it does not start paid training or publish. A newly validated real drop sends one Dain discovery alert for manual review. The request's aule inbox is `/home/ainur/Apps/.ainur/splat-intake/inbox`. A real full-processing invocation alerts Dain after staging via the fleet ops-alert API. The schedule rail must verify the live crontab and a fresh first-run receipt before this can be called active.

# Access-point reboot

## Design

The package provides an opt-in daily AP reboot facility. Administrators copy
the example profile to `/etc/iserv/server-unifios/ap-reboot.env`, set mode
`0600`, provide a UniFi controller API key, and set `enabled=true`.

`server-unifios-reboot-aps` uses the controller's local Network API with
`X-API-KEY` authentication. It lists devices from
`/proxy/network/api/s/<site>/stat/device`, selects `uap` devices whose names
start with `name_prefix`, and requests each reboot through
`/proxy/network/api/s/<site>/cmd/devmgr`. It neither needs PHP/Composer nor an
AP SSH key.

An absent or disabled profile is a successful no-op. Failed controller
requests fail the job. The profile supports `base_url` (default
`https://$(hostname -f)`), `site` (default `default`), and `name_prefix`
(default `UAP-`).

## Implementation plan

1. Add a package-install regression test that expects the reboot script and
   root-only example profile, and uses a mocked `curl` to cover disabled
   operation and prefix-filtered reboot requests.
2. Add the runner, daily cron wrapper, profile example, and `iservchk`
   directory provisioning. The runner accepts `PROFILE_FILE` only to make the
   regression test isolated; production uses the root-only profile path.
3. Document setup, API-key handling, opt-in scheduling, and the exact script
   path in the README.
4. Run the package-install test, shell syntax checks, and `iservmake run_tools`.

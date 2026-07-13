# PSK Profile Rotation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rotate opted-in PSK profiles daily while securely retaining and rendering non-rotating profiles.

**Architecture:** Store each active PSK outside nginx's public alias.  Split controller mutation from public-asset rendering so the daily runner can rotate only opted-in profiles while regenerating static assets from saved state for all other profiles.  An explicit `--force-rotate` list overrides `rotate=false` for manual rotations.

**Tech Stack:** POSIX shell, Bash, `iservchk`, nginx IConf shell generator, `qrencode`, Debian packaging tests.

## Global Constraints

- `rotate=true` profiles rotate in `cron/daily.d/server-unifios-update`.
- `rotate=false` profiles keep their saved PSK and only render from it.
- Private PSK state must never be inside `/var/lib/iserv/server-unifios/psk/<profile>`.
- `--force-rotate profile1,profile2` is the only manual override for disabled profiles.

---

### Task 1: Add private PSK state and decouple rendering

**Files:**
- Modify: `lib/server-unifios/rotate_wlan_psk`
- Create: `lib/server-unifios/render_wlan_psk`
- Modify: `iservchk/40unifios/40server-unifios`
- Test: `tests/package-install.sh`

**Interfaces:**
- Consumes: `NEWPSK`, `TARGET_DIR`, `UNIFI_SSID`, template/style environment variables.
- Produces: `render_wlan_psk <psk>` which creates `index.html`, `qrcode.png`, and `style.css` without contacting UniFi.

- [ ] Write a package-test assertion that `render_wlan_psk` is executable and that `iservchk` creates `/var/lib/iserv/server-unifios/psk-state` mode 0700.
- [ ] Run `tests/package-install.sh`; expect failure because the renderer and state directory do not exist.
- [ ] Make `rotate_wlan_psk` call `SET_PSK_COMMAND`, write `NEWPSK` to a mode-0600 state file, then invoke `render_wlan_psk "$NEWPSK"`.
- [ ] Implement `render_wlan_psk` to contain the existing QR/template/style operations and no controller command.
- [ ] Add `MkDir 0700 root:root /var/lib/iserv/server-unifios/psk-state` to IConf.
- [ ] Re-run `tests/package-install.sh` and shell syntax checks; expect success.

### Task 2: Select automatic and forced profiles

**Files:**
- Modify: `lib/server-unifios/server-unifios-rotate-psk`
- Modify: `cron/daily.d/server-unifios-update`
- Test: `tests/package-install.sh`

**Interfaces:**
- Consumes: profile `rotate`, `name`, controller settings, and optional `--force-rotate name[,name...]`.
- Produces: a daily invocation that rotates only `rotate=true` profiles and re-renders saved disabled profiles.

- [ ] Write mocked runner tests covering `rotate=true`, saved `rotate=false`, missing saved state warning, and forced disabled-profile rotation.
- [ ] Run the test; expect the current runner to fail because it gates on `enabled` and always creates a new key.
- [ ] Parse exactly one `--force-rotate` option, validate comma-separated profile names, and fail for unknown names.
- [ ] For normal processing, call the rotation helper only for `rotate=true`; otherwise read the private state and call the renderer, warning when state is absent.
- [ ] Append `/usr/lib/iserv/server-unifios/server-unifios-rotate-psk` after the controller restart in the existing daily update job.
- [ ] Re-run mocked tests, `tests/package-install.sh`, and `sh -n`/`bash -n` checks; expect success.

### Task 3: Keep all configured profiles publishable and document controls

**Files:**
- Modify: `iconf/etc/nginx/server-iserv/41server-unifios_psk.sh`
- Modify: `iservchk/40unifios/40server-unifios`
- Modify: `psk-profiles.d/guest.env.example`
- Modify: `README.md`
- Modify: `config/80server-unifios`
- Test: `tests/package-install.sh`

**Interfaces:**
- Consumes: valid profile names independent of `rotate`.
- Produces: nginx locations/directories for every valid profile and administrator documentation for daily/manual semantics.

- [ ] Add tests proving a valid `rotate=false` profile yields an nginx location and public directory.
- [ ] Run the tests; expect failure because nginx and IConf currently skip false profiles.
- [ ] Remove rotation/enable gating from nginx and IConf profile directory loops while retaining name validation and access policy generation.
- [ ] Replace `enabled` with `rotate` in the example profile and explain that false preserves state.
- [ ] Replace the obsolete README statement that rotation is separately scheduled with the daily automatic behaviour and the exact `--force-rotate guest,staff` example.
- [ ] Regenerate translations if the config description changes, then run `iservmake run_tools` and the focused package checks.

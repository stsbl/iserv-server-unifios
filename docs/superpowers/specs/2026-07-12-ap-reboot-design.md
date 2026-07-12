# UniFi AP reboot feature

## Goal

Provide an opt-in, daily controller-managed reboot for selected UniFi access
points without shipping controller credentials or SSH keys in the package.

## Configuration

`iservchk` creates `/etc/iserv/server-unifios/ap-reboot.env`'s parent
directory with root-only permissions. The package installs a documented example
profile below `/usr/share/doc/stsbl-iserv-server-unifios/examples/`.

The administrator copies the example to `/etc/iserv/server-unifios/ap-reboot.env`,
sets mode `0600`, and configures:

- `enabled=true` to opt in; omitted or any other value disables the feature.
- `api_key` as the required UniFi controller API key.
- `site`, defaulting to `default`.
- `name_prefix`, defaulting to `UAP-`.
- `base_url`, defaulting to `https://$(hostname -f)`.

The profile is never generated, committed, or exposed through nginx.

## Runtime

`/usr/lib/iserv/server-unifios/server-unifios-reboot-aps` exits successfully
when the profile is absent or disabled. Otherwise, it lists devices through the
controller API, selects access points whose names start with `name_prefix`, and
sends one restart command per selected device through the controller API. It
uses `curl` and `jq`, avoids PHP/Composer, and does not use AP SSH credentials.

The package's daily cron entry invokes this script after the regular UniFi
update job. Reboots are independent of image updates and occur only after an
administrator explicitly enables the profile.

## Failure handling

The script validates required configuration before making API calls. A failed
device listing or reboot command exits non-zero so cron records the failure.
It processes matching devices sequentially and reports the affected AP name to
standard error. An empty match set succeeds without action.

## Tests

The package installation regression test proves the script and example profile
are installed at their intended locations. A shell test with mocked `curl`
will cover disabled operation, filtering by name prefix, and API reboot command
generation.

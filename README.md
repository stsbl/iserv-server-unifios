# IServ UniFi OS Server

`stsbl-iserv-server-unifios` runs
[lemker/unifi-os-server](https://github.com/lemker/unifi-os-server) as an
IServ-managed Docker Compose service.  It also contains a configurable WLAN
PSK rotation helper which renders a QR-code and HTML page for every enabled
profile.

## Installation and lifecycle

Install the package on the UniFi host and apply the complete IServ
configuration:

```sh
apt install stsbl-iserv-server-unifios
iservchk
```

The managed Compose manifest is supplied by the pinned `docker/unifi-os-server`
Git submodule and installed at
`/usr/share/iserv/server-unifios/docker/unifi-os-server/docker-compose.yaml`;
it must not be copied to or edited in `/opt`.  Its generated environment is
`/var/lib/iserv/server-unifios/docker-compose.env` and derives `HOST` from the
`Hostname` configuration supplied by `iserv-config-file`.

The `iserv-server-unifios.service` systemd unit starts and stops the Compose
stack.  Persistent container state deliberately remains outside the package:

- `/var/lib/iserv/server-unifios/{persistent,data,srv,unifi,mongodb,rabbitmq-ssl}`
- `/var/log/iserv/server-unifios`

iservchk creates these bind-mount directories when absent, but deliberately
does not reconcile their owner or mode afterwards: the container owns and
changes permissions within this state.

The Compose configuration also mounts `/sys/fs/cgroup` read/write because
UniFi OS uses systemd inside the container.  It exposes the controller GUI on
TCP 11443 and the upstream adoption, STUN, portal, AQMPS and discovery ports.
The package-owned FERM fragment configures the `br-unifi` Docker bridge,
masquerading for `198.18.2.0/24`, and the controller's required TCP/UDP ports.

Nginx terminates the public TLS connection and reverse-proxies `/` to the
container on `https://127.0.0.1:11443`, including WebSocket upgrade headers.
It generates a QR-code location `/psk/<profile>/` for every enabled PSK
profile.  A profile using `access_mode=cidr` is protected by its own CIDR
allowlist; no PSK directories or locations are hard-coded in the package.

The daily IServ cron job pulls `ghcr.io/lemker/unifi-os-server:latest` and
runs Compose reconciliation. A new image may therefore recreate the controller
during that run.

## WLAN PSK profiles

Profile definitions are root-only shell environment files in:

```
/etc/iserv/server-unifios/psk-profiles.d/*.env
```

Start with the installed example:

```sh
install -m 0600 \
  /usr/share/doc/stsbl-iserv-server-unifios/examples/psk-profiles.d/guest.env.example \
  /etc/iserv/server-unifios/psk-profiles.d/guest.env
editor /etc/iserv/server-unifios/psk-profiles.d/guest.env
```

Each profile supports the following fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `enabled` | yes | Set to `true` to rotate the profile. |
| `name` | yes | Output directory name below `psk/`; use letters, digits, `_` and `-`. |
| `site` | yes | UniFi site, usually `default`. |
| `wlan_name` | yes | Exact UniFi WLAN name to update. |
| `api_key` | one auth method | Preferred UniFi API key; keep it only in this mode-0600 file. |
| `username` / `password` | one auth method | Alternative UniFi login when `api_key` is empty; both fields are required together. |
| `base_url` | no | UniFi controller URL; defaults to `https://$(hostname -f)`. |
| `ssid` | no | SSID encoded in the QR code; defaults to `wlan_name`. |
| `title` | no | Browser page title; defaults to `IServ Gast-WLAN-Schlüssel`. |
| `notice` | no | Text rendered in the generated HTML page. |
| `access_mode` / `access_value` | no | Web access policy. Use `cidr` and a whitespace-separated IPv4/IPv6 CIDR allowlist. |

Do not commit profile files or API keys.  The generated public artifacts are
written to `/var/lib/iserv/server-unifios/psk/<name>/` as `index.html`,
`qrcode.png`, and `style.css`.

Run a rotation manually after changing a profile:

```sh
/usr/lib/iserv/server-unifios/server-unifios-rotate-psk
```

PSK rotation is intentionally not part of the daily UniFi update job. Schedule
this command separately if automatic rotation is wanted.

## Source provenance

The upstream container Dockerfile, Compose manifest, and entrypoint are pinned
as the `docker/unifi-os-server` submodule on the `adoptions` branch of
`git@git.jacobi-bs.de:sysadmin/unifi-os-server.git`.  The historical
WLAN rotator repository is included under `psk-rotator/` with its Git history;
the package runtime copies live in `lib/`.

## Development

Useful local checks:

```sh
sh -n cron/daily.d/server-unifios-update lib/server-unifios/server-unifios-rotate-psk
bash -n lib/server-unifios/unifi-set-psk lib/server-unifios/rotate_wlan_psk
HOST=unifi.example.invalid docker compose -f docker/docker-compose.yaml config
dpkg-buildpackage -us -uc -b
```

The package build requires `dh-sequence-iserv` and `dh-sequence-stsbl`.

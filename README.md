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
IServ configuration.

The `iserv-server-unifios.service` systemd unit starts and stops the Compose
stack.  Persistent container state deliberately remains outside the package:

- `/var/lib/iserv/server-unifios/{persistent,data,srv,unifi,mongodb,rabbitmq-ssl}`
- `/var/log/iserv/server-unifios`

The Compose configuration also mounts `/sys/fs/cgroup` read/write because
UniFi OS uses systemd inside the container.  It exposes the controller GUI on
TCP 11443 and the upstream adoption, STUN, portal, AQMPS and discovery ports.
The package-owned FERM fragment configures the `br-unifi` Docker bridge,
masquerading for `198.18.2.0/24`, and the controller's required TCP/UDP ports.

Nginx terminates the public TLS connection and reverse-proxies `/` to the
container on `https://127.0.0.1:11443`, including WebSocket upgrade headers.
It also serves the generated QR-code pages at `/psk/guest/` and `/psk/office/`
from the managed PSK directories.  Their current STSBL network allowlists are
rendered by the package IConf fragment.

The daily IServ cron job pulls `ghcr.io/lemker/unifi-os-server:latest`, runs
Compose reconciliation, and then rotates enabled PSK profiles.  A new image
may therefore recreate the controller during that run.

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
| `api_key` | yes | UniFi API key; keep it only in this mode-0600 file. |
| `base_url` | no | UniFi controller URL; defaults to `https://$(hostname -f)`. |
| `ssid` | no | SSID encoded in the QR code; defaults to `wlan_name`. |
| `notice` | no | Text rendered in the generated HTML page. |
| `schedule` | no | Reserved per-profile schedule metadata; profiles currently run in the daily package job. |
| `access_mode` / `access_value` | no | Reserved access-policy metadata for generated web-serving configuration. |

Do not commit profile files or API keys.  The generated public artifacts are
written to `/var/lib/iserv/server-unifios/psk/<name>/` as `index.html`,
`qrcode.png`, and `style.css`.

Run a rotation manually after changing a profile:

```sh
/usr/lib/iserv/server-unifios/server-unifios-rotate-psk
```

## Source provenance

The upstream container Dockerfile, Compose manifest, and entrypoint are pinned
as the `docker/unifi-os-server` submodule on the `adoptions` branch of
`git@git.jacobi-bs.de:sysadmin/unifi-os-server.git`.  The historical
WLAN rotator repository is included under `psk-rotator/` with its Git history;
the package runtime copies live in `lib/`.

## Development

Useful local checks:

```sh
sh -n cron/daily.d/server-unifios-update lib/server-unifios-rotate-psk
bash -n lib/unifi-set-psk lib/rotate_wlan_psk
HOST=unifi.example.invalid docker compose -f docker/docker-compose.yaml config
dpkg-buildpackage -us -uc -b
```

The package build requires `dh-sequence-iserv` and `dh-sequence-stsbl`.

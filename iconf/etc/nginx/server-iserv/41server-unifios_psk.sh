#!/bin/sh
set -eu

profiles=/etc/iserv/server-unifios/psk-profiles.d
[ -d "$profiles" ] || exit 0

for profile in "$profiles"/*.env; do
  [ -f "$profile" ] || continue
  unset enabled name access_mode access_value
  . "$profile"
  [ "${enabled:-false}" = true ] || continue
  case "${name:-}" in
    ''|*[!A-Za-z0-9_-]*) continue ;;
  esac

  printf 'location /psk/%s {\n' "$name"
  printf '  alias /var/lib/iserv/server-unifios/psk/%s/;\n' "$name"
  printf '  index index.html;\n'
  case "${access_mode:-cidr}" in
    cidr)
      printf '  allow 127.0.0.0/8;\n  allow ::1;\n'
      for cidr in ${access_value:-}; do
        printf '  allow %s;\n' "$cidr"
      done
      printf '  deny all;\n'
      ;;
    *)
      # Do not publish a profile until its selected authentication backend is rendered.
      printf '  deny all;\n'
      ;;
  esac
  printf '}\n\n'
done


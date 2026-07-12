#!/bin/sh
set -eu

package=stsbl-iserv-server-unifios
package_dir=debian/$package

rm -rf "$package_dir" debian/.debhelper
dh_iservinstall -p"$package"

test -f "$package_dir/usr/lib/iserv/server-unifios/rotate_wlan_psk"
test -f "$package_dir/usr/share/iserv/$package/template.html"
test -f "$package_dir/usr/share/iserv/$package/style.css"

grep -Fqx "  export TEMPLATE_FILE=/usr/share/iserv/$package/template.html" \
  lib/server-unifios/server-unifios-rotate-psk
grep -Fqx "  export STYLE_FILE=/usr/share/iserv/$package/style.css" \
  lib/server-unifios/server-unifios-rotate-psk
grep -Fq '<title>%title%</title>' "$package_dir/usr/share/iserv/$package/template.html"
grep -Fq 's|%title%|$TITLE|g' \
  lib/server-unifios/rotate_wlan_psk
if grep -Fq server-unifios-rotate-psk cron/daily.d/server-unifios-update; then
  exit 1
fi
test -x "$package_dir/usr/lib/iserv/server-unifios/server-unifios-rotate-psk"

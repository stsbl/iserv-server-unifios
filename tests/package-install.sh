#!/bin/sh
set -eu

package=stsbl-iserv-server-unifios
package_dir=debian/$package

rm -rf "$package_dir" debian/.debhelper
dh_iservinstall -p"$package"

test -f "$package_dir/usr/lib/iserv/server-unifios/rotate_wlan_psk"
test -x "$package_dir/usr/lib/iserv/server-unifios/server-unifios-reboot-aps"
test -f "$package_dir/usr/share/doc/$package/examples/ap-reboot.env.example"
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

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/bin"
cat > "$tmp/bin/curl" <<'EOF'
#!/bin/sh
case "$*" in
  *stat/device*)
    printf '%s\n' '{"data":[{"type":"uap","name":"UAP-library","mac":"aa:bb:cc:dd:ee:ff"},{"type":"uap","name":"other-ap","mac":"11:22:33:44:55:66"}]}'
    ;;
  *cmd/devmgr*)
    printf '%s\n' "$*" >> "$CURL_LOG"
    ;;
esac
EOF
chmod +x "$tmp/bin/curl"

printf '%s\n' 'enabled=false' > "$tmp/disabled.env"
PATH="$tmp/bin:$PATH" PROFILE_FILE="$tmp/disabled.env" CURL_LOG="$tmp/curl.log" \
  "$package_dir/usr/lib/iserv/server-unifios/server-unifios-reboot-aps"
test ! -e "$tmp/curl.log"

cat > "$tmp/enabled.env" <<'EOF'
enabled=true
api_key=test-api-key
base_url=https://unifi.example.invalid
site=default
name_prefix=UAP-
EOF
PATH="$tmp/bin:$PATH" PROFILE_FILE="$tmp/enabled.env" CURL_LOG="$tmp/curl.log" \
  "$package_dir/usr/lib/iserv/server-unifios/server-unifios-reboot-aps"
grep -Fq 'aa:bb:cc:dd:ee:ff' "$tmp/curl.log"
if grep -Fq '11:22:33:44:55:66' "$tmp/curl.log"; then
  exit 1
fi

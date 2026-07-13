# PSK profile rotation and rendering

## Goal

Allow every valid PSK profile to publish its protected web location while
controlling automatic key rotation per profile.  Previously generated PSKs
must remain private and be reusable to regenerate the public QR-code and HTML
assets.

## Profile behaviour

Profiles use a `rotate` boolean.  `rotate=true` enables automatic rotation in
the existing daily UniFi update job; `rotate=false` preserves the saved key.
The rotation setting does not disable a profile, its output directory, or its
nginx location.  Valid configured profiles always receive those resources.

## Private state and public artifacts

The active PSK is stored root-only below
`/var/lib/iserv/server-unifios/psk-state/<profile>`, outside nginx's aliased
directory.  The public directory remains
`/var/lib/iserv/server-unifios/psk/<profile>` and only contains rendered
`index.html`, `qrcode.png`, and `style.css`.

Rendering is separated from applying a new PSK to the controller.  A rotation
creates a key, applies it, saves it privately, and renders the public assets.
A non-rotating profile reads the saved key and renders assets without calling
the controller.  If its private state does not exist, processing emits a
warning; nginx configuration is still generated.

## Invocation

The existing daily update job invokes the profile runner after the controller
update.  With no options it rotates only profiles with `rotate=true` and
re-renders the public assets of profiles with `rotate=false` from their saved
private state.  A disabled profile receives a new key only through the
explicit manual forced-profile command.

`server-unifios-rotate-psk --force-rotate profile1,profile2` forces a new key
for exactly the comma-separated named profiles, including profiles whose
`rotate` flag is false.  Named profiles continue to use the normal validation
and controller credentials.  Unknown or malformed names are reported as
errors rather than silently ignored.

## Configuration and filesystem generation

`iservchk` creates the private state root and per-profile public directories
for every valid profile, regardless of `rotate`.  The nginx generator follows
the same rule, so disabling automatic rotation never removes a profile URL.

## Documentation and tests

The example profile and README explain `rotate`, the private-state behaviour,
the daily automatic path, and `--force-rotate`.  Regression tests cover:

- automatic rotation only for `rotate=true` profiles;
- rendering from a saved PSK for `rotate=false` profiles without controller
  mutation;
- a warning for missing state on a non-rotating profile;
- forced rotation of selected `rotate=false` profiles;
- nginx/iservchk generation for valid non-rotating profiles; and
- no PSK state file beneath the publicly aliased directory.

LOCALE_DISABLE_POOTLE_DOWNLOAD=1

DEPENDENCY_TARGETS += docker/unifi-os-server

docker/unifi-os-server:
	git submodule update --init docker/unifi-os-server

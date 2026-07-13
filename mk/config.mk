LOCALE_DISABLE_POOTLE_DOWNLOAD=1

DEPENDENCY_TARGETS += init_unifi_os_server

.PHONY: init_unifi_os_server
init_unifi_os_server:
	git submodule update --init docker/unifi-os-server

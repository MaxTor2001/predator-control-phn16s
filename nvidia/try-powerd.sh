#!/bin/bash
# Временно включить nvidia-powerd (Dynamic Boost) - до перезагрузки. Запуск: sudo nvidia/try-powerd.sh [stop]
set -e
cd "$(dirname "$0")"
policy=/etc/dbus-1/system.d/nvidia-dbus.conf

if [ "$1" = stop ]; then
	systemctl stop nvidia-powerd-test
	rm $policy
	systemctl reload dbus
	echo "nvidia-powerd остановлен, политика D-Bus удалена"
	exit
fi

install -m 644 nvidia-dbus.conf $policy
systemctl reload dbus
systemd-run --unit=nvidia-powerd-test /usr/bin/nvidia-powerd
sleep 3
systemctl status nvidia-powerd-test --no-pager | head -8
journalctl -u nvidia-powerd-test --no-pager | tail -8

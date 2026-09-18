#!/bin/bash
# Постоянно включить nvidia-powerd (Dynamic Boost). Запуск: sudo nvidia/install-powerd.sh [remove]
set -e
cd "$(dirname "$0")"
policy=/etc/dbus-1/system.d/nvidia-dbus.conf
unit=/etc/systemd/system/nvidia-powerd.service

if [ "$1" = remove ]; then
	systemctl disable --now nvidia-powerd
	rm $policy $unit
	systemctl daemon-reload
	systemctl reload dbus
	echo "nvidia-powerd отключён, юнит и политика D-Bus удалены"
	exit
fi

install -m 644 nvidia-dbus.conf $policy
install -m 644 /usr/share/doc/nvidia-kernel-common-*/nvidia-powerd.service $unit
systemctl reload dbus
systemctl daemon-reload
systemctl enable --now nvidia-powerd
sleep 3
systemctl status nvidia-powerd --no-pager | head -8
nvidia-smi --query-gpu=enforced.power.limit --format=csv

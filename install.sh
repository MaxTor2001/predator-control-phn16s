#!/bin/bash
# Установка/обновление пропатченного acer-wmi через DKMS и udev-правил. Запуск: sudo ./install.sh
set -e
cd "$(dirname "$0")"

pkg=acer-wmi-phn16s
ver=$(sed -n 's/^PACKAGE_VERSION="\(.*\)"/\1/p' driver/dkms.conf)

make -C driver clean
install -d /var/lib/dkms  # каталог пакета dkms; без него dkms падает с "No write access to DKMS tree"
for old in $(dkms status $pkg | sed -E 's|^[^/]+/([^,]+),.*|\1|' | sort -u); do
	dkms remove $pkg/$old --all
	rm -rf /usr/src/$pkg-$old
done
dkms add ./driver
dkms install $pkg/$ver

install -m 644 90-acer-fan.rules /etc/udev/rules.d/
udevadm control --reload

modprobe -r acer_wmi
modprobe acer_wmi
udevadm settle

dkms status $pkg
modinfo -n acer_wmi
ls -l /sys/class/hwmon/hwmon*/pwm* /sys/class/platform-profile/*/profile
cat /sys/firmware/acpi/platform_profile

#!/bin/bash
# Хук gamemode: start [режим] - запомнить режим мощности и включить указанный (по умолчанию Performance), end - вернуть прежний.
profile=$(grep -l acer-wmi /sys/class/platform-profile/*/name | xargs dirname)/profile
saved=$XDG_RUNTIME_DIR/predator-profile-before-game

if [ "$1" = start ]; then
	cat "$profile" > "$saved"
	echo "${2:-balanced-performance}" > "$profile"
else
	cat "$saved" > "$profile"
	rm "$saved"
fi

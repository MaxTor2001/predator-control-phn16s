#!/bin/bash
# Хук gamemode: start - запомнить режим мощности и включить Performance, end - вернуть прежний.
profile=$(grep -l acer-wmi /sys/class/platform-profile/*/name | xargs dirname)/profile
saved=$XDG_RUNTIME_DIR/predator-profile-before-game

if [ "$1" = start ]; then
	cat "$profile" > "$saved"
	echo balanced-performance > "$profile"
else
	cat "$saved" > "$profile"
	rm "$saved"
fi

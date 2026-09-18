#!/bin/bash
# Ярлык в меню приложений, иконка и хук gamemode для текущего пользователя. Запуск без sudo: ./install-user.sh
set -e
dir=$(dirname "$(readlink -f "$0")")
apps=~/.local/share/applications
icons=~/.local/share/icons/hicolor/scalable/apps

mkdir -p "$apps" "$icons"
cp "$dir/predator-control.svg" "$icons/"
sed "s|@DIR@|$dir|" "$dir/predator-control.desktop.in" > "$apps/predator-control.desktop"
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor
update-desktop-database "$apps"
[ -e ~/.config/gamemode.ini ] || sed "s|@DIR@|$dir|" "$dir/gamemode.ini.in" > ~/.config/gamemode.ini

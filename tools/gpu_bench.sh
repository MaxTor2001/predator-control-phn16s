#!/bin/bash
# Замер GPU под нагрузкой: мощность, лимит, частота, температура, скорость. Запуск: tools/gpu_bench.sh [секунды] [light|heavy]
seconds=${1:-70}
dir=$(dirname "$(readlink -f "$0")")
log=$(mktemp)

echo "nvidia-powerd: $(pgrep -x nvidia-powerd > /dev/null && echo запущен || echo не запущен), режим: $(cat /sys/firmware/acpi/platform_profile)"
uv run --no-project --with wgpu "$dir/gpu_load.py" "$seconds" ${2:-light} > "$log" 2>&1 &
load=$!

for t in $(seq 10 10 "$seconds"); do
	sleep 10
	temp=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader)
	echo "t=${t}с: $(nvidia-smi --query-gpu=pstate,clocks.gr,power.draw,enforced.power.limit --format=csv,noheader), ${temp}°C, CPU $(( $(cat /sys/class/hwmon/hwmon*/temp1_input | sort -n | tail -1) / 1000 ))°C"
	if [ "$temp" -gt 87 ]; then
		echo "GPU горячее 87°C - останавливаю нагрузку"
		kill $load
		break
	fi
done
wait $load 2>/dev/null
echo "--- скорость:"
cat "$log"
rm "$log"

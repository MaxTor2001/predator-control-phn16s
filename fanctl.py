"""Вентиляторы и режимы мощности Acer Predator PHN16S-71 через sysfs драйвера acer-wmi."""

import argparse
from pathlib import Path

FANS = {"cpu": 1, "gpu": 2}
MIN_PERCENT = 20
"""Нижняя граница ручного режима (~950 об/мин).

На 15% вентиляторы близки к срыву (500-700 об/мин); остановку в простое делает авто-режим.
Проценты - не абсолютная скорость: когда датчик вентилятора теплее ~55°C, EC сам добавляет
обороты поверх заданных (50% дают ~2400 об/мин в холодном состоянии и ~3200 в тёплом).
"""
MODES = {0: "max", 1: "manual", 2: "auto"}
MAX, MANUAL, AUTO = 0, 1, 2

PROFILES = {
    "low-power": "Eco",
    "quiet": "Quiet",
    "balanced": "Balanced",
    "balanced-performance": "Performance",
    "performance": "Turbo",
}
"""Имена platform_profile ядра -> названия режимов PredatorSense (PL1 от сети: 55/65/75/85 Вт)."""


def find_device(pattern: str, name: str) -> Path:
    """Каталог sysfs-устройства по содержимому его файла `name`."""
    for path in Path("/sys/class").glob(f"{pattern}/name"):
        if path.read_text().strip() == name:
            return path.parent
    raise SystemExit(f"устройство {name} не найдено: загружен ли пропатченный acer-wmi?")


HWMON = find_device("hwmon/hwmon*", "acer")
PROFILE = find_device("platform-profile/*", "acer-wmi") / "profile"
POWER_LIMIT = Path("/sys/class/powercap/intel-rapl-mmio:0/constraint_0_power_limit_uw")


def read(attr: str) -> int:
    return int((HWMON / attr).read_text())


def write(attr: str, value: int) -> None:
    (HWMON / attr).write_text(str(value))


def fan_mode() -> int:
    return read("pwm1_enable")


def set_fan_mode(mode: int) -> None:
    """Режим обоих вентиляторов: AUTO - управляет прошивка, MAX - полные обороты."""
    for n in FANS.values():
        write(f"pwm{n}_enable", mode)


def percent(n: int) -> int:
    return round(read(f"pwm{n}") * 100 / 255)


def set_percent(value: int, fans: list[int]) -> None:
    """Перевести вентиляторы в ручной режим и задать скорость в процентах."""
    for n in fans:
        write(f"pwm{n}_enable", MANUAL)
        write(f"pwm{n}", round(value * 255 / 100))


def profile() -> str:
    return PROFILE.read_text().strip()


def set_profile(name: str) -> None:
    PROFILE.write_text(name)


def power_limit() -> int:
    """Длительный лимит мощности CPU (PL1) в ваттах - его и меняют режимы."""
    return int(POWER_LIMIT.read_text()) // 1_000_000


def status() -> None:
    print(f"режим мощности: {PROFILES[profile()]}, лимит CPU {power_limit()} Вт")
    print(f"температура: CPU {read('temp1_input') // 1000}°C, GPU {read('temp2_input') // 1000}°C")
    for label, n in FANS.items():
        mode = MODES[read(f"pwm{n}_enable")]
        target = f" {percent(n)}%" if mode == "manual" else ""
        print(f"{label}: {read(f'fan{n}_input')} об/мин, режим {mode}{target}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="обороты, температуры, режимы (по умолчанию)")
    sub.add_parser("auto", help="вентиляторы: автоматический режим")
    sub.add_parser("max", help="вентиляторы: полные обороты")
    p_set = sub.add_parser("set", help="вентиляторы: задать скорость вручную")
    p_set.add_argument("percent", type=int, choices=range(MIN_PERCENT, 101), metavar=f"{MIN_PERCENT}-100")
    p_set.add_argument("--fan", choices=FANS, help="только один вентилятор (по умолчанию оба)")
    p_profile = sub.add_parser("profile", help="режим мощности")
    p_profile.add_argument("name", choices=[label.lower() for label in PROFILES.values()])
    args = parser.parse_args()

    if args.command == "auto":
        set_fan_mode(AUTO)
    elif args.command == "max":
        set_fan_mode(MAX)
    elif args.command == "set":
        set_percent(args.percent, [FANS[args.fan]] if args.fan else list(FANS.values()))
    elif args.command == "profile":
        set_profile(next(key for key, label in PROFILES.items() if label.lower() == args.name))
    status()


if __name__ == "__main__":
    main()

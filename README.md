# Predator Control

**English** | [Русский](README.ru.md)

A PredatorSense-like tool for Linux: power modes, fan control and monitoring
for the **Acer Predator Helios Neo 16S (PHN16S-71)** laptop.

![Predator Control window](docs/screenshot.png)

Tested on a single machine: PHN16S-71, BIOS V1.06, Ubuntu with kernel 7.0.0-31, GNOME on X11.
Not tested on other models or kernels. The application UI is in Russian.

## Features

- **Monitoring** — CPU/GPU temperature and the speed of both fans, updated once a second.
- **Power modes** — Eco / Quiet / Balanced / Performance / Turbo, the same as in PredatorSense.
- **Fans** — Auto (firmware-controlled), Max, Custom with separate CPU and GPU sliders (20–100 %).
- A window (`fan-gui`) and a command-line tool (`fanctl.py`), both work without sudo.

## How it works

The in-kernel `acer-wmi` driver already supports all of the above, but the PHN16S-71 is missing from
its model table, so on this laptop it does not even report fan speed. `driver/` contains `acer-wmi.c`
from kernel v7.0 with [`phn16s-71.patch`](driver/phn16s-71.patch) applied:

1. A DMI entry for `Predator PHN16S-71` with the `predator_v4` + `pwm` flags.
2. Until a mode is selected for the first time, this model's firmware reports profile code `0x02`,
   which the driver does not know (reading `platform_profile` failed with `EOPNOTSUPP`).
   In that case the driver selects Balanced on load.

The module is installed through DKMS and is rebuilt on kernel updates. The application uses standard
sysfs files: `hwmon/*/pwm{1,2}`, `pwm{1,2}_enable`, `fan*_input`, `temp*_input` and
`platform-profile/*/profile`. A udev rule gives the `sudo` group write access to them.

## Installation

Requirements: headers for the running kernel, `gcc`, `make`, `dkms`, [`uv`](https://docs.astral.sh/uv/),
system GTK4 + libadwaita with PyGObject (already present on Ubuntu with GNOME). Secure Boot disabled
(otherwise the module has to be signed).

```bash
sudo ./install.sh     # driver (DKMS) + udev rule, reloads acer_wmi
./install-user.sh     # "Predator Control" launcher and icon in the applications menu
```

At the end `install.sh` should print the module path under `updates/dkms`, `rw-rw-r-- root sudo`
permissions on `pwm*` and `profile`, and the current mode.

## Usage

Window: "Predator Control" in the applications menu, or `./fan-gui`.

```bash
uv run fanctl.py                  # status
uv run fanctl.py profile quiet    # eco | quiet | balanced | performance | turbo
uv run fanctl.py set 40           # manual fan speed, 20-100 %
uv run fanctl.py set 60 --fan gpu
uv run fanctl.py max
uv run fanctl.py auto
```

Closing the window resets nothing: the selected mode stays until reboot.

## Measurements on this machine

| Mode | PredatorSense | PL1 (on AC) |
|---|---|---|
| `low-power` | Eco | 65 W (on AC, same as Balanced) |
| `quiet` | Quiet | 55 W |
| `balanced` | Balanced | 65 W |
| `balanced-performance` | Performance | 75 W |
| `performance` | Turbo | 85 W |

PL2 is 140 W with a 56 s window in every mode — short loads do not depend on the mode.

Full all-core load, 130 s, fans in Auto, average over 70–128 s:

| | Balanced | Turbo |
|---|---|---|
| Frequency | 3177 MHz | 3239 MHz (+2 %) |
| CPU temperature | 96 °C | 103–105 °C |
| Fans | ~3130 RPM | ~4810 RPM |

In both modes the CPU is limited by temperature, not by the power limit; Turbo raises the thermal
ceiling. Games have not been measured.

Firmware (EC) quirks:

- Custom percentages are not an absolute speed. When the fan's sensor is warmer than ~55 °C, the EC adds
  RPM on top of the requested value: 50 % gives ~2400 RPM when cold and ~3200 when warm.
  You cannot overheat the machine with the slider.
- Below 20 % the fans are close to stalling (15 % — 500–700 RPM), hence the 20–100 % range.
  Only Auto mode stops the fans at idle.
- The stock Auto curve is lazy: under load the fans take ~40 s to reach 3100 RPM.

## Work in progress: Dynamic Boost for the GPU

Not finished. The RTX 5070 Laptop has a default power limit of 70 W with a maximum of 115 W;
the limit is raised by the `nvidia-powerd` daemon (Dynamic Boost). The firmware reports
`Notebook Dynamic Boost: Supported`, but Ubuntu neither enables the daemon nor installs its D-Bus policy.

- `nvidia/nvidia-dbus.conf` — the D-Bus policy from the official NVIDIA distribution (taken from Debian's `nvidia-powerd` package).
- `sudo nvidia/try-powerd.sh` — enable the daemon temporarily, until reboot; `... stop` — undo.
- `tools/gpu_bench.sh` — GPU measurement under load (a Vulkan compute shader via `wgpu`, no root), stops if the GPU exceeds 87 °C.

Measurement: 70 s of load, Balanced mode, values after reaching P0 (for the first ~20 s the driver keeps
the card in P4, 19 W, regardless of the Acer mode):

| | without the daemon | with `nvidia-powerd` |
|---|---|---|
| GPU power limit | 70 W | 85 W |
| Power draw | 66–67 W | 65–66 W |
| Clock | 2790 MHz | 2805 MHz |
| GPU temperature | 68 °C | 64 °C |
| Speed | 9.7 passes/s | 9.6 passes/s |

The `light` shader draws only ~65 W by itself and never hits the limit. The `heavy` load
(`tools/gpu_bench.sh 50 heavy`, random memory reads) is power-limited, Balanced mode:

| `heavy` | without the daemon | with `nvidia-powerd` |
|---|---|---|
| Limit / draw | 70 / 69.9 W | 85 / 84.8 W (+21 %) |
| Clock | 2300–2380 MHz | 2625–2655 MHz (+12 %) |
| GPU temperature after 50 s | 65 °C | 68 °C |
| Speed | 1.26–1.29 passes/s | 1.32–1.33 passes/s (+5 %) |

The daemon gives +15 W and +12 % clock; on this load, which is also memory-bound, that is +5 % speed.
Games and the limit in Performance/Turbo modes have not been measured; the daemon is not installed permanently yet.

## Limitations and untested areas

- After a reboot the driver comes up by itself (Balanced, fans in Auto). Interaction with
  `power-profiles-daemon` (it writes to the same `platform_profile`) has not been tested.
- The fan tiles in the window do not track mode changes made elsewhere (the power mode is tracked).
- No keyboard backlight control: `acer-wmi` has no interface for it.
- If DKMS fails to build the module for a new kernel, the stock driver is loaded: the fans stay
  in Auto and the application reports that the device was not found.

## Uninstall

```bash
sudo dkms remove acer-wmi-phn16s/1.1 --all
sudo rm -rf /usr/src/acer-wmi-phn16s-1.1 /etc/udev/rules.d/90-acer-fan.rules
sudo modprobe -r acer_wmi && sudo modprobe acer_wmi
rm ~/.local/share/applications/predator-control.desktop ~/.local/share/icons/hicolor/scalable/apps/predator-control.svg
```

## License

`driver/acer-wmi.c` is Linux kernel code, GPL-2.0-or-later. Everything else is under the same terms.
This project is not affiliated with Acer; no Acer logos or artwork are used.

"""Круговой индикатор: внешняя дуга - обороты вентилятора, внутренняя - температура, в центре цифры."""

import math

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gsk, Gtk  # noqa: E402

ACCENT, WARM, HOT, TRACK = "#00d8ff", "#ffb020", "#ff3b4e", "#1b242b"
START, SWEEP = 135, 270
"""Дуга идёт по часовой стрелке от 135° (слева внизу) на 270°."""
MAX_RPM = 5000
TEMP_RANGE = (30, 100)


def rgba(color: str, alpha: float = 1.0) -> Gdk.RGBA:
    result = Gdk.RGBA()
    result.parse(color)
    result.alpha = alpha
    return result


def temp_color(temp: int) -> str:
    return ACCENT if temp < 65 else WARM if temp < 85 else HOT


def arc(cx: float, cy: float, radius: float, fraction: float) -> Gsk.Path:
    """Путь дуги от START на долю `fraction` полного размаха."""
    start, end = math.radians(START), math.radians(START + SWEEP * fraction)
    builder = Gsk.PathBuilder.new()
    builder.move_to(cx + radius * math.cos(start), cy + radius * math.sin(start))
    builder.svg_arc_to(
        radius, radius, 0, SWEEP * fraction > 180, True, cx + radius * math.cos(end), cy + radius * math.sin(end)
    )
    return builder.to_path()


def stroke(width: float, dash: list[float] | None = None) -> Gsk.Stroke:
    result = Gsk.Stroke.new(width)
    if dash:
        result.set_dash(dash)
    else:
        result.set_line_cap(Gsk.LineCap.ROUND)
    return result


class Ring(Gtk.Widget):
    """Рисует дуги; значения - доли 0..1."""

    def __init__(self, size: int) -> None:
        super().__init__(width_request=size, height_request=size)
        self.fan = self.temp = 0.0
        self.color = ACCENT

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        size = min(self.get_width(), self.get_height())
        cx, cy, outer = self.get_width() / 2, self.get_height() / 2, size / 2 - 12
        inner = outer - 16

        snapshot.append_stroke(arc(cx, cy, outer, 1), stroke(8), rgba(TRACK))
        snapshot.append_stroke(arc(cx, cy, inner, 1), stroke(5, [2, 7]), rgba(TRACK))
        if self.fan > 0.005:
            snapshot.append_stroke(arc(cx, cy, outer, self.fan), stroke(18), rgba(ACCENT, 0.13))
            snapshot.append_stroke(arc(cx, cy, outer, self.fan), stroke(8), rgba(ACCENT))
        if self.temp > 0.005:
            snapshot.append_stroke(arc(cx, cy, inner, self.temp), stroke(5, [2, 7]), rgba(self.color))


class Gauge(Gtk.Overlay):
    def __init__(self, name: str, size: int = 220) -> None:
        super().__init__()
        self.ring = Ring(size)
        self.temp = Gtk.Label(css_classes=["gauge-temp"])
        self.rpm = Gtk.Label(css_classes=["gauge-rpm"])
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        labels.append(Gtk.Label(label=name, css_classes=["gauge-name"]))
        labels.append(self.temp)
        labels.append(self.rpm)
        self.set_child(self.ring)
        self.add_overlay(labels)

    def update(self, rpm: int, temp: int) -> None:
        low, high = TEMP_RANGE
        self.ring.fan = min(rpm / MAX_RPM, 1)
        self.ring.temp = min(max((temp - low) / (high - low), 0), 1)
        self.ring.color = temp_color(temp)
        self.ring.queue_draw()
        self.temp.set_label(f"{temp}°")
        self.rpm.set_label(f"{rpm} RPM")

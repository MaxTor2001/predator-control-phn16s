"""Окно в духе PredatorSense: мониторинг, режим мощности, вентиляторы (GTK4/libadwaita). Запуск: ./fan-gui"""

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

import fanctl  # noqa: E402
from gauge import Gauge  # noqa: E402

TEMPS = {"cpu": "temp1_input", "gpu": "temp2_input"}
PROFILE_TILES = {
    "low-power": ("ECO", "батарея"),
    "quiet": ("QUIET", "55 Вт"),
    "balanced": ("BALANCED", "65 Вт"),
    "balanced-performance": ("PERFORM", "75 Вт"),
    "performance": ("TURBO", "85 Вт"),
}
FAN_TILES = {fanctl.AUTO: ("AUTO", None), fanctl.MAX: ("MAX", None), fanctl.MANUAL: ("CUSTOM", None)}
FAN_STATES = {
    fanctl.AUTO: "УПРАВЛЯЕТ ПРОШИВКА",
    fanctl.MAX: "ПОЛНЫЕ ОБОРОТЫ",
    fanctl.MANUAL: "ЗАДАНО ВРУЧНУЮ",
}


class TileGroup(Gtk.Box):
    """Ряд плиток с одним активным вариантом; on_select(key) вызывается при выборе."""

    def __init__(self, options: dict, active, on_select) -> None:
        super().__init__(spacing=8, homogeneous=True)
        self.buttons = {}
        for key, (title, subtitle) in options.items():
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            content.append(Gtk.Label(label=title, css_classes=["tile-title"]))
            if subtitle:
                content.append(Gtk.Label(label=subtitle, css_classes=["tile-subtitle"]))
            button = Gtk.ToggleButton(child=content, css_classes=["tile", title.lower()])
            button.set_group(next(iter(self.buttons.values()), None))
            self.buttons[key] = button
            self.append(button)
        self.select(active)
        for key, button in self.buttons.items():
            button.connect("toggled", lambda b, k=key: b.get_active() and on_select(k))

    def select(self, key) -> None:
        self.buttons[key].set_active(True)


def section(title: str, value: Gtk.Label | None = None) -> Gtk.Box:
    """Заголовок секции; справа - необязательное живое значение."""
    box = Gtk.Box(css_classes=["section"])
    box.append(Gtk.Label(label=title, xalign=0, hexpand=True))
    if value:
        box.append(value)
    return box


class FanWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="Predator Control", default_width=660, resizable=False)
        self.add_css_class("predator")

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        for side in ("top", "bottom", "start", "end"):
            getattr(body, f"set_margin_{side}")(26)
        self.limit = Gtk.Label(css_classes=["section-value"])
        self.fan_state = Gtk.Label(css_classes=["section-value"])
        for widget in (
            self.build_gauges(),
            section("РЕЖИМ", self.limit),
            self.build_profiles(),
            section("ВЕНТИЛЯТОРЫ", self.fan_state),
        ):
            body.append(widget)
        for widget in self.build_fans():
            body.append(widget)

        header = Adw.HeaderBar(title_widget=Gtk.Label(label="PREDATOR CONTROL", css_classes=["brand"]))
        view = Adw.ToolbarView(content=body)
        view.add_top_bar(header)
        self.set_content(view)

        self.refresh()
        GLib.timeout_add_seconds(1, self.refresh)

    def build_gauges(self) -> Gtk.Box:
        box = Gtk.Box(spacing=40, halign=Gtk.Align.CENTER, margin_bottom=8)
        self.gauges = {label: Gauge(label.upper()) for label in fanctl.FANS}
        for gauge in self.gauges.values():
            box.append(gauge)
        return box

    def build_profiles(self) -> TileGroup:
        self.profiles = TileGroup(PROFILE_TILES, fanctl.profile(), self.apply_profile)
        return self.profiles

    def build_fans(self) -> list[Gtk.Widget]:
        """Плитки AUTO/MAX/CUSTOM и ползунки CPU/GPU, выставленные по текущему состоянию EC."""
        self.sliders = Gtk.Grid(column_spacing=16, row_spacing=6, css_classes=["sliders"])
        self.sliders.set_sensitive(fanctl.fan_mode() == fanctl.MANUAL)
        self.scales = {}
        for row, (label, n) in enumerate(fanctl.FANS.items()):
            value = Gtk.Label(width_chars=5, xalign=1, css_classes=["fan-value"])
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, fanctl.MIN_PERCENT, 100, 1)
            scale.set_hexpand(True)
            scale.connect("value-changed", self.apply_percent, n, value)
            scale.set_value(max(fanctl.MIN_PERCENT, fanctl.percent(n)))
            value.set_label(f"{scale.get_value():.0f}%")
            self.sliders.attach(Gtk.Label(label=label.upper(), xalign=0, css_classes=["fan-label"]), 0, row, 1, 1)
            self.sliders.attach(scale, 1, row, 1, 1)
            self.sliders.attach(value, 2, row, 1, 1)
            self.scales[n] = scale

        hint = Gtk.Label(
            label="CUSTOM: при нагреве выше ~55°C прошивка сама добавляет обороты поверх заданных.",
            xalign=0,
            wrap=True,
            css_classes=["hint"],
        )
        self.fan_tiles = TileGroup(FAN_TILES, fanctl.fan_mode(), self.apply_fan_mode)
        return [self.fan_tiles, self.sliders, hint]

    def apply_profile(self, name: str) -> None:
        if name != fanctl.profile():
            fanctl.set_profile(name)

    def apply_fan_mode(self, mode: int) -> None:
        self.sliders.set_sensitive(mode == fanctl.MANUAL)
        if mode == fanctl.MANUAL:
            for n, scale in self.scales.items():
                fanctl.set_percent(round(scale.get_value()), [n])
        else:
            fanctl.set_fan_mode(mode)

    def apply_percent(self, scale: Gtk.Scale, n: int, value: Gtk.Label) -> None:
        """Обновить подпись; в EC писать только в ручном режиме (при создании окна ползунки лишь отражают состояние)."""
        value.set_label(f"{scale.get_value():.0f}%")
        if self.sliders.get_sensitive():
            fanctl.set_percent(round(scale.get_value()), [n])

    def refresh(self) -> bool:
        """Обновить показания; режим мощности могли сменить извне (клавиша Turbo, меню GNOME)."""
        for label, n in fanctl.FANS.items():
            self.gauges[label].update(fanctl.read(f"fan{n}_input"), fanctl.read(TEMPS[label]) // 1000)
        self.profiles.select(fanctl.profile())
        self.limit.set_label(f"ЛИМИТ CPU  {fanctl.power_limit()} Вт")
        self.fan_state.set_label(FAN_STATES[fanctl.fan_mode()])
        return GLib.SOURCE_CONTINUE


def load_style() -> None:
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
    provider = Gtk.CssProvider()
    provider.load_from_path(str(Path(__file__).with_name("style.css")))
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def activate(app: Adw.Application) -> None:
    load_style()
    FanWindow(app).present()


def main() -> None:
    app = Adw.Application(application_id="local.itguy.FanControl")
    app.connect("activate", activate)
    app.run()


if __name__ == "__main__":
    main()

from win32gui import SetForegroundWindow
from pygame import display
from pygame_menu import Menu, themes, font


class IGMenu:
    def __init__(self, settings):
        self.set = settings
        self.b2s = lambda x: "Enabled" if x else "Disabled"
        self.set_bool = lambda x: setattr(self.set, x, False if getattr(self.set, x) else True)

        theme = themes.THEME_DARK
        theme.title_font_size = 16
        theme.widget_font_size = 14
        theme.title_font = font.FONT_FRANCHISE
        theme.title_background_color = (0, 0, 0)
        theme.widget_font = font.FONT_FRANCHISE

        self.menu = Menu(
            title="Meow CSGO",
            height=320,
            width=200,
            theme=themes.THEME_DARK,
            mouse_visible=False,
            mouse_enabled=False,
            mouse_motion_selection=False,
            joystick_enabled=False,
        )

        self.update_widgets()
        self.menu.disable()

    def switch(self):
        if self.menu.is_enabled():
            self.menu.disable()
            self.update_widgets()
        else:
            self.menu.enable()

    def update_widgets(self):
        self.menu.clear()
        self.menu.add_label("Misc")
        self.menu.add_selector(
            "Trigger Bot  ", [(self.b2s(self.set.trigger_bot), 0), (self.b2s(not self.set.trigger_bot), 0)],
            onchange=lambda x, y: self.set_bool("trigger_bot")
        )
        self.menu.add_selector(
            "Team Attack  ", [(self.b2s(self.set.team_attack), 0), (self.b2s(not self.set.team_attack), 0)],
            onchange=lambda x, y: self.set_bool("team_attack")
        )
        self.menu.add_vertical_margin(10)
        self.menu.add_label("ESP")
        self.menu.add_selector(
            "Boxes  ", [(self.b2s(self.set.esp_boxes), 0), (self.b2s(not self.set.esp_boxes), 0)],
            onchange=lambda x, y: self.set_bool("esp_boxes")
        )
        self.menu.add_selector(
            "Glow  ", [(self.b2s(self.set.esp_glow), 0), (self.b2s(not self.set.esp_glow), 0)],
            onchange=lambda x, y: self.set_bool("esp_glow")
        )
        self.menu.add_selector(
            "Weapon Icon  ", [(self.b2s(self.set.esp_weapon_icon), 0), (self.b2s(not self.set.esp_weapon_icon), 0)],
            onchange=lambda x, y: self.set_bool("esp_weapon_icon")
        )
        self.menu.add_selector(
            "Health Pie  ", [(self.b2s(self.set.esp_health_pie), 0), (self.b2s(not self.set.esp_health_pie), 0)],
            onchange=lambda x, y: self.set_bool("esp_health_pie")
        )
        self.menu.add_vertical_margin(10)
        self.menu.add_label("Color")
        self.menu.add_color_input(
            "T:   ", color_type="rgb", default=self.set.t_color,
            onreturn=lambda x: setattr(self.set, "t_color", x)
        )
        self.menu.add_color_input(
            "C:   ", color_type="rgb", default=self.set.c_color,
            onreturn=lambda x: setattr(self.set, "c_color", x)
        )

    def draw_menu(self, events, overlay):
        try:
            SetForegroundWindow(display.get_wm_info()["window"])
        except:
            pass
        self.menu.update(events)
        self.menu.draw(overlay)

import os
import win32gui
import win32con
import win32api
import math
import json

from requests import get
from colorama import Fore
from tabulate import tabulate

import contextlib

with contextlib.redirect_stdout(None):
    import pygame


class Colors:
    trans = (255, 0, 128)
    red = (255, 0, 0)
    yellow = (255, 255, 100)
    blue = (0, 0, 255)
    green = (0, 255, 0)
    white = (255, 255, 255)
    black = (0, 0, 0)
    silver = (192, 192, 192)


class Settings:
    team_attack = False
    trigger_bot = True

    esp_glow = True
    esp_boxes = False
    esp_weapon_icon = True
    esp_health_pie = True

    t_color = (255, 0, 0)
    c_color = (0, 0, 255)


def parse_dump_offsets():
    offset_website = "https://raw.githubusercontent.com/frk1/hazedumper/master/csgo.json"
    web = False if os.path.isfile("data/csgo.json") else True

    class Offsets:
        pass

    offsets = get(offset_website).json() if web else json.load(open("data/csgo.json"))
    [setattr(Offsets, k, v) for k, v in offsets["signatures"].items()]
    [setattr(Offsets, k, v) for k, v in offsets["netvars"].items()]
    table = [
        [Fore.LIGHTCYAN_EX + k, Fore.LIGHTWHITE_EX + hex(v).upper()]
        for k, v in vars(Offsets).items()
        if not k.startswith("_")
    ]
    print(tabulate(table, ("Name", "Pointer / Offset"), "pretty", showindex=True))
    return Offsets


def get_game_window(hwnd_name="Counter-Strike: Global Offensive"):
    class Window:
        hwnd = None
        x = None
        y = None
        width = None
        height = None

    w = Window()
    w.hwnd = win32gui.FindWindow(None, hwnd_name)
    window_rect = win32gui.GetWindowRect(w.hwnd)
    w.x = window_rect[0] - 5
    w.y = window_rect[1]
    w.width = window_rect[2] - w.x
    w.height = window_rect[3] - w.y

    return w


def wts(matrix, pos):
    game = get_game_window()

    clip_x = pos.x * matrix[0] + pos.y * matrix[1] + pos.z * matrix[2] + matrix[3]
    clip_y = pos.x * matrix[4] + pos.y * matrix[5] + pos.z * matrix[6] + matrix[7]
    clip_w = pos.x * matrix[12] + pos.y * matrix[13] + pos.z * matrix[14] + matrix[15]

    if clip_w < 0.1:
        return False

    ndc = pygame.math.Vector2()
    ndc.x = clip_x / clip_w
    ndc.y = clip_y / clip_w

    screen = pygame.math.Vector2()
    screen.x = (game.width / 2 * ndc.x) + (ndc.x + game.width / 2)
    screen.y = -(game.height / 2 * ndc.y) + (ndc.y + game.height / 2)

    return screen


def track_game():
    game = get_game_window()
    win32gui.SetWindowPos(pygame.display.get_wm_info()["window"], -1, game.x, game.y, 0, 0, 0x0001)


def create_overlay(game_window):
    pygame.event.set_blocked(pygame.MOUSEMOTION)
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    screen = pygame.display.set_mode(
        (game_window.width, game_window.height), pygame.NOFRAME | pygame.DOUBLEBUF | pygame.HWACCEL
    )
    pygame.display.set_caption("Meowbot CSCSGO", "Meowbot CSGO")
    hwnd = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowLong(
        hwnd,
        win32con.GWL_EXSTYLE,
        win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        | win32con.WS_EX_LAYERED
        | win32con.WS_EX_TOOLWINDOW
        | win32con.WS_EX_TOPMOST
        | win32con.WS_EX_NOACTIVATE,
    )
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*Colors.trans), 0, win32con.LWA_COLORKEY)
    return screen


def draw_pie(screen, pos, r, value, bg=Colors.red, fill=Colors.green):
    """
    A polygon circle with a filled background circle
    """
    x, y = map(int, pos)
    pygame.draw.circle(screen, bg, (x, y), r)
    angle = int(value * 360 / 100)

    p = [(x, y)]
    for n in range(angle):
        p.append((x + int(r * math.cos(n * math.pi / 180)), y + int(r * math.sin(n * math.pi / 180))))
    p.append((x, y))

    if len(p) > 2:
        pygame.draw.polygon(screen, fill, p)


def _circlepoints(r):
    _circle_cache = {}
    r = int(round(r))
    if r in _circle_cache:
        return _circle_cache[r]
    x, y, e = r, 0, 1 - r
    _circle_cache[r] = points = []
    while x >= y:
        points.append((x, y))
        y += 1
        if e < 0:
            e += 2 * y - 1
        else:
            x -= 1
            e += 2 * (y - x) - 1
    points += [(y, x) for x, y in points if x > y]
    points += [(-x, y) for x, y in points if x]
    points += [(x, -y) for x, y in points if y]
    points.sort()
    return points


def render(text, font, gfcolor=Colors.white, ocolor=Colors.black, opx=2):
    textsurface = font.render(text, False, gfcolor).convert_alpha()
    w = textsurface.get_width() + 2 * opx
    h = font.get_height()

    osurf = pygame.Surface((w, h + 2 * opx)).convert_alpha()
    osurf.fill((0, 0, 0, 0))

    surf = osurf.copy()
    osurf.blit(font.render(text, False, ocolor).convert_alpha(), (0, 0))

    for dx, dy in _circlepoints(opx):
        surf.blit(osurf, (dx + opx, dy + opx))

    surf.blit(textsurface, (opx, opx))
    return surf

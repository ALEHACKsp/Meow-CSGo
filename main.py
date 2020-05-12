import sys

from struct import unpack, pack
from time import sleep
from warnings import filterwarnings

from pymem import Pymem, logger; logger.disabled = True

from pymem.process import module_from_name
from pymem.memory import write_bytes
from pymem.exception import *
from mouse import click
from keyboard import register_hotkey
from colorama import init

from helper import *
from menu import IGMenu

try:
    init(True)
    pygame.display.init()
    pygame.font.init()
    filterwarnings("ignore")

    with contextlib.redirect_stdout(None):
        mem = Pymem("csgo.exe")

    Offsets = parse_dump_offsets()
    Offsets.game_module = module_from_name(mem.process_handle, "client_panorama.dll").lpBaseOfDll
    Offsets.game_engine = module_from_name(mem.process_handle, "engine.dll").lpBaseOfDll

    game_window = get_game_window()
    overlay = create_overlay(game_window)
    settings = Settings()
    game_menu = IGMenu(settings)
    weapon_ids = json.load(open("data/weapons.json"))
    view_matrix = lambda: unpack("16f", mem.read_bytes(Offsets.game_module + Offsets.dwViewMatrix, 16 * 4))

    font = pygame.font.SysFont("Courier", 11)
    gun_font = pygame.font.Font("data/guns.ttf", 18)
except ProcessNotFound:
    sys.exit("please start csgo first")


class Entity:
    def __init__(self, address):
        self.address = address

        self.team = mem.read_int(self.address + Offsets.m_iTeamNum) == 2
        self.health = mem.read_int(self.address + Offsets.m_iHealth)
        self.dormant = mem.read_int(self.address + Offsets.m_bDormant)
        self.alive = self.health > 0
        self.id = mem.read_int(self.address + 0x64)

        self.matrix = view_matrix()
        self.wts = wts(self.matrix, self.pos)
        self.bone_base = mem.read_int(self.address + Offsets.m_dwBoneMatrix)

    @property
    def pos(self):
        v = pygame.math.Vector3()
        v.x, v.y, v.z = unpack("3f", mem.read_bytes(self.address + Offsets.m_vecOrigin, 12))
        return v

    @property
    def weapon(self):
        weapon = mem.read_int(self.address + Offsets.m_hActiveWeapon)
        weapon_entity = mem.read_int(Offsets.game_module + Offsets.dwEntityList + ((weapon & 0xFFF) - 1) * 0x10)
        weapon_id = str(mem.read_short(weapon_entity + Offsets.m_iItemDefinitionIndex))
        return weapon_ids.get(weapon_id, weapon_id)

    @property
    def name(self):
        radar_base = mem.read_int(Offsets.game_module + Offsets.dwRadarBase)
        c_hud_radar = mem.read_int(radar_base + 0x74)
        name = mem.read_string(c_hud_radar + 0x300 + (0x174 * (self.id - 1)))
        return name

    @property
    def cross_id(self):
        return mem.read_int(self.address + Offsets.m_iCrosshairId)

    def bone_pos(self, bone):
        bone_pos = pygame.math.Vector3()
        bone_pos.x = mem.read_float(self.bone_base + 0x30 * bone + 0x0C)
        bone_pos.y = mem.read_float(self.bone_base + 0x30 * bone + 0x1C)
        bone_pos.z = mem.read_float(self.bone_base + 0x30 * bone + 0x2C)
        bone_wts = wts(self.matrix, bone_pos)
        return bone_wts

    def glow(self):
        glow_address = \
            mem.read_int(Offsets.game_module + Offsets.dwGlowObjectManager) + \
            mem.read_int(self.address + Offsets.m_iGlowIndex) * 0x38

        # RGBA at EntityGlowAddress + Base  // 4 floats, 16 bytes
        write_bytes(
            mem.process_handle,
            glow_address + 0x4,
            pack("4f", *list(settings.t_color) + [1.3] if self.team else list(settings.c_color) + [1.3]),
            16
        )

        # renderWhenOccluded, renderWhenUnOccluded, FullGlow at EntityGlowAddress + 0x24
        write_bytes(
            mem.process_handle,
            glow_address + 0x24,
            pack("??", True, False),
            2
        )

    def cham(self):
        """
        Not used
        """
        write_bytes(
            mem.process_handle,
            self.address + Offsets.m_clrRender,
            pack("4f", *list(settings.t_color) + [1.1] if self.team else list(settings.c_color) + [1.1]),
            16
        )

    def spotted(self):
        mem.write_int(self.address + Offsets.m_bSpotted, 1)

    def draw_box(self):
        """
        Not bad, not good.
        """
        head_pos = self.bone_pos(8)
        if self.wts and head_pos:
            scale = 15
            pygame.draw.lines(
                overlay,
                settings.t_color if self.team else settings.c_color,
                True,
                [
                    (head_pos.x + scale, head_pos.y),
                    (head_pos.x - scale, head_pos.y),
                    (self.wts.x - scale, self.wts.y + 20),
                    (self.wts.x + scale, self.wts.y + 20),
                ],
                2,
            )

    def draw_health(self):
        if self.health > 66:
            hp_color = Colors.green
        elif self.health > 33:
            hp_color = Colors.yellow
        else:
            hp_color = Colors.red

        if self.wts:
            overlay.blit(font.render(f"H: {self.health}", False, hp_color), (self.wts.x - 15, self.wts.y + 25))
            if settings.esp_health_pie:
                draw_pie(overlay, (self.wts.x - 30, self.wts.y + 45), 10, self.health, bg=Colors.black, fill=hp_color)

    def draw_distance(self, local_player):
        try:
            distance = int(self.pos.distance_to(local_player.pos) / 20)
        except ZeroDivisionError:
            return

        if distance < 30:
            color = Colors.red
        elif distance < 40:
            color = Colors.yellow
        else:
            color = Colors.white

        if self.wts:
            overlay.blit(font.render(f"D: {distance}", False, color), (self.wts.x - 15, self.wts.y + 35))

    def draw_weapon(self):
        if self.wts:
            w = self.weapon
            overlay.blit(font.render(f"W: {self.weapon[0]}", False, Colors.white), (self.wts.x - 15, self.wts.y + 45))
            if w[1] and settings.esp_weapon_icon:
                overlay.blit(render(w[1], gun_font), (self.wts.x + 33, self.wts.y + 25))

    def draw_name(self):
        if self.wts:
            overlay.blit(font.render(f"N: {self.name}", False, Colors.white), (self.wts.x - 15, self.wts.y + 55))


class Hacks:
    @staticmethod
    def trigger_bot(local, entity):
        if local.cross_id and local.cross_id == entity.id:
            if local.weapon[0].startswith("Revo"):
                click("right")
            elif local.weapon[0].startswith("Knife") or "grenade" in local.weapon[0]:
                return
            else:
                click()

    @staticmethod
    def no_recoil(local_player):
        """
        Works, but I hate it.


        global o_punch

        shots_fired = mem.read_int(local_player.address + Offsets.m_iShotsFired)

        if shots_fired > 1:
            client_state = mem.read_int(game_engine + Offsets.dwClientState)

            view_angles = pygame.math.Vector2()
            view_angles.x, view_angles.y = unpack(
                "2f", mem.read_bytes(client_state + Offsets.dwClientState_ViewAngles, 8)
            )

            punch_angle = pygame.math.Vector2()
            punch_angle.x, punch_angle.y = unpack(
                "2f", mem.read_bytes(local_player.address + Offsets.m_aimPunchAngle, 8)
            )

            new_angle = (view_angles + o_punch) - (punch_angle * 2)
            # new_angle.normalize()

            o_punch = punch_angle * 2

            mem.write_float(client_state + Offsets.dwClientState_ViewAngles, new_angle.x)
            mem.write_float(client_state + Offsets.dwClientState_ViewAngles + 4, new_angle.y)
        else:
            o_punch = pygame.math.Vector2()
        """
        pass


def get_entities(local_player):
    for i in range(64):
        entity_address = mem.read_int(Offsets.game_module + Offsets.dwEntityList + i * 0x10)
        if entity_address and entity_address != local_player.address:
            ent_class = Entity(entity_address)
            if ent_class.team == local_player.team and not settings.team_attack:
                continue
            yield ent_class


def main():
    register_hotkey("F1", game_menu.switch)
    register_hotkey("F2", lambda: os._exit(1))
    win32gui.SetForegroundWindow(game_window.hwnd)

    while True:
        try:
            overlay.fill(Colors.trans)
            window_focused = game_window.hwnd == win32gui.GetForegroundWindow()

            if window_focused:
                try:
                    local_player = Entity(mem.read_int(Offsets.game_module + Offsets.dwLocalPlayer))
                except:
                    sleep(0.2)
                    continue

                for e in get_entities(local_player):
                    if not e.dormant and e.alive:
                        try:
                            if settings.trigger_bot:
                                Hacks.trigger_bot(local_player, e)
                            if settings.esp_boxes:
                                e.draw_box()
                            if settings.esp_glow:
                                e.glow()
                            e.spotted()
                            e.draw_health()
                            e.draw_distance(local_player)
                            e.draw_weapon()
                            e.draw_name()
                            # e.cham()
                        except Exception as exc:
                            print(f"Entity Error: ({e}) {exc}")

            events = pygame.event.get()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    break

            if game_menu.menu.is_enabled():
                try:
                    game_menu.draw_menu(events, overlay)
                except:
                    pass

            track_game()
            pygame.display.update()
            pygame.time.delay(5)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()

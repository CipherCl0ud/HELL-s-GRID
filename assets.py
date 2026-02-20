import pygame
import os
import numpy as np
from settings import *

BASE_PATH = r"D:\Project\Hell's Grid\assets"
FONT_FOLDER = r"D:\Project\Hell's Grid\Font"
FONT_FILENAME = "KingstoneDemoRegular-G3n5G.ttf"

# Specific Menu Assets
MENU_BG_FILENAME = "background.png"
MENU_LOGO_FILENAME = "logo and mc.png"
LOADING_SCREEN_FILENAME = "hell's grid main.png"

def load_custom_font(size):
    try:
        path = os.path.join(FONT_FOLDER, FONT_FILENAME)
        return pygame.font.Font(path, size)
    except:
        return pygame.font.SysFont('Arial', size, bold=True)

def load_texture(filename):
    path = os.path.join(BASE_PATH, filename)
    if not os.path.exists(path): path = path.replace(".png", ".jpg")
    try:
        img = pygame.image.load(path).convert()
        img = pygame.transform.scale(img, (TEXTURE_SIZE, TEXTURE_SIZE))
        return pygame.surfarray.array3d(img)
    except:
        surf = pygame.Surface((TEXTURE_SIZE, TEXTURE_SIZE))
        surf.fill((255, 0, 255))
        return pygame.surfarray.array3d(surf)

class AssetManager:
    def __init__(self):
        self.fonts = {}
        self.images = {}
        self.wall_textures = None
        self.floor_texture = None
        self.ceil_texture = None
        self.enemy_frames = []
        self.faces = {}
        
    def load_all(self):
        self.fonts['menu'] = load_custom_font(20)
        self.fonts['hud'] = load_custom_font(50)
        self.fonts['label'] = load_custom_font(16)
        self.fonts['interact'] = load_custom_font(24)
        self.fonts['fps'] = load_custom_font(18)
        self.fonts['death'] = load_custom_font(100)
        self.fonts['restart'] = load_custom_font(30)

        for name, file in [('menu_bg', MENU_BG_FILENAME), ('loading', LOADING_SCREEN_FILENAME)]:
            try:
                img = pygame.image.load(os.path.join(BASE_PATH, file)).convert()
                self.images[name] = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
            except: 
                self.images[name] = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        try:
            logo = pygame.image.load(os.path.join(BASE_PATH, MENU_LOGO_FILENAME)).convert_alpha()
            target_w = int(SCREEN_WIDTH * 1.15)
            ratio = target_w / logo.get_width()
            target_h = int(logo.get_height() * ratio)
            self.images['menu_logo'] = pygame.transform.scale(logo, (target_w, target_h))
        except: 
            self.images['menu_logo'] = pygame.Surface((400, 300))

        # Gun Sprites
        try:
            gun = pygame.image.load(os.path.join(BASE_PATH, "gun_default.png")).convert_alpha()
            w, h = gun.get_size()
            self.images['gun_default'] = pygame.transform.scale(gun, (int(w * GUN_SCALE), int(h * GUN_SCALE)))
            gun_f = pygame.image.load(os.path.join(BASE_PATH, "gun_fire.png")).convert_alpha()
            w, h = gun_f.get_size()
            self.images['gun_fire'] = pygame.transform.scale(gun_f, (int(w * GUN_SCALE), int(h * GUN_SCALE)))
        except:
            self.images['gun_default'] = pygame.Surface((50,50))
            self.images['gun_fire'] = pygame.Surface((50,50))

        # Textures
        max_textures = 10
        self.wall_textures = np.zeros((max_textures, TEXTURE_SIZE, TEXTURE_SIZE, 3), dtype=np.int32)
        def add_texture(index, filename):
            if index < max_textures: self.wall_textures[index] = load_texture(filename)

        # 1=Wall, 2=Mossy, 3=Locked(Switch1), 4=Door(Switch2), 5=Tech
        add_texture(1, "wall1.png")
        add_texture(2, "wall2.png")
        add_texture(3, "wall switch1.png") # Locked
        add_texture(4, "wall switch2.png") # Standard Door
        add_texture(5, "wall3.png")

        self.floor_texture = np.ascontiguousarray(load_texture("floor1.png"), dtype=np.int32)
        self.ceil_texture = np.ascontiguousarray(load_texture("floor2.png"), dtype=np.int32)

        # Enemy
        try:
            e1 = pygame.image.load(os.path.join(BASE_PATH, "enemywalk1.png")).convert()
            e1.set_colorkey((0,0,0))
            e2 = pygame.image.load(os.path.join(BASE_PATH, "enemywalk2.png")).convert()
            e2.set_colorkey((0,0,0))
            self.enemy_frames = [e1, e2]
        except: self.enemy_frames = [pygame.Surface((10,10)), pygame.Surface((10,10))]

        # HUD / Faces / Decals
        try:
            self.images['hole'] = pygame.transform.scale(pygame.image.load(os.path.join(BASE_PATH, "bullethole.png")).convert_alpha(), (30,30))
            self.images['blood'] = pygame.image.load(os.path.join(BASE_PATH, "blood splatter.png")).convert_alpha()
        except: 
            self.images['hole'] = pygame.Surface((10,10))
            self.images['blood'] = pygame.Surface((10,10))

        for name, f in [('center','face.png'), ('left','face_left.png'), ('right','face_right.png')]:
            try: self.faces[name] = pygame.transform.scale(pygame.image.load(os.path.join(BASE_PATH, f)).convert_alpha(), (64,64))
            except: self.faces[name] = pygame.Surface((64,64))

        self.images['hud_bg'] = pygame.Surface((SCREEN_WIDTH, HUD_HEIGHT))
        try:
            t = pygame.image.load(os.path.join(BASE_PATH, "floor2.png")).convert()
            for x in range(0, SCREEN_WIDTH, t.get_width()):
                self.images['hud_bg'].blit(t, (x,0))
            d = pygame.Surface((SCREEN_WIDTH, HUD_HEIGHT)); d.fill((30,30,30)); d.set_alpha(120)
            self.images['hud_bg'].blit(d, (0,0))
        except: self.images['hud_bg'].fill((100,100,100))
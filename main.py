import pygame
import math
import numpy as np
import random
import sys
import json  # For saving/loading profiles
import os    # To check if the save file exists

# Import our custom modules
from settings import *
import assets
import raycaster
import levels

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        
        # Load Assets
        print("Compiling Engine & Loading Assets...")
        self.assets = assets.AssetManager()
        self.assets.load_all()

        # The green activated door is natively loaded by assets.py at Map ID 6
        self.green_switch_id = 6

        # --- FONT LOADING ---
        try:
            font_path = r"Font/FunkyWhimsyRegular-8OlpB.ttf"
            self.custom_ui_font = pygame.font.Font(font_path, 40)
            self.custom_ui_font_small = pygame.font.Font(font_path, 20)
            self.compass_font = pygame.font.Font(font_path, 32)
        except:
            print("Custom font file not found, falling back to default.")
            self.custom_ui_font = pygame.font.SysFont("Arial", 40)
            self.custom_ui_font_small = pygame.font.SysFont("Arial", 20)
            self.compass_font = pygame.font.SysFont("Arial", 32, bold=True)
        
        # --- GAME STATES & MENUS ---
        self.state = "menu"
        self.previous_state = "menu" 
        
        self.menu_selected = 0
        self.menu_options = ["START GAME", "OPTIONS", "EXIT"]
        
        # --- PROFILE SYSTEM ---
        self.save_file = "profiles.json"
        self.profiles = self.load_profiles()
        self.active_profile = None
        self.typing_name = ""
        
        self.profile_action_selected = 0
        self.profile_action_options = ["CONTINUE", "NEW PROFILE", "DELETE PROFILE", "BACK"]
        
        self.profile_list_selected = 0
        self.profile_list_mode = "continue" # Can be "continue" or "delete"

        self.pause_selected = 0
        self.pause_options = ["RESUME", "OPTIONS", "RESTART", "MAIN MENU", "QUIT TO DESKTOP"]
        
        # --- OPTIONS MENU VARIABLES ---
        self.options_selected = 0
        self.options_menu = ["MOUSE SENSITIVITY", "CROSSHAIR COLOR", "SHOW FPS", "CONTROLS", "BACK"]
        
        # Editable Settings
        self.mouse_sens = MOUSE_SENSITIVITY
        self.show_fps = False
        self.crosshair_colors = [
            (CROSSHAIR_COLOR, "DEFAULT"), 
            ((255, 0, 0), "RED"), 
            ((0, 255, 0), "GREEN"), 
            ((0, 255, 255), "CYAN"), 
            ((255, 255, 255), "WHITE"), 
            ((255, 255, 0), "YELLOW")
        ]
        self.crosshair_idx = 0

        # Controls List
        self.controls_text = [
            "W, A, S, D - Move",
            "MOUSE - Look Around",
            "LEFT CLICK - Fire Weapon",
            "R - Reload",
            "E - Interact (Doors/Switches)",
            "ESC / P - Pause Game"
        ]
        
        # Loading Vars
        self.loading_phase = 0
        self.loading_alpha = 0
        self.loading_timer = 0
        self.fade_speed = 5

        self.reset_game_data()
        
        self.screen_buffer = np.zeros((SCREEN_WIDTH, SCREEN_HEIGHT, 3), dtype=np.int32)
        self.depth_buffer = np.zeros(SCREEN_WIDTH, dtype=np.float32)

    # --- JSON SAVE SYSTEM ---
    def load_profiles(self):
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_profiles(self):
        with open(self.save_file, "w") as f:
            json.dump(self.profiles, f, indent=4)

    # --- LEVEL INIT & RESET ---
    def init_map(self):
        lvl = levels.LEVELS[self.current_level]
        self.map_size_x = lvl['MAP_SIZE_X']
        self.map_size_y = lvl['MAP_SIZE_Y']
        
        self.world_map = np.zeros((self.map_size_x, self.map_size_y), dtype=np.int32)
        self.door_state = np.zeros((self.map_size_x, self.map_size_y), dtype=np.float32) 
        self.door_lock = np.zeros((self.map_size_x, self.map_size_y), dtype=np.int32)
        self.door_dir = np.zeros((self.map_size_x, self.map_size_y), dtype=np.int32) 
        
        for j, char in enumerate(lvl['MAP_STRING']):
            x, y = j % self.map_size_x, j // self.map_size_x
            val = int(char)
            self.world_map[x, y] = val
            if val in [3, 4]:
                left = self.world_map[x-1, y] if x > 0 else 0
                right = self.world_map[x+1, y] if x < self.map_size_x-1 else 0
                self.door_dir[x, y] = 1 if (left != 0 and right != 0) else 0

    def reset_game_data(self):
        # 1. Load from profile if active, otherwise set defaults
        if self.active_profile and self.active_profile in self.profiles:
            p_data = self.profiles[self.active_profile]
            self.current_level = p_data["level"]
            self.health = p_data["health"]
            self.ammo = p_data["ammo"]
            self.armor = p_data["armor"]
        else:
            self.current_level = 0
            self.health, self.ammo, self.armor = MAX_HEALTH, MAX_AMMO, 0
            
        # 2. Build the map layout for the current level
        self.init_map()
        
        # 3. Spawn the player dynamically based on the map size
        self.player_x, self.player_y = 2.5 * TILE_SIZE, (self.map_size_y - 1.5) * TILE_SIZE
        self.player_angle, self.player_pitch = -math.pi / 2, 0.0
        
        # 4. Reset temporary game stats
        self.weapon_recoil, self.weapon_bob, self.screen_shake = 0.0, 0.0, 0.0
        self.damage_flash, self.muzzle_timer, self.last_shot = 0.0, 0, 0
        self.is_reloading, self.reload_timer = False, 0
        self.unlock_timers, self.active_doors, self.open_timers = {}, {}, {}
        
        self.tracers, self.enemies, self.pickups = [], [], []
        
        # Load entities from the current level
        lvl = levels.LEVELS[self.current_level]
        for sx, sy in lvl['SPAWN_LOCATIONS']:
            self.enemies.append({'x': sx * TILE_SIZE, 'y': sy * TILE_SIZE, 'health': ENEMY_HEALTH, 'state': 'chase', 'frame': 0, 'anim_timer': 0, 'hit_timer': 0})
        for px, py, pt in lvl['PICKUP_LOCATIONS']:
            self.pickups.append({'x': px * TILE_SIZE, 'y': py * TILE_SIZE, 'type': pt, 'collected': False})
            
        self.face_state, self.face_timer, self.player_facing_door = 'center', 0, False

    def get_compass_direction(self):
        dirs = ["E", "SE", "S", "SW", "W", "NW", "N", "NE"]
        angle = self.player_angle % (2 * math.pi)
        idx = int((angle + math.pi/8) / (math.pi/4)) % 8
        return dirs[idx]

    def reload_weapon(self):
        if self.ammo < MAX_AMMO and not self.is_reloading:
            self.is_reloading, self.reload_timer = True, 60

    # --- INPUT HANDLING ---
    def check_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if self.state == "menu": self.handle_menu_input(event)
            elif self.state == "profile_action_menu": self.handle_profile_action_input(event)
            elif self.state == "profile_select": self.handle_profile_select_input(event)
            elif self.state == "profile_create": self.handle_profile_create_input(event)
            elif self.state == "game": self.handle_game_input(event)
            elif self.state == "paused": self.handle_pause_input(event)
            elif self.state == "options": self.handle_options_input(event)
            elif self.state == "controls": self.handle_controls_input(event)
            
            # --- LEVEL TRANSITION & SAVE HOOK ---
            elif self.state in ["game_over", "level_complete"]:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    if self.state == "level_complete":
                        next_level = self.current_level + 1
                        if next_level >= len(levels.LEVELS):
                            self.current_level = 0
                            self.state = "menu"
                            pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                            return True
                        
                        # OVERWRITE PROFILE WITH NEW STATS AND NEXT LEVEL
                        if self.active_profile:
                            self.profiles[self.active_profile]["level"] = next_level
                            self.profiles[self.active_profile]["health"] = self.health
                            self.profiles[self.active_profile]["ammo"] = self.ammo
                            self.profiles[self.active_profile]["armor"] = self.armor
                            self.save_profiles()
                    
                    # Restart map or load next map (pulling from profile)
                    self.reset_game_data()
                    self.state = "game"
                    pygame.mouse.set_visible(False); pygame.event.set_grab(True)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: return False
                
        if self.state == "game": self.handle_movement(); self.handle_shooting()
        return True

    def handle_menu_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT: self.menu_selected = (self.menu_selected - 1) % len(self.menu_options)
            elif event.key == pygame.K_RIGHT: self.menu_selected = (self.menu_selected + 1) % len(self.menu_options)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE: self.execute_menu_action()
            elif event.key == pygame.K_ESCAPE: sys.exit()
        if event.type == pygame.MOUSEMOTION:
            mx, my = pygame.mouse.get_pos()
            for i, txt in enumerate(self.menu_options):
                w = self.custom_ui_font.size(txt)[0]
                if pygame.Rect(SCREEN_WIDTH*(0.25+i*0.25)-w//2, SCREEN_HEIGHT-55, w, 30).collidepoint(mx, my): self.menu_selected = i
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: self.execute_menu_action()

    def execute_menu_action(self):
        if self.menu_selected == 0: 
            self.state = "profile_action_menu" # Route to the profile menu!
            self.profile_action_selected = 0
        elif self.menu_selected == 1: self.state, self.previous_state, self.options_selected = "options", "menu", 0
        elif self.menu_selected == 2: sys.exit()

    # --- PROFILE MENU INPUTS ---
    def handle_profile_action_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: self.profile_action_selected = (self.profile_action_selected - 1) % len(self.profile_action_options)
            elif event.key == pygame.K_DOWN: self.profile_action_selected = (self.profile_action_selected + 1) % len(self.profile_action_options)
            elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                
                # CONTINUE
                if self.profile_action_selected == 0:
                    if not self.profiles: return 
                    self.state, self.profile_list_mode, self.profile_list_selected = "profile_select", "continue", 0
                # NEW PROFILE
                elif self.profile_action_selected == 1:
                    self.state, self.typing_name = "profile_create", ""
                # DELETE
                elif self.profile_action_selected == 2:
                    if not self.profiles: return
                    self.state, self.profile_list_mode, self.profile_list_selected = "profile_select", "delete", 0
                # BACK
                elif self.profile_action_selected == 3:
                    self.state = "menu"
            elif event.key == pygame.K_ESCAPE: self.state = "menu"

    def handle_profile_select_input(self, event):
        profiles_list = list(self.profiles.keys())
        if not profiles_list:
            self.state = "profile_action_menu"
            return
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: self.profile_list_selected = (self.profile_list_selected - 1) % len(profiles_list)
            elif event.key == pygame.K_DOWN: self.profile_list_selected = (self.profile_list_selected + 1) % len(profiles_list)
            elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                selected_name = profiles_list[self.profile_list_selected]
                
                if self.profile_list_mode == "continue":
                    self.active_profile = selected_name
                    self.state, self.loading_phase, self.loading_alpha = "loading", 0, 0
                elif self.profile_list_mode == "delete":
                    del self.profiles[selected_name]
                    self.save_profiles()
                    if not self.profiles: self.state = "profile_action_menu"
                    else: self.profile_list_selected = 0
            elif event.key == pygame.K_ESCAPE: self.state = "profile_action_menu"

    def handle_profile_create_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = "profile_action_menu"
            elif event.key == pygame.K_RETURN:
                if len(self.typing_name) > 0:
                    # Create a brand new default profile
                    self.profiles[self.typing_name] = {"level": 0, "health": MAX_HEALTH, "ammo": MAX_AMMO, "armor": 0}
                    self.save_profiles()
                    self.active_profile = self.typing_name
                    self.state, self.loading_phase, self.loading_alpha = "loading", 0, 0
            elif event.key == pygame.K_BACKSPACE:
                self.typing_name = self.typing_name[:-1]
            else:
                # Capture alphanumeric characters (up to 12)
                if event.unicode.isalnum() and len(self.typing_name) < 12:
                    self.typing_name += event.unicode.upper()

    def handle_pause_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: self.pause_selected = (self.pause_selected - 1) % len(self.pause_options)
            elif event.key == pygame.K_DOWN: self.pause_selected = (self.pause_selected + 1) % len(self.pause_options)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE: self.execute_pause_action()
            elif event.key == pygame.K_ESCAPE or event.key == pygame.K_p:
                self.state = "game"; pygame.mouse.set_visible(False); pygame.event.set_grab(True)

    def execute_pause_action(self):
        if self.pause_selected == 0: self.state = "game"; pygame.mouse.set_visible(False); pygame.event.set_grab(True)
        elif self.pause_selected == 1: self.state, self.previous_state, self.options_selected = "options", "paused", 0
        elif self.pause_selected == 2: self.reset_game_data(); self.state = "game"; pygame.mouse.set_visible(False); pygame.event.set_grab(True)
        elif self.pause_selected == 3: self.state = "menu"; pygame.mouse.set_visible(True); pygame.event.set_grab(False)
        elif self.pause_selected == 4: pygame.quit(); sys.exit()

    def handle_options_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: self.options_selected = (self.options_selected - 1) % len(self.options_menu)
            elif event.key == pygame.K_DOWN: self.options_selected = (self.options_selected + 1) % len(self.options_menu)
            elif event.key == pygame.K_LEFT:
                if self.options_selected == 0: self.mouse_sens = max(0.001, self.mouse_sens - 0.0005)
                elif self.options_selected == 1: self.crosshair_idx = (self.crosshair_idx - 1) % len(self.crosshair_colors)
                elif self.options_selected == 2: self.show_fps = not self.show_fps
            elif event.key == pygame.K_RIGHT:
                if self.options_selected == 0: self.mouse_sens = min(0.010, self.mouse_sens + 0.0005)
                elif self.options_selected == 1: self.crosshair_idx = (self.crosshair_idx + 1) % len(self.crosshair_colors)
                elif self.options_selected == 2: self.show_fps = not self.show_fps
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                if self.options_selected == 3: self.state = "controls"
                elif self.options_selected == 4: 
                    self.state = self.previous_state
                    if self.state == "game": pygame.mouse.set_visible(False); pygame.event.set_grab(True)
            elif event.key == pygame.K_ESCAPE:
                self.state = self.previous_state
                if self.state == "game": pygame.mouse.set_visible(False); pygame.event.set_grab(True)

    def handle_controls_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self.state = "options"

    def handle_game_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e: self.interact()
            if event.key == pygame.K_r: self.reload_weapon()
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_p:
                self.state, self.pause_selected = "paused", 0
                pygame.mouse.set_visible(True); pygame.event.set_grab(False)

    def handle_shooting(self):
        if pygame.mouse.get_pressed()[0]: self.fire_weapon()

    def handle_movement(self):
        mdx, mdy = pygame.mouse.get_rel()
        self.player_angle += mdx * self.mouse_sens
        self.player_pitch = max(-HALF_HEIGHT, min(HALF_HEIGHT, self.player_pitch - mdy * MOUSE_PITCH_SENSITIVITY))
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_w]: dx, dy = math.cos(self.player_angle)*PLAYER_SPEED, math.sin(self.player_angle)*PLAYER_SPEED
        if keys[pygame.K_s]: dx, dy = -math.cos(self.player_angle)*PLAYER_SPEED, -math.sin(self.player_angle)*PLAYER_SPEED
        if keys[pygame.K_a]: dx, dy = math.cos(self.player_angle-1.57)*(PLAYER_SPEED*0.7), math.sin(self.player_angle-1.57)*(PLAYER_SPEED*0.7)
        if keys[pygame.K_d]: dx, dy = math.cos(self.player_angle+1.57)*(PLAYER_SPEED*0.7), math.sin(self.player_angle+1.57)*(PLAYER_SPEED*0.7)
        if dx != 0 or dy != 0:
            self.weapon_bob += 0.2
            if not self.is_solid(int((self.player_x+dx+(1 if dx>0 else -1)*PLAYER_SIZE)/TILE_SIZE), int(self.player_y/TILE_SIZE)): self.player_x += dx
            if not self.is_solid(int(self.player_x/TILE_SIZE), int((self.player_y+dy+(1 if dy>0 else -1)*PLAYER_SIZE)/TILE_SIZE)): self.player_y += dy
        else: self.weapon_bob = 0.0

    def is_solid(self, x, y):
        if x < 0 or x >= self.map_size_x or y < 0 or y >= self.map_size_y: return True
        cell = self.world_map[x, y]
        return cell != 0 and not ((cell in [3, 4, self.green_switch_id]) and self.door_state[x, y] > 0.8)

    def interact(self):
        check_dist = TILE_SIZE * 1.0 
        gx = int((self.player_x + math.cos(self.player_angle) * check_dist) / TILE_SIZE)
        gy = int((self.player_y + math.sin(self.player_angle) * check_dist) / TILE_SIZE)
        
        if 0 <= gx < self.map_size_x and 0 <= gy < self.map_size_y:
            cell = self.world_map[gx, gy]
            if cell == 3 and self.door_lock[gx, gy] == 0: 
                self.door_lock[gx, gy] = 1
                self.world_map[gx, gy] = self.green_switch_id 
                self.unlock_timers[(gx, gy)] = pygame.time.get_ticks() + 1000 
            elif cell == 4 and self.door_state[gx, gy] < 0.1 and (gx, gy) not in self.unlock_timers: 
                self.world_map[gx, gy] = self.green_switch_id 
                self.unlock_timers[(gx, gy)] = pygame.time.get_ticks() + 1000 

    def update(self):
        if self.state != "game": return
        now = pygame.time.get_ticks()

        # --- WIN CONDITION: Progress North ---
        if self.player_y < 1.5 * TILE_SIZE:
            self.state = "level_complete"
            pygame.mouse.set_visible(True); pygame.event.set_grab(False)
        
        for p in self.pickups:
            if not p['collected'] and math.hypot(self.player_x - p['x'], self.player_y - p['y']) < 75:
                if p['type'] == 'health' and self.health < MAX_HEALTH: self.health = min(MAX_HEALTH, self.health + 25); p['collected'] = True
                elif p['type'] == 'ammo' and self.ammo < MAX_AMMO: self.ammo = min(MAX_AMMO, self.ammo + 20); p['collected'] = True
                elif p['type'] == 'armor' and self.armor < 100: self.armor = min(100, self.armor + 25); p['collected'] = True
        
        # Door automation
        for k in [k for k, t in self.unlock_timers.items() if now >= t]: self.active_doors[k], _ = 'opening', self.unlock_timers.pop(k)
        fin = []
        for k, s in self.active_doors.items():
            if s == 'opening': 
                self.door_state[k] += 0.03
                if self.door_state[k] >= 1.0: self.door_state[k], self.active_doors[k], self.open_timers[k] = 1.0, 'open', now + 5000
            elif s == 'closing': 
                self.door_state[k] -= 0.03
                if self.door_state[k] <= 0.0: 
                    self.door_state[k] = 0.0
                    fin.append(k)
                    if self.door_lock[k[0], k[1]] == 1: self.world_map[k[0], k[1]], self.door_lock[k[0], k[1]] = 3, 0
                    else: self.world_map[k[0], k[1]] = 4 
                        
        for k in fin: del self.active_doors[k]
        for k in [k for k, t in self.open_timers.items() if now >= t and math.hypot(self.player_x-(k[0]+0.5)*TILE_SIZE, self.player_y-(k[1]+0.5)*TILE_SIZE) > TILE_SIZE]: self.active_doors[k], _ = 'closing', self.open_timers.pop(k)
        
        gx, gy = int((self.player_x+math.cos(self.player_angle)*TILE_SIZE*1.0)/TILE_SIZE), int((self.player_y+math.sin(self.player_angle)*TILE_SIZE*1.0)/TILE_SIZE)
        if 0 <= gx < self.map_size_x and 0 <= gy < self.map_size_y: self.player_facing_door = (self.world_map[gx, gy] in [3, 4]) and self.door_state[gx, gy] < 0.1
        else: self.player_facing_door = False

        for e in self.enemies:
            if e['health'] <= 0: continue
            e['anim_timer'] += 1
            if e['anim_timer'] > 20: e['anim_timer'], e['frame'] = 0, 1 - e['frame']
            d = math.hypot(self.player_x - e['x'], self.player_y - e['y'])
            if d > 40:
                nx, ny = (self.player_x-e['x'])/d, (self.player_y-e['y'])/d
                if self.world_map[int((e['x']+nx*ENEMY_SPEED)//TILE_SIZE), int(e['y']//TILE_SIZE)] == 0: e['x'] += nx*ENEMY_SPEED
                if self.world_map[int(e['x']//TILE_SIZE), int((e['y']+ny*ENEMY_SPEED)//TILE_SIZE)] == 0: e['y'] += ny*ENEMY_SPEED
            else:
                self.health -= ENEMY_DAMAGE; self.damage_flash, self.screen_shake = 120, 15
                if self.health <= 0: self.state = "game_over"

        if self.is_reloading: 
            self.reload_timer -= 1
            if self.reload_timer <= 0: self.is_reloading, self.ammo = False, MAX_AMMO
        self.damage_flash, self.screen_shake = max(0, self.damage_flash-5), self.screen_shake*0.9 if self.screen_shake > 1 else 0
        self.weapon_recoil, self.muzzle_timer = max(0, self.weapon_recoil-2), max(0, self.muzzle_timer-1)
        self.face_timer -= 1
        if self.face_timer <= 0:
            if self.face_state == 'center': self.face_state, self.face_timer = random.choice(['left', 'right']), FACE_LOOK_TIME
            else: self.face_state, self.face_timer = 'center', random.randint(FACE_IDLE_MIN, FACE_IDLE_MAX)

    def fire_weapon(self):
        now = pygame.time.get_ticks()
        if self.is_reloading or self.ammo <= 0 or now - self.last_shot < FIRE_RATE: return
        self.last_shot, self.ammo, self.weapon_recoil, self.screen_shake, self.muzzle_timer = now, self.ammo - 1, RECOIL_FORCE, 10.0, 5
        self.player_pitch += 10.0
        self.tracers.append({'x': SCREEN_WIDTH//2 + random.randint(-10, 10), 'y': HALF_HEIGHT + random.randint(-10, 10), 'life': 5})
        pc, ps = math.cos(self.player_angle), math.sin(self.player_angle)
        for e in self.enemies:
            if e['health'] > 0 and (e['x']-self.player_x)*pc + (e['y']-self.player_y)*ps > 0 and abs((e['y']-self.player_y)*pc - (e['x']-self.player_x)*ps) < 30:
                e['health'] -= 20; e['hit_timer'] = 5; return

    # --- RENDERING ---
    def draw(self):
        if self.state == "menu":
            self.screen.blit(self.assets.images['menu_bg'], (0,0))
            pygame.draw.rect(self.screen, (0,0,0), (0, SCREEN_HEIGHT-80, SCREEN_WIDTH, 80))
            self.screen.blit(self.assets.images['menu_logo'], ((SCREEN_WIDTH-self.assets.images['menu_logo'].get_width())//2, SCREEN_HEIGHT-80-self.assets.images['menu_logo'].get_height()))
            for i, txt in enumerate(self.menu_options):
                color = MENU_TEXT_HOVER if i == self.menu_selected else MENU_TEXT_COLOR
                surf = self.custom_ui_font.render(txt, True, color)
                self.screen.blit(surf, (SCREEN_WIDTH*(0.25+i*0.25)-surf.get_width()//2, SCREEN_HEIGHT-55))
        
        elif self.state in ["profile_action_menu", "profile_select", "profile_create"]:
            self.screen.blit(self.assets.images['menu_bg'], (0,0))
            ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); ov.fill((0,0,0)); ov.set_alpha(150); self.screen.blit(ov, (0,0))
            
            if self.state == "profile_action_menu":
                ts = self.assets.fonts['death'].render("PROFILES", True, DOOM_GOLD)
                self.screen.blit(ts, (SCREEN_WIDTH//2 - ts.get_width()//2, 80))
                for i, txt in enumerate(self.profile_action_options):
                    # Gray out CONTINUE and DELETE if no profiles exist
                    if (txt == "CONTINUE" or txt == "DELETE PROFILE") and not self.profiles:
                        color = (100, 100, 100) 
                    else:
                        color = MENU_TEXT_HOVER if i == self.profile_action_selected else (160, 160, 160)
                    surf = self.custom_ui_font.render(f">  {txt}  <" if i == self.profile_action_selected else txt, True, color)
                    self.screen.blit(surf, (SCREEN_WIDTH//2 - surf.get_width()//2, 220 + i * 60))
            
            elif self.state == "profile_select":
                title = "SELECT PROFILE" if self.profile_list_mode == "continue" else "DELETE PROFILE"
                ts = self.assets.fonts['death'].render(title, True, DOOM_GOLD if self.profile_list_mode == "continue" else DOOM_RED)
                self.screen.blit(ts, (SCREEN_WIDTH//2 - ts.get_width()//2, 80))
                
                profiles_list = list(self.profiles.keys())
                for i, name in enumerate(profiles_list):
                    color = MENU_TEXT_HOVER if i == self.profile_list_selected else (160, 160, 160)
                    p_data = self.profiles[name]
                    txt = f"{name} - LVL {p_data['level']+1}"
                    txt = f">  {txt}  <" if i == self.profile_list_selected else txt
                    surf = self.custom_ui_font.render(txt, True, color)
                    self.screen.blit(surf, (SCREEN_WIDTH//2 - surf.get_width()//2, 220 + i * 50))
            
            elif self.state == "profile_create":
                ts = self.assets.fonts['death'].render("NEW PROFILE", True, DOOM_GOLD)
                self.screen.blit(ts, (SCREEN_WIDTH//2 - ts.get_width()//2, 80))
                prompt = self.custom_ui_font.render("ENTER NAME:", True, (200, 200, 200))
                self.screen.blit(prompt, (SCREEN_WIDTH//2 - prompt.get_width()//2, 250))
                
                # Blinking cursor effect
                cursor = "_" if pygame.time.get_ticks() % 1000 < 500 else ""
                name_surf = self.custom_ui_font.render(self.typing_name + cursor, True, DOOM_RED)
                self.screen.blit(name_surf, (SCREEN_WIDTH//2 - name_surf.get_width()//2, 320))

        elif self.state == "loading":
            self.screen.fill((0,0,0)); img = self.assets.images['loading'].copy(); img.set_alpha(int(self.loading_alpha)); self.screen.blit(img, (0,0))
            if self.loading_phase == 0:
                self.loading_alpha += self.fade_speed
                if self.loading_alpha >= 255: self.loading_alpha, self.loading_phase, self.loading_timer = 255, 1, pygame.time.get_ticks()
            elif self.loading_phase == 1 and pygame.time.get_ticks() - self.loading_timer > 2000: self.loading_phase = 2
            elif self.loading_phase == 2:
                self.loading_alpha -= self.fade_speed
                if self.loading_alpha <= 0: 
                    self.reset_game_data()
                    self.state = "game"
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
        
        elif self.state in ["game", "paused", "game_over", "level_complete", "options", "controls"]:
            # Render World
            raycaster.render_kernel(self.player_x, self.player_y, self.player_angle, self.player_pitch, self.world_map, self.door_state, self.door_lock, self.door_dir, self.assets.wall_textures, self.assets.floor_texture, self.assets.ceil_texture, self.screen_buffer, self.depth_buffer)
            sx, sy = (random.randint(-int(self.screen_shake), int(self.screen_shake)), random.randint(-int(self.screen_shake), int(self.screen_shake))) if self.screen_shake > 0 else (0,0)
            self.screen.blit(pygame.surfarray.make_surface(self.screen_buffer), (sx, sy))
            
            # Draw Compass
            if self.state == "game":
                dir_text = self.get_compass_direction()
                compass_surf = self.compass_font.render(dir_text, True, (245, 245, 220))
                self.screen.blit(compass_surf, (25, 25))

            pc, ps = math.cos(self.player_angle), math.sin(self.player_angle)
            to_draw = []
            for e in self.enemies:
                if e['health'] > 0:
                    d = (e['x']-self.player_x)*pc + (e['y']-self.player_y)*ps
                    if d > 10: to_draw.append((d, e, 'enemy'))
            for p in self.pickups:
                if not p['collected']:
                    d = (p['x']-self.player_x)*pc + (p['y']-self.player_y)*ps
                    if d > 10: to_draw.append((d, p, 'pickup'))
            
            to_draw.sort(key=lambda x: x[0], reverse=True)
            for depth, obj, st in to_draw:
                lat = (obj['y']-self.player_y)*pc - (obj['x']-self.player_x)*ps
                scale = SCREEN_HEIGHT / (depth / TILE_SIZE)
                scx, scy = int(SCREEN_WIDTH/2+(lat/depth)*(SCREEN_WIDTH/2/math.tan(HALF_FOV))), int(HALF_HEIGHT+self.player_pitch+(0.5*SCREEN_HEIGHT/(depth/TILE_SIZE)))
                if 0 <= scx < SCREEN_WIDTH and depth/TILE_SIZE < self.depth_buffer[scx] + 0.3:
                    if st == 'enemy':
                        tex = self.assets.enemy_frames[obj['frame']]
                        sw, sh = int(scale*0.7*(tex.get_width()/tex.get_height())), int(scale*0.7)
                        self.screen.blit(pygame.transform.scale(tex, (sw, sh)), (scx-sw//2+sx, scy-sh+sy))
                    
                    # --- SPRITE PICKUP RENDERING ---
                    else:
                        sprite = self.assets.images[f"{obj['type']}_pickup"]
                        pw, ph = int(scale * 0.4), int(scale * 0.4)
                        self.screen.blit(pygame.transform.scale(sprite, (pw, ph)), (scx - pw//2 + sx, scy - ph//2 + sy))

            if self.damage_flash > 0:
                f = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); f.fill((255,0,0)); f.set_alpha(int(self.damage_flash)); self.screen.blit(f, (0,0))

            gun = self.assets.images['gun_fire'] if self.muzzle_timer > 0 else self.assets.images['gun_default']
            roff = math.sin((1-self.reload_timer/60)*math.pi)*200 if self.is_reloading else 0
            gx = (SCREEN_WIDTH//2) - (gun.get_width()//2) + 180 + math.cos(self.weapon_bob)*10 + sx
            gy = SCREEN_HEIGHT - gun.get_height() + 40 + abs(math.sin(self.weapon_bob))*10 + self.weapon_recoil + sy + roff
            self.screen.blit(gun, (gx, gy))
            
            for t in self.tracers:
                pygame.draw.line(self.screen, (255,255,0), (gx + gun.get_width() * 0.3, gy + gun.get_height() * 0.2), (t['x']+sx, t['y']+sy), 2)
                t['life'] -= 1
            self.tracers = [t for t in self.tracers if t['life'] > 0]

            self.screen.blit(self.assets.images['hud_bg'], (0, SCREEN_HEIGHT-HUD_HEIGHT))
            pygame.draw.line(self.screen, DOOM_BEVEL_LIGHT, (0, SCREEN_HEIGHT-HUD_HEIGHT), (SCREEN_WIDTH, SCREEN_HEIGHT-HUD_HEIGHT), 3)
            
            def db(x, l, v, p=False):
                r = pygame.Rect(x, SCREEN_HEIGHT-HUD_HEIGHT+15, 100, HUD_HEIGHT-30)
                pygame.draw.rect(self.screen, DOOM_BEVEL_DARK, r); pygame.draw.rect(self.screen, DOOM_BEVEL_LIGHT, r, 2)
                ls = self.custom_ui_font_small.render(l, True, DOOM_GOLD); self.screen.blit(ls, (r.x+(r.w-ls.get_width())//2, r.y+4))
                vs = self.custom_ui_font.render(f"{int(v)}{'%' if p else ''}", True, DOOM_RED); self.screen.blit(vs, (r.x+(r.w-vs.get_width())//2, r.y+18))

            db(20, "AMMO", self.ammo); db(140, "HEALTH", self.health, True); db(SCREEN_WIDTH-260, "ARMOR", self.armor, True)
            fr = pygame.Rect(SCREEN_WIDTH//2-40, SCREEN_HEIGHT-HUD_HEIGHT+10, 80, 80); pygame.draw.rect(self.screen, (0,0,0), fr)
            self.screen.blit(self.assets.faces[self.face_state], (fr.x+8, fr.y+8)); pygame.draw.rect(self.screen, DOOM_BEVEL_LIGHT, fr, 3)

            # Draw Interaction Text
            if self.player_facing_door and self.state == "game":
                itxt = self.custom_ui_font_small.render("Press E to Open", True, (255, 255, 255))
                self.screen.blit(itxt, (SCREEN_WIDTH//2 - itxt.get_width()//2, HALF_HEIGHT + 60))

            # Render Crosshair
            if self.state == "game":
                c = self.crosshair_colors[self.crosshair_idx][0]
                cx, cy, g, l = SCREEN_WIDTH//2, HALF_HEIGHT, 6, 12
                pygame.draw.line(self.screen, c, (cx, cy-g-l), (cx, cy-g), 2); pygame.draw.line(self.screen, c, (cx, cy+g), (cx, cy+g+l), 2)
                pygame.draw.line(self.screen, c, (cx-g-l, cy), (cx-g, cy), 2); pygame.draw.line(self.screen, c, (cx+g, cy), (cx+g+l, cy), 2)
                
                # Render FPS if enabled
                if self.show_fps:
                    fps_txt = self.custom_ui_font_small.render(f"FPS: {int(self.clock.get_fps())}", True, (0, 255, 0))
                    self.screen.blit(fps_txt, (SCREEN_WIDTH - 100, 20))

            # Overlays
            if self.state in ["paused", "options", "controls"]:
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); ov.set_alpha(200); ov.fill((10, 5, 5)); self.screen.blit(ov, (0,0))
                
                if self.state == "paused":
                    ps = self.assets.fonts['death'].render("PAUSED", True, DOOM_RED)
                    self.screen.blit(ps, (SCREEN_WIDTH//2 - ps.get_width()//2, 80))
                    for i, opt in enumerate(self.pause_options):
                        is_s = (i == self.pause_selected)
                        clr = MENU_TEXT_HOVER if is_s else (160, 160, 160)
                        txt = f">  {opt}  <" if is_s else opt
                        os = self.custom_ui_font.render(txt, True, clr) 
                        self.screen.blit(os, (SCREEN_WIDTH//2 - os.get_width()//2, 220 + i * 50))
                
                elif self.state == "options":
                    ts = self.assets.fonts['death'].render("OPTIONS", True, DOOM_GOLD)
                    self.screen.blit(ts, (SCREEN_WIDTH//2 - ts.get_width()//2, 60))
                    
                    for i, opt in enumerate(self.options_menu):
                        is_s = (i == self.options_selected)
                        clr = MENU_TEXT_HOVER if is_s else (160, 160, 160)
                        
                        # Dynamically build the text based on current settings
                        display_text = opt
                        if i == 0: display_text += f" < {round(self.mouse_sens, 4)} >"
                        elif i == 1: display_text += f" < {self.crosshair_colors[self.crosshair_idx][1]} >"
                        elif i == 2: display_text += f" < {'ON' if self.show_fps else 'OFF'} >"
                        
                        txt = f">  {display_text}  <" if is_s else display_text
                        os = self.custom_ui_font.render(txt, True, clr) 
                        self.screen.blit(os, (SCREEN_WIDTH//2 - os.get_width()//2, 180 + i * 60))

                elif self.state == "controls":
                    ts = self.assets.fonts['death'].render("CONTROLS", True, DOOM_GOLD)
                    self.screen.blit(ts, (SCREEN_WIDTH//2 - ts.get_width()//2, 60))
                    for i, line in enumerate(self.controls_text):
                        cs = self.custom_ui_font.render(line, True, (200, 200, 200))
                        self.screen.blit(cs, (SCREEN_WIDTH//2 - cs.get_width()//2, 160 + i * 45))
                    bs = self.custom_ui_font_small.render("Press SPACE or ESC to return", True, MENU_TEXT_HOVER)
                    self.screen.blit(bs, (SCREEN_WIDTH//2 - bs.get_width()//2, SCREEN_HEIGHT - 100))

            if self.state == "game_over":
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); ov.fill((0,0,0)); ov.set_alpha(180); self.screen.blit(ov, (0,0))
                ds = self.assets.fonts['death'].render("YOU DIED", True, (150,0,0)); self.screen.blit(ds, (SCREEN_WIDTH//2-ds.get_width()//2, HALF_HEIGHT-50))
                rs = self.assets.fonts['restart'].render("Press SPACE to Restart", True, (200,200,200)); self.screen.blit(rs, (SCREEN_WIDTH//2-rs.get_width()//2, HALF_HEIGHT+50))

            if self.state == "level_complete":
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); ov.fill((0,0,0)); ov.set_alpha(180); self.screen.blit(ov, (0,0))
                ds = self.custom_ui_font.render("MISSION ACCOMPLISHED", True, (0, 255, 100))
                self.screen.blit(ds, (SCREEN_WIDTH//2-ds.get_width()//2, HALF_HEIGHT-50))
                
                # Check if there are more levels to change the spacebar text
                msg = "Press SPACE to Continue" if self.current_level < len(levels.LEVELS) - 1 else "Press SPACE to Finish"
                rs = self.custom_ui_font_small.render(msg, True, (200,200,200))
                self.screen.blit(rs, (SCREEN_WIDTH//2-rs.get_width()//2, HALF_HEIGHT+50))

        pygame.display.flip()

    def run(self):
        while self.check_input(): self.update(); self.draw(); self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    game = Game(); game.run()
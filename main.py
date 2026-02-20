import pygame
import math
import numpy as np
import random
import sys

# Import our new modules
from settings import *
import assets
import raycaster

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
        
        # Game State
        self.state = "menu"
        self.menu_selected = 0
        self.menu_options = ["START GAME", "OPTIONS", "EXIT"]
        
        # Loading Vars
        self.loading_phase = 0
        self.loading_alpha = 0
        self.loading_timer = 0
        self.fade_speed = 5

        # Initialize Map
        self.init_map()
        self.reset_game_data()
        
        # Screen Buffers
        self.screen_buffer = np.zeros((SCREEN_WIDTH, SCREEN_HEIGHT, 3), dtype=np.int32)
        self.depth_buffer = np.zeros(SCREEN_WIDTH, dtype=np.float32)

    def init_map(self):
        self.world_map = np.zeros((MAP_SIZE_X, MAP_SIZE_Y), dtype=np.int32)
        self.door_state = np.zeros((MAP_SIZE_X, MAP_SIZE_Y), dtype=np.float32) 
        self.door_lock = np.zeros((MAP_SIZE_X, MAP_SIZE_Y), dtype=np.int32)
        self.door_dir = np.zeros((MAP_SIZE_X, MAP_SIZE_Y), dtype=np.int32) 
        
        for j, char in enumerate(MAP_STRING):
            x, y = j % MAP_SIZE_X, j // MAP_SIZE_X
            val = int(char)
            self.world_map[x, y] = val
            
            # --- AUTO-DETECT DOOR ORIENTATION ---
            if val == 4:
                left = self.world_map[x-1, y] if x > 0 else 0
                right = self.world_map[x+1, y] if x < MAP_SIZE_X-1 else 0
                
                # If walls are Left/Right, it's a Vertical Corridor -> Horizontal Door (1)
                if left != 0 and right != 0:
                    self.door_dir[x, y] = 1 
                else:
                    self.door_dir[x, y] = 0

    def reset_game_data(self):
        # NEW SPAWN POINT: Bottom Left Room (Safe Zone)
        self.player_x = 2.5 * TILE_SIZE
        self.player_y = 22.5 * TILE_SIZE
        self.player_angle = -math.pi / 2 # Start Facing North
        self.player_pitch = 0.0
        
        self.health = MAX_HEALTH
        self.ammo = MAX_AMMO
        self.armor = 0
        
        self.weapon_recoil = 0.0
        self.weapon_bob = 0.0
        self.screen_shake = 0.0
        self.damage_flash = 0.0
        self.muzzle_timer = 0
        self.last_shot = 0
        self.is_reloading = False
        self.reload_timer = 0
        self.is_firing = False
        
        self.unlock_timers = {}
        self.active_doors = {}
        self.open_timers = {}
        
        self.tracers = []
        self.bullet_holes = []
        
        # Spawn Enemies
        self.enemies = []
        for sx, sy in SPAWN_LOCATIONS:
            self.enemies.append({
                'x': sx * TILE_SIZE, 'y': sy * TILE_SIZE,
                'health': ENEMY_HEALTH, 'state': 'chase',
                'frame': 0, 'anim_timer': 0, 'hit_timer': 0
            })
            
        self.face_state = 'center'
        self.face_timer = 0
        self.player_facing_door = False

    def check_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if self.state == "menu":
                self.handle_menu_input(event)
            elif self.state == "game":
                self.handle_game_input(event)
            elif self.state == "game_over":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE: 
                        self.reset_game_data()
                        self.state = "game"
                        pygame.mouse.set_visible(False); pygame.event.set_grab(True)
                    if event.key == pygame.K_ESCAPE: return False

        # Continuous Input (Movement & Shooting)
        if self.state == "game":
            self.handle_movement()
            self.handle_shooting()
            
        return True

    def handle_menu_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT: self.menu_selected = (self.menu_selected - 1) % 3
            elif event.key == pygame.K_RIGHT: self.menu_selected = (self.menu_selected + 1) % 3
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self.execute_menu_action()
            elif event.key == pygame.K_ESCAPE: sys.exit()
        
        if event.type == pygame.MOUSEMOTION:
            bar_height = 80
            y_pos = SCREEN_HEIGHT - bar_height + (bar_height // 2) - 15
            mx, my = pygame.mouse.get_pos()
            for i, txt in enumerate(self.menu_options):
                t_surf = self.assets.fonts['menu'].render(txt, True, (255,255,255))
                if i == 0: x = SCREEN_WIDTH * 0.25 - t_surf.get_width()//2
                elif i == 1: x = SCREEN_WIDTH * 0.5 - t_surf.get_width()//2
                else: x = SCREEN_WIDTH * 0.75 - t_surf.get_width()//2
                if pygame.Rect(x, y_pos, t_surf.get_width(), t_surf.get_height()).collidepoint(mx, my):
                    self.menu_selected = i
                    
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.execute_menu_action()

    def execute_menu_action(self):
        if self.menu_selected == 0: # Start
            self.state = "loading"
            self.loading_phase = 0
            self.loading_alpha = 0
        elif self.menu_selected == 2: # Exit
            sys.exit()

    def handle_game_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e: self.interact()
            if event.key == pygame.K_r: self.reload_weapon()
            if event.key == pygame.K_ESCAPE:
                self.state = "menu"
                pygame.mouse.set_visible(True); pygame.event.set_grab(False)

    def handle_shooting(self):
        if pygame.mouse.get_pressed()[0]:
            self.fire_weapon()

    def handle_movement(self):
        mouse_dx, mouse_dy = pygame.mouse.get_rel()
        self.player_angle += mouse_dx * MOUSE_SENSITIVITY
        self.player_pitch -= mouse_dy * MOUSE_PITCH_SENSITIVITY
        self.player_pitch = max(-HALF_HEIGHT, min(HALF_HEIGHT, self.player_pitch))
        
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_w]: dx = math.cos(self.player_angle) * PLAYER_SPEED; dy = math.sin(self.player_angle) * PLAYER_SPEED
        if keys[pygame.K_s]: dx = -math.cos(self.player_angle) * PLAYER_SPEED; dy = -math.sin(self.player_angle) * PLAYER_SPEED
        if keys[pygame.K_a]: dx = math.cos(self.player_angle - math.pi/2) * (PLAYER_SPEED*0.7); dy = math.sin(self.player_angle - math.pi/2) * (PLAYER_SPEED*0.7)
        if keys[pygame.K_d]: dx = math.cos(self.player_angle + math.pi/2) * (PLAYER_SPEED*0.7); dy = math.sin(self.player_angle + math.pi/2) * (PLAYER_SPEED*0.7)
        
        if dx != 0 or dy != 0:
            self.weapon_bob += 0.2
            
            # --- IMPROVED COLLISION (X-AXIS) ---
            new_x = self.player_x + dx
            sign_x = 1 if dx > 0 else -1
            check_x_grid = int((new_x + sign_x * PLAYER_SIZE) / TILE_SIZE)
            top_y_grid = int((self.player_y - PLAYER_SIZE) / TILE_SIZE)
            bot_y_grid = int((self.player_y + PLAYER_SIZE) / TILE_SIZE)
            
            if not self.is_solid(check_x_grid, top_y_grid) and not self.is_solid(check_x_grid, bot_y_grid):
                self.player_x += dx

            # --- IMPROVED COLLISION (Y-AXIS) ---
            new_y = self.player_y + dy
            sign_y = 1 if dy > 0 else -1
            check_y_grid = int((new_y + sign_y * PLAYER_SIZE) / TILE_SIZE)
            left_x_grid = int((self.player_x - PLAYER_SIZE) / TILE_SIZE)
            right_x_grid = int((self.player_x + PLAYER_SIZE) / TILE_SIZE)
            
            if not self.is_solid(left_x_grid, check_y_grid) and not self.is_solid(right_x_grid, check_y_grid):
                self.player_y += dy
        else:
            self.weapon_bob = 0.0

    def is_solid(self, x, y):
        # 1. Bounds Check
        if x < 0 or x >= MAP_SIZE_X or y < 0 or y >= MAP_SIZE_Y:
            return True
        
        # 2. Wall Check
        cell = self.world_map[x, y]
        if cell == 0: 
            return False # Empty air
            
        # 3. Door Check
        if (cell in [3, 4]) and self.door_state[x, y] > 0.8:
            return False
            
        return True

    def check_facing(self):
        check = TILE_SIZE * 1.5
        gx = int((self.player_x + math.cos(self.player_angle) * check) / TILE_SIZE)
        gy = int((self.player_y + math.sin(self.player_angle) * check) / TILE_SIZE)
        if 0 <= gx < MAP_SIZE_X and 0 <= gy < MAP_SIZE_Y:
            c = self.world_map[gx, gy]
            if (c == 3 or c == 4) and self.door_state[gx, gy] < 0.1:
                self.player_facing_door = True
            else:
                self.player_facing_door = False
        else:
            self.player_facing_door = False

    def interact(self):
        check = TILE_SIZE * 1.5
        fx = self.player_x + math.cos(self.player_angle) * check
        fy = self.player_y + math.sin(self.player_angle) * check
        gx, gy = int(fx / TILE_SIZE), int(fy / TILE_SIZE)
        if 0 <= gx < MAP_SIZE_X and 0 <= gy < MAP_SIZE_Y:
            cell = self.world_map[gx, gy]
            if cell == 3:
                if self.door_lock[gx, gy] == 0: 
                    self.door_lock[gx, gy] = 1
                    self.unlock_timers[(gx, gy)] = pygame.time.get_ticks() + 1000
            elif cell == 4:
                if self.door_state[gx, gy] < 0.1:
                    tile_cy = (gy + 0.5) * TILE_SIZE
                    self.active_doors[(gx, gy)] = 'opening'

    def update(self):
        now = pygame.time.get_ticks()
        
        # Face Anim
        self.face_timer -= 1
        if self.face_timer <= 0:
            if self.face_state == 'center':
                self.face_state = random.choice(['left', 'right'])
                self.face_timer = FACE_LOOK_TIME
            else:
                self.face_state = 'center'
                self.face_timer = random.randint(FACE_IDLE_MIN, FACE_IDLE_MAX)

        # Doors
        ready = []
        for k, t in self.unlock_timers.items():
            if now >= t: self.active_doors[k] = 'opening'; ready.append(k)
        for k in ready: del self.unlock_timers[k]
        
        finished_anim = []
        for (gx, gy), state in self.active_doors.items():
            if state == 'opening':
                self.door_state[gx, gy] += 0.03
                if self.door_state[gx, gy] >= 1.0:
                    self.door_state[gx, gy] = 1.0; self.active_doors[(gx, gy)] = 'open'
                    self.open_timers[(gx, gy)] = now + 5000
            elif state == 'closing':
                self.door_state[gx, gy] -= 0.03
                if self.door_state[gx, gy] <= 0.0:
                    self.door_state[gx, gy] = 0.0; finished_anim.append((gx, gy))
                    if self.world_map[gx, gy] == 3: self.door_lock[gx, gy] = 0
        for k in finished_anim: del self.active_doors[k]
        
        closing_soon = []
        for (gx, gy), t in self.open_timers.items():
            dist = math.hypot(self.player_x - (gx+0.5)*TILE_SIZE, self.player_y - (gy+0.5)*TILE_SIZE)
            if now >= t and dist > TILE_SIZE: self.active_doors[(gx, gy)] = 'closing'; closing_soon.append((gx, gy))
        for k in closing_soon: del self.open_timers[k]

        # Check Facing Door
        self.check_facing()

        # Enemies
        for enemy in self.enemies:
            if enemy['health'] <= 0: continue
            enemy['anim_timer'] += 1
            if enemy['anim_timer'] > 20: enemy['anim_timer'] = 0; enemy['frame'] = 1 - enemy['frame']
            
            dx = self.player_x - enemy['x']; dy = self.player_y - enemy['y']
            dist = math.hypot(dx, dy)
            
            if dist > 40:
                dx /= dist; dy /= dist
                cx = enemy['x'] + dx * ENEMY_SPEED
                if self.world_map[int(cx//TILE_SIZE), int(enemy['y']//TILE_SIZE)] == 0: enemy['x'] = cx
                cy = enemy['y'] + dy * ENEMY_SPEED
                if self.world_map[int(enemy['x']//TILE_SIZE), int(cy//TILE_SIZE)] == 0: enemy['y'] = cy
            elif dist < 50:
                self.health -= ENEMY_DAMAGE
                self.damage_flash = 120; self.screen_shake = 15; self.player_pitch -= 5
                if self.health <= 0: self.health = 0; self.state = "game_over"

        # Weapons
        if self.is_reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0: self.is_reloading = False; self.ammo = MAX_AMMO
        if self.damage_flash > 0: self.damage_flash -= 5
        if self.screen_shake > 0: self.screen_shake *= 0.9; 
        if self.screen_shake < 1.0: self.screen_shake = 0
        if self.weapon_recoil > 0: self.weapon_recoil -= 2
        if self.muzzle_timer > 0: self.muzzle_timer -= 1

    def reload_weapon(self):
        if self.ammo < MAX_AMMO and not self.is_reloading: self.is_reloading = True; self.reload_timer = 60

    def shoot_ray(self, p_x, p_y, p_angle, pitch):
        sin_a = math.sin(p_angle); cos_a = math.cos(p_angle)
        map_x = int(p_x // TILE_SIZE); map_y = int(p_y // TILE_SIZE)
        delta_dist_x = abs(1 / (cos_a + 1e-30)); delta_dist_y = abs(1 / (sin_a + 1e-30))
        step_x = 1 if cos_a >= 0 else -1; side_dist_x = (map_x + 1.0 - p_x / TILE_SIZE) * delta_dist_x if cos_a >= 0 else (p_x / TILE_SIZE - map_x) * delta_dist_x
        step_y = 1 if sin_a >= 0 else -1; side_dist_y = (map_y + 1.0 - p_y / TILE_SIZE) * delta_dist_y if sin_a >= 0 else (p_y / TILE_SIZE - map_y) * delta_dist_y
        hit = False; side = 0; hit_x, hit_y = 0, 0; hit_dist = 0.0
        while not hit:
            if side_dist_x < side_dist_y: side_dist_x += delta_dist_x; map_x += step_x; side = 0
            else: side_dist_y += delta_dist_y; map_y += step_y; side = 1
            if map_x < 0 or map_x >= MAP_SIZE_X or map_y < 0 or map_y >= MAP_SIZE_Y: return None 
            if self.world_map[map_x, map_y] > 0:
                hit = True
                if side == 0: hit_dist = side_dist_x - delta_dist_x
                else: hit_dist = side_dist_y - delta_dist_y
                hit_x = p_x + cos_a * hit_dist * TILE_SIZE; hit_y = p_y + sin_a * hit_dist * TILE_SIZE
                hit_height = 0.5 + (pitch * hit_dist / SCREEN_HEIGHT)
                if hit_height < 0.0 or hit_height > 1.0: return None
                return {'x': hit_x, 'y': hit_y, 'z': hit_height, 'dist': hit_dist, 'time': pygame.time.get_ticks()}
        return None

    def draw_bullet_holes(self):
        current_time = pygame.time.get_ticks()
        to_remove = []
        horizon = HALF_HEIGHT + self.player_pitch
        
        for i, hole in enumerate(self.bullet_holes):
            if current_time - hole['time'] > 5000: to_remove.append(i); continue
            dx = hole['x'] - self.player_x; dy = hole['y'] - self.player_y
            
            p_cos = math.cos(self.player_angle)
            p_sin = math.sin(self.player_angle)
            
            depth = dx * p_cos + dy * p_sin; lateral = dx * p_sin - dy * p_cos
            if depth <= 0.1: continue
            scale_x = (SCREEN_WIDTH / 2) / math.tan(HALF_FOV) 
            screen_x = int((SCREEN_WIDTH / 2) + (lateral / depth) * scale_x)
            hit_h = hole['z']
            screen_y = int(horizon + (0.5 - hit_h) * (SCREEN_HEIGHT / depth))
            if 0 <= screen_x < SCREEN_WIDTH:
                dist_tiles = depth / TILE_SIZE
                if screen_x < len(self.depth_buffer) and dist_tiles < self.depth_buffer[screen_x] + 0.5:
                    size = int(800 / depth) 
                    if size < 2: continue 
                    if size > 60: size = 60
                    
                    sx = int(random.randint(-int(self.screen_shake), int(self.screen_shake))) if self.screen_shake > 0 else 0
                    sy = int(random.randint(-int(self.screen_shake), int(self.screen_shake))) if self.screen_shake > 0 else 0
                    
                    scaled_hole = pygame.transform.scale(self.assets.images['hole'], (size, size))
                    rect = scaled_hole.get_rect(center=(screen_x + sx, screen_y + sy))
                    self.screen.blit(scaled_hole, rect)
        
        for i in reversed(to_remove): self.bullet_holes.pop(i)

    def fire_weapon(self):
        now = pygame.time.get_ticks()
        if self.is_reloading or self.ammo <= 0 or now - self.last_shot < FIRE_RATE: return
        self.last_shot = now
        self.ammo -= 1
        self.weapon_recoil = RECOIL_FORCE
        self.screen_shake = 10.0
        self.muzzle_timer = 5
        self.player_pitch += 10.0
        
        end_x = SCREEN_WIDTH // 2 + random.randint(-10, 10)
        end_y = HALF_HEIGHT + random.randint(-10, 10)
        self.tracers.append({'x': end_x, 'y': end_y, 'life': 5}) 

        p_cos = math.cos(self.player_angle); p_sin = math.sin(self.player_angle)
        hit_enemy = False
        for enemy in self.enemies:
            if enemy['health'] <= 0: continue
            dx = enemy['x'] - self.player_x; dy = enemy['y'] - self.player_y
            depth = dx * p_cos + dy * p_sin; lateral = dx * p_sin - dy * p_cos
            if depth > 0 and abs(lateral) < 30:
                enemy['health'] -= 20; enemy['hit_timer'] = 5; hit_enemy = True; break
        
        if not hit_enemy:
            hit = self.shoot_ray(self.player_x, self.player_y, self.player_angle, self.player_pitch)
            if hit: self.bullet_holes.append(hit)

    def draw(self):
        if self.state == "menu":
            self.screen.blit(self.assets.images['menu_bg'], (0,0))
            bar_h = 80; bar_y = SCREEN_HEIGHT - bar_h
            pygame.draw.rect(self.screen, (0,0,0), (0, bar_y, SCREEN_WIDTH, bar_h))
            logo = self.assets.images['menu_logo']
            self.screen.blit(logo, ((SCREEN_WIDTH-logo.get_width())//2, bar_y - logo.get_height()))
            
            y_pos = bar_y + (bar_h // 2) - 15
            for i, txt in enumerate(self.menu_options):
                color = MENU_TEXT_HOVER if i == self.menu_selected else MENU_TEXT_COLOR
                surf = self.assets.fonts['menu'].render(txt, True, color)
                if i==0: x = SCREEN_WIDTH*0.25 - surf.get_width()//2
                elif i==1: x = SCREEN_WIDTH*0.5 - surf.get_width()//2
                else: x = SCREEN_WIDTH*0.75 - surf.get_width()//2
                self.screen.blit(surf, (x, y_pos))

        elif self.state == "loading":
            self.screen.fill((0,0,0))
            img = self.assets.images['loading'].copy()
            img.set_alpha(int(self.loading_alpha))
            self.screen.blit(img, (0,0))
            
            if self.loading_phase == 0: 
                self.loading_alpha += self.fade_speed
                if self.loading_alpha >= 255: self.loading_alpha = 255; self.loading_phase = 1; self.loading_timer = pygame.time.get_ticks()
            elif self.loading_phase == 1:
                if pygame.time.get_ticks() - self.loading_timer > 2000: self.loading_phase = 2
            elif self.loading_phase == 2:
                self.loading_alpha -= self.fade_speed
                if self.loading_alpha <= 0: 
                    self.reset_game_data()
                    self.state = "game"
                    pygame.mouse.set_visible(False); pygame.event.set_grab(True)

        elif self.state == "game" or self.state == "game_over":
            raycaster.render_kernel(
                self.player_x, self.player_y, self.player_angle, self.player_pitch,
                self.world_map, self.door_state, self.door_lock, self.door_dir,
                self.assets.wall_textures, self.assets.floor_texture, self.assets.ceil_texture,
                self.screen_buffer, self.depth_buffer
            )
            surf = pygame.surfarray.make_surface(self.screen_buffer)
            
            sx = int(random.randint(-int(self.screen_shake), int(self.screen_shake))) if self.screen_shake > 0 else 0
            sy = int(random.randint(-int(self.screen_shake), int(self.screen_shake))) if self.screen_shake > 0 else 0
            self.screen.blit(surf, (sx, sy))

            self.draw_bullet_holes()

            p_cos = math.cos(self.player_angle); p_sin = math.sin(self.player_angle)
            to_draw = []
            for e in self.enemies:
                if e['health'] <= 0: continue
                dx = e['x'] - self.player_x; dy = e['y'] - self.player_y
                depth = dx * p_cos + dy * p_sin
                to_draw.append((depth, e))
            to_draw.sort(key=lambda x: x[0], reverse=True)
            
            for depth, e in to_draw:
                if depth < 10.0: continue
                dx = e['x'] - self.player_x; dy = e['y'] - self.player_y
                lateral = dy * p_cos - dx * p_sin
                scale = SCREEN_HEIGHT / (depth / TILE_SIZE)
                if scale > SCREEN_HEIGHT * 1.5: scale = SCREEN_HEIGHT * 1.5
                
                screen_x = int((SCREEN_WIDTH / 2) + (lateral / depth) * (SCREEN_WIDTH/2/math.tan(HALF_FOV)))
                screen_y = int((HALF_HEIGHT + self.player_pitch) + (0.5 * SCREEN_HEIGHT / (depth/TILE_SIZE))) - int(scale*0.7)
                
                if 0 <= screen_x < SCREEN_WIDTH and (depth/TILE_SIZE) < self.depth_buffer[screen_x] + 0.3:
                    tex = self.assets.enemy_frames[e['frame']]
                    ratio = tex.get_width() / tex.get_height()
                    sw = int(scale * 0.7 * ratio); sh = int(scale * 0.7)
                    if sw > 0 and sh > 0:
                        img = pygame.transform.scale(tex, (sw, sh))
                        self.screen.blit(img, (screen_x - sw//2 + sx, screen_y + sy))
                        if e['hit_timer'] > 0:
                            b = pygame.transform.scale(self.assets.images['blood'], (int(sw*0.6), int(sh*0.6)))
                            self.screen.blit(b, (screen_x - sw//4 + sx, screen_y + sh//4 + sy))

            if self.damage_flash > 0:
                f = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); f.fill((255,0,0))
                f.set_alpha(int(self.damage_flash))
                self.screen.blit(f, (0,0))

            gun = self.assets.images['gun_fire'] if self.muzzle_timer > 0 else self.assets.images['gun_default']
            bx = math.cos(self.weapon_bob) * 10; by = abs(math.sin(self.weapon_bob)) * 10
            reload_off = math.sin((1 - self.reload_timer/60) * math.pi) * 200 if self.is_reloading else 0
            gx = (SCREEN_WIDTH//2) - (gun.get_width()//2) + 180 + bx + sx
            gy = SCREEN_HEIGHT - gun.get_height() + 40 + by + self.weapon_recoil + sy + reload_off
            self.screen.blit(gun, (gx, gy))

            if not self.is_reloading:
                barrel_x = gx + (gun.get_width() // 2)
                barrel_y = gy + int(gun.get_height() * 0.4) 
                active_tracers = []
                for t in self.tracers:
                    start_pos = (barrel_x, barrel_y)
                    t_x = t['x'] + sx; t_y = t['y'] + sy
                    pygame.draw.line(self.screen, (255, 255, 0), start_pos, (t_x, t_y), 2)
                    t['life'] -= 1
                    if t['life'] > 0: active_tracers.append(t)
                self.tracers = active_tracers

            self.screen.blit(self.assets.images['hud_bg'], (0, SCREEN_HEIGHT - HUD_HEIGHT))
            pygame.draw.line(self.screen, DOOM_BEVEL_LIGHT, (0, SCREEN_HEIGHT-HUD_HEIGHT), (SCREEN_WIDTH, SCREEN_HEIGHT-HUD_HEIGHT), 3)
            
            def draw_box(x, label, val, is_pct=False):
                r = pygame.Rect(x, SCREEN_HEIGHT-HUD_HEIGHT+15, 100, HUD_HEIGHT-30)
                pygame.draw.rect(self.screen, DOOM_BEVEL_DARK, r)
                pygame.draw.rect(self.screen, DOOM_BEVEL_LIGHT, r, 2)
                l = self.assets.fonts['label'].render(label, True, DOOM_GOLD)
                self.screen.blit(l, (r.x + (r.w-l.get_width())//2, r.y+4))
                t = f"{int(val)}%" if is_pct else f"{int(val)}"
                v = self.assets.fonts['hud'].render(t, True, DOOM_RED)
                self.screen.blit(v, (r.x + (r.w-v.get_width())//2, r.y+18))

            draw_box(20, "AMMO", self.ammo)
            draw_box(140, "HEALTH", self.health, True)
            
            fr = pygame.Rect(SCREEN_WIDTH//2 - 40, SCREEN_HEIGHT-HUD_HEIGHT+10, 80, 80)
            pygame.draw.rect(self.screen, (0,0,0), fr)
            self.screen.blit(self.assets.faces[self.face_state], (fr.x + (80-64)//2, fr.y + (80-64)//2))
            pygame.draw.rect(self.screen, DOOM_BEVEL_LIGHT, fr, 3)
            
            draw_box(SCREEN_WIDTH-260, "ARMOR", self.armor, True)

            fps_surf = self.assets.fonts['fps'].render(f"FPS: {int(self.clock.get_fps())}", True, (255, 255, 0))
            self.screen.blit(fps_surf, (10, 10))

            if self.ammo == 0:
                reload_txt = self.assets.fonts['interact'].render("PRESS R TO RELOAD", True, (255, 0, 0))
                rect = reload_txt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50))
                self.screen.blit(reload_txt, rect)

            if self.player_facing_door:
                txt = self.assets.fonts['interact'].render("Press E to Open", True, (255, 255, 255))
                rect = txt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 120))
                self.screen.blit(txt, rect)

            cx, cy = SCREEN_WIDTH // 2, HALF_HEIGHT
            g, l = 6, 12; th = 2; c = (200, 200, 200)
            pygame.draw.line(self.screen, c, (cx, cy-g-l), (cx, cy-g), th)
            pygame.draw.line(self.screen, c, (cx, cy+g), (cx, cy+g+l), th)
            pygame.draw.line(self.screen, c, (cx-g-l, cy), (cx-g, cy), th)
            pygame.draw.line(self.screen, c, (cx+g, cy), (cx+g+l, cy), th)

            if self.state == "game_over":
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); ov.fill((0,0,0)); ov.set_alpha(180)
                self.screen.blit(ov, (0,0))
                d = self.assets.fonts['death'].render("YOU DIED", True, (150,0,0))
                self.screen.blit(d, (SCREEN_WIDTH//2 - d.get_width()//2, HALF_HEIGHT - 50))
                r = self.assets.fonts['restart'].render("Press SPACE to Restart", True, (200,200,200))
                self.screen.blit(r, (SCREEN_WIDTH//2 - r.get_width()//2, HALF_HEIGHT + 50))

        pygame.display.flip()

    def run(self):
        while True:
            if not self.check_input():
                break
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
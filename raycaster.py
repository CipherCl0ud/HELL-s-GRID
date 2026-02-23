import math
import numpy as np
from numba import njit
from settings import *
from levels import MAP_SIZE_X, MAP_SIZE_Y  # <--- NEW IMPORT ADDED HERE

@njit(fastmath=True)
def render_kernel(player_x, player_y, player_angle, pitch, world_map, door_state, door_lock, door_dir, wall_textures, floor_texture, ceil_texture, screen_buffer, depth_buffer):
    horizon = int(HALF_HEIGHT + pitch)
    cos_dir = math.cos(player_angle); sin_dir = math.sin(player_angle); plane_scale = 0.66
    ray_dir_x0 = cos_dir - (-sin_dir * plane_scale); ray_dir_y0 = sin_dir - (cos_dir * plane_scale)
    ray_dir_x1 = cos_dir + (-sin_dir * plane_scale); ray_dir_y1 = sin_dir + (cos_dir * plane_scale)

    # --- FLOOR & CEILING CASTING (Darker) ---
    for y in range(0, SCREEN_HEIGHT):
        p_y = y - horizon
        if p_y == 0: continue
        is_floor = p_y > 0
        row_dist = (0.5 * SCREEN_HEIGHT) / abs(p_y) 
        step_x = row_dist * (ray_dir_x1 - ray_dir_x0) / SCREEN_WIDTH
        step_y = row_dist * (ray_dir_y1 - ray_dir_y0) / SCREEN_WIDTH
        floor_x = player_x/TILE_SIZE + row_dist * ray_dir_x0
        floor_y = player_y/TILE_SIZE + row_dist * ray_dir_y0
        
        for x in range(SCREEN_WIDTH):
            tx = int(floor_x * TEXTURE_SIZE) & (TEXTURE_SIZE - 1)
            ty = int(floor_y * TEXTURE_SIZE) & (TEXTURE_SIZE - 1)
            
            # 1. Distance Shading (Much darker, faster falloff)
            shade = 1.0 / (1.0 + row_dist * 0.15)
            # Cap maximum brightness lower for dinginess
            shade = min(0.85, shade) 
            
            # 2. Fake Ambient Occlusion (Deeper corners)
            dist_x = abs(tx - HALF_TEX) / HALF_TEX
            dist_y = abs(ty - HALF_TEX) / HALF_TEX
            edge_factor = max(dist_x, dist_y)
            # Deeper black in corners (min 0.1 instead of 0.4)
            ao_mult = max(0.1, 1.0 - (edge_factor ** 4) * 0.8)
            
            final_shade = shade * ao_mult

            if is_floor:
                fc = floor_texture[tx, ty]
                screen_buffer[x, y, 0] = int(fc[0] * final_shade)
                screen_buffer[x, y, 1] = int(fc[1] * final_shade)
                screen_buffer[x, y, 2] = int(fc[2] * final_shade)
            else:
                cc = ceil_texture[tx, ty]
                screen_buffer[x, y, 0] = int(cc[0] * final_shade)
                screen_buffer[x, y, 1] = int(cc[1] * final_shade)
                screen_buffer[x, y, 2] = int(cc[2] * final_shade)
            
            floor_x += step_x; floor_y += step_y

    # --- WALL CASTING (Darker) ---
    start_angle = player_angle - HALF_FOV
    for ray in range(NUM_RAYS):
        angle = start_angle + ray * DELTA_ANGLE
        sin_a = math.sin(angle); cos_a = math.cos(angle)
        map_x = int(player_x // TILE_SIZE); map_y = int(player_y // TILE_SIZE)
        delta_dist_x = abs(1 / (cos_a + 1e-30)); delta_dist_y = abs(1 / (sin_a + 1e-30))
        step_x = 1 if cos_a >= 0 else -1; step_y = 1 if sin_a >= 0 else -1
        side_dist_x = (map_x + 1.0 - player_x / TILE_SIZE) * delta_dist_x if cos_a >= 0 else (player_x / TILE_SIZE - map_x) * delta_dist_x
        side_dist_y = (map_y + 1.0 - player_y / TILE_SIZE) * delta_dist_y if sin_a >= 0 else (player_y / TILE_SIZE - map_y) * delta_dist_y

        hit = False; side = 0; tex_id = 1; wall_x = 0.0; final_dist = 0.0

        while not hit:
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x; map_x += step_x; side = 0
            else:
                side_dist_y += delta_dist_y; map_y += step_y; side = 1
            
            if map_x < 0 or map_x >= MAP_SIZE_X or map_y < 0 or map_y >= MAP_SIZE_Y:
                hit = True; final_dist = 1000; tex_id = 1
                break

            cell = world_map[map_x, map_y]
            
            if cell > 0:
                if side == 0: 
                    perp_dist = (map_x - player_x / TILE_SIZE + (1 - step_x) / 2) / cos_a
                    hit_x = player_y / TILE_SIZE + perp_dist * sin_a
                else: 
                    perp_dist = (map_y - player_y / TILE_SIZE + (1 - step_y) / 2) / sin_a
                    hit_x = player_x / TILE_SIZE + perp_dist * cos_a
                
                hit_x -= math.floor(hit_x)

                # --- FIXED: DOOR LOGIC NOW INCLUDES CELL 6 ---
                # We use specific OR statements because Numba prefers them over lists/tuples
                if cell == 3 or cell == 4 or cell == 6: 
                    door_amt = door_state[map_x, map_y]
                    if door_amt >= 0.98: continue 
                    if hit_x + door_amt > 1.0: continue 
                    
                    hit = True; final_dist = perp_dist; wall_x = hit_x + door_amt
                    tex_id = cell # Automatically apply the correct texture ID (3, 4, or 6)
                else:
                    hit = True; final_dist = perp_dist; wall_x = hit_x
                    tex_id = cell

        final_dist *= math.cos(angle - player_angle)
        if final_dist < 0.05: final_dist = 0.05
        
        for s in range(SCALE):
            if ray * SCALE + s < SCREEN_WIDTH: depth_buffer[ray * SCALE + s] = final_dist

        line_height = int(SCREEN_HEIGHT / final_dist)
        draw_start = -line_height // 2 + horizon; draw_end = line_height // 2 + horizon
        draw_start_clamped = max(0, draw_start); draw_end_clamped = min(SCREEN_HEIGHT, draw_end)
        
        tex_x = int(wall_x * TEXTURE_SIZE)
        if side == 0 and cos_a > 0: tex_x = TEXTURE_SIZE - tex_x - 1
        if side == 1 and sin_a < 0: tex_x = TEXTURE_SIZE - tex_x - 1
        tex_x = max(0, min(tex_x, TEXTURE_SIZE - 1))
        
        step = 1.0 * TEXTURE_SIZE / line_height
        tex_pos = (draw_start_clamped - horizon + line_height / 2) * step
        
        # --- ATMOSPHERE RESTORED & DARKENED ---
        # 1. Distance Shading (Heavy fog)
        shade = 1.0 / (1.0 + final_dist * 0.15)
        
        # 2. Side Dimming (More drastic for contrast)
        if side == 1: shade *= 0.6 
        
        # 3. Fake Ambient Occlusion (Deeper vertical edges)
        dist_x_pixel = abs(tex_x - HALF_TEX) / HALF_TEX
        # Darker corners (min 0.2) and steeper curve (**6)
        ao_mult = max(0.2, 1.0 - (dist_x_pixel ** 6) * 0.8)
        
        final_shade = shade * ao_mult

        for y in range(draw_start_clamped, draw_end_clamped):
            tex_y = int(tex_pos) & (TEXTURE_SIZE - 1)
            tex_pos += step
            color = wall_textures[tex_id, tex_x, tex_y]
            
            r = int(color[0] * final_shade)
            g = int(color[1] * final_shade)
            b = int(color[2] * final_shade)
            
            for s in range(SCALE):
                if ray * SCALE + s < SCREEN_WIDTH:
                    screen_buffer[ray * SCALE + s, y, 0] = r
                    screen_buffer[ray * SCALE + s, y, 1] = g
                    screen_buffer[ray * SCALE + s, y, 2] = b
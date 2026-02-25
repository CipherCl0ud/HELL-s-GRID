# 💀 Hell's Grid: Alpha Edition

> *A retro-style raycasting FPS engine built from scratch in Python.*

**Hell's Grid** is a modular 2.5D First-Person Shooter engine inspired by classics like *Wolfenstein 3D* and *Doom*. Built using **Python** and **Pygame**, it utilizes **Numba** for high-performance just-in-time (JIT) compilation, allowing for smooth framerates even with complex texture mapping and shading calculations.
![Hell's Grid Gameplay](background.png)

## 🕹️ Features

### **Rendering Engine**
* **Custom Raycasting Kernel:** A high-speed rendering engine accelerated by Numba (`@njit`).
* **Atmospheric Lighting:** Distance-based "Blood Fog" shading and fake Ambient Occlusion (AO) on wall corners for a dark, oppressive atmosphere.
* **Texture Mapping:** Full support for textured walls, floors, and ceilings.
* **Camera Effects:** Dynamic weapon bobbing and screen shake on impact/firing.

### **Gameplay & UI**
* **Campaign Progression:** Multi-level support. Navigate to the Northernmost sector to beat the map and progress to the next stage.
* **Persistent Save Profiles:** JSON-based profile system (`profiles.json`). The engine automatically saves your Health, Ammo, Armor, and Level progress between stages.
* **Combat System:** Hitscan weapon mechanics with recoil, muzzle flash animations, and bullet tracers.
* **Enemy AI:** Sprite-based enemies with basic pathfinding and chase logic.
* **Interactive World:** Robust sliding door system with "locked" and "unlocked" states, plus 2D sprite billboarding for Health, Armor, and Ammo pickups.
* **Navigation & Objectives:** Dynamic 8-point compass HUD. Reach the Northernmost sector of the grid to secure a "Mission Accomplished" victory.
* **Dynamic HUD:** Real-time health, ammo, and armor tracking with a reactive status face.
* **Customizable Settings:** Fully integrated Options menu featuring adjustable mouse sensitivity, crosshair color cycling, and a live FPS toggle.

## 🛠️ Installation & Usage

### **Prerequisites**
You need Python installed, along with the following libraries:

```bash
pip install pygame numba numpy

Running the Game
Navigate to the project directory and run the main entry point:

Bash
python main.py


🎮 Controls
W, A, S, D: Move Player

Mouse: Look / Aim

Left Click: Fire Weapon

R: Reload

E: Interact (Open Doors / Switches)

ESC / P: Pause / Options Menu

📂 Project Structure
main.py - The game loop, input handling, state manager, and UI rendering.

raycaster.py - The math engine containing the Numba-accelerated rendering kernel.

assets.py - Asset manager for loading textures, sprites, and fonts.

levels.py - Map data, enemy spawn points, and level configurations.

settings.py - Global constants, physics settings, and UI colors.

🚀 Roadmap
[x] Pickups (Health, ammo, armor)

[x] Victory Condition (Navigate North)

[x] Options Menu (Phase 1: UI & Sensitivity)

[x] Level Transition & Save Profile System

[ ] Engine Refactor (Phase 2: Dynamic FOV & Resolution Scaling)

[ ] Sound Effects (Gunshots, sliding doors, ambiance)

Created as a Python engine development project.
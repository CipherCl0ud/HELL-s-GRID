# 💀 Hell's Grid: Alpha Edition

> *A retro-style raycasting FPS engine built from scratch in Python.*

**Hell's Grid** is a modular 2.5D First-Person Shooter engine inspired by classics like *Wolfenstein 3D* and *Doom*. Built using **Python** and **Pygame**, it utilizes **Numba** for high-performance just-in-time (JIT) compilation, allowing for smooth framerates even with complex texture mapping and shading calculations.

## 🕹️ Features

### **Rendering Engine**

* **Custom Raycasting Kernel:** A high-speed rendering engine accelerated by Numba (`@njit`).
* **Atmospheric Lighting:** Distance-based "Blood Fog" shading and fake Ambient Occlusion (AO) on wall corners for a dark, oppressive atmosphere.
* **Texture Mapping:** Full support for textured walls, floors, and ceilings.
* **Camera Effects:** Dynamic weapon bobbing and screen shake on impact/firing.

### **Gameplay**

* **Combat System:** Hitscan weapon mechanics with recoil, muzzle flash animations, and bullet tracers.
* **Enemy AI:** Sprite-based enemies with basic pathfinding and chase logic.
* **Interactive World:** robust sliding door system (Wolfenstein-style) with "locked" and "unlocked" states.
* **Dynamic HUD:** Real-time health, ammo, and armor tracking with a reactive status face.

## 🛠️ Installation & Usage

### **Prerequisites**

You need Python installed, along with the following libraries:

```bash
pip install pygame numba numpy

```

### **Running the Game**

Navigate to the project directory and run the main entry point:

```bash
python main.py

```

## 🎮 Controls

* **W, A, S, D**: Move Player
* **Mouse**: Look / Aim
* **Left Click**: Fire Weapon
* **R**: Reload
* **E**: Interact (Open Doors)
* **ESC**: Pause / Menu

## 📂 Project Structure

* `main.py` - The game loop, input handling, and state manager.
* `raycaster.py` - The math engine containing the Numba-accelerated rendering kernel.
* `assets.py` - Asset manager for loading textures, sprites, and fonts.
* `levels.py` - Map data, enemy spawn points, and level configurations.
* `settings.py` - Global constants, physics settings, and UI colors.

## 🚀 Roadmap

* [ ] Sound Effects (Gunshots, footsteps, ambiance)
* [ ] Pickups (Health packs, ammo crates)
* [ ] Victory Condition (Exit switch)
* [ ] Options Menu

---

*Created as a Python engine development project.*

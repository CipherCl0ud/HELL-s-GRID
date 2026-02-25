## [Unreleased / Alpha Update] - 2026-02-23

### Added
- **Unified Custom Fonts:** Integrated `FunkyWhimsyRegular` across the entire UI (Main Menu, Pause Menu, and HUD elements) for a consistent retro-arcade aesthetic.
- **Dynamic Door States:** Sliding doors now dynamically swap textures when interacted with. The control panel starts with a red light, turns green when activated, and reverts to red when the door seals shut.
- **Glowing Pickup Orbs:** Replaced flat pickup dots with stylized glowing orbs featuring white cores (Red = Health, Green = Ammo, Blue = Armor).

### Changed
- **Weapon Rendering Order:** Adjusted the rendering pipeline so the player's weapon is drawn in front of the HUD, allowing it to seamlessly tuck behind the UI bar during the reload animation.
- **Pickup Hitboxes:** Increased the collision radius for item pickups to 75 pixels to make collecting items feel much smoother and more forgiving.
- **Door Timing:** Added a 1-second mechanical delay to all sliding doors after interaction before the opening animation begins.

### Fixed
- **Pickup Logic Bug:** Fixed an issue where the player's stats (Health, Ammo, Armor) were not updating correctly upon collection due to a tuple unpacking error.
- **Raycaster Door Animation:** Updated the core raycasting kernel to properly calculate sliding axes and render animations for dynamically swapped map tiles (specifically Tile ID 6).
- **Interaction Prompt Visibility:** Fixed the "Press E to Open" prompt so it correctly renders in the center of the screen above the HUD, rather than being hidden behind it.

### Removed
- **Bullet Hole Raycasting:** Temporarily removed the wall-hit detection and bullet hole decal rendering to clean up the engine's core loop and improve performance.
## [Added] - 2026-02-24
### Navigation & Objectives
- **Compass HUD:** Integrated a dynamic 8-point compass in the top-left corner to show the player's current facing direction.
- **Victory Condition:** Reaching the Northernmost sector of the map (`Y < 1.5 * TILE_SIZE`) now triggers a "MISSION ACCOMPLISHED" victory screen.

### UI & Menus
- **Options Menu:** Added a unified settings menu accessible from both the Main Menu and the in-game Pause screen.
- **Settings Added:**
  - Adjustable Mouse Sensitivity slider.
  - Crosshair Color cycler (Default, Red, Green, Cyan, White, Yellow).
  - Show/Hide FPS toggle.
- **Controls Menu:** Added a dedicated sub-menu detailing all in-game keybindings.

### Under the Hood
- Refactored the state machine in `main.py` to seamlessly track and return to the `previous_state` when exiting menus.
- Replaced hardcoded `MOUSE_SENSITIVITY` with a dynamic variable tied to the Options menu.
## [Added] - 2026-02-25
### Core Systems & Progression
- **Persistent Profile System:** Integrated a JSON-based save system (`profiles.json`). Player stats (Health, Ammo, Armor) and Level progression are now automatically saved upon completing a map.
- **Level Transitioning:** Built a multi-level array system in `levels.py`. The engine now seamlessly unloads the current map and generates the next level in the sequence when the player reaches the Northern exit zone.

### UI & Menus
- **Profile Manager:** Overhauled the Main Menu flow. "START GAME" now directs to a Profile Manager allowing players to CONTINUE, create a NEW PROFILE, or DELETE an existing profile.
- **Custom Text Input:** Built a custom Pygame text-entry loop allowing players to type alphanumeric names for their save files with a blinking retro cursor.
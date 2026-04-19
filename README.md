# MultiPurpose AutoClicker

A feature-rich auto clicker with a dark-themed GUI, preset system, and record-to-bind controls for both mouse buttons and keyboard keys.

---

## Quickstart

### Just want to use it? (No Python required)

1. Go to the [Releases](../../releases) page
2. Download `AutoClicker.exe`
3. Double-click it — done

> Works on any Windows PC. No installation, no Python, no setup.

---

### Want to run from source?

**Step 1 — Install Python**
Download from [python.org](https://www.python.org/downloads/) and check **"Add Python to PATH"** during setup.

**Step 2 — Install the one dependency**
```
pip install pynput
```

**Step 3 — Run the app**
```
python autoclicker.py
```
Or double-click `run.bat` — it installs `pynput` automatically and launches the app.

---

### Want to build the exe yourself?

```
build.bat
```
This installs PyInstaller, compiles everything, and puts `AutoClicker.exe` in the `dist\` folder.

---

## Features

| Feature | Details |
|---|---|
| **Presets** | Create, save, edit, duplicate, and delete named presets. Each preset has its own independent settings and hotkey. |
| **Mouse clicks** | Auto-click Left, Right, or Middle mouse button — recorded by physically pressing the button. |
| **Keyboard key presses** | Instead of clicking the mouse, press any keyboard key automatically (Space, E, F1, Enter, etc.) — recorded by pressing the key. |
| **Per-preset hotkeys** | Each preset has its own trigger key (e.g. F5 for "Super Fast", F6 for "1 per second"). Press it to start, press again to stop. Works globally even when the app is minimized. |
| **Adjustable interval** | Set click speed using hours / minutes / seconds / milliseconds spinners. |
| **Single or double click/press** | Choose whether each action fires once or twice per interval. |
| **Repeat modes** | Repeat forever, or stop after a set number of clicks/presses. |
| **Fixed cursor position** | Lock clicks to a specific X/Y coordinate, or use a full-screen overlay to pick the spot by clicking it. |
| **Persistent presets** | All presets are saved to `presets.json` automatically — they survive app restarts. |

---

## Getting started

### Option A — Standalone executable (no Python needed)

1. Install [Python](https://www.python.org/downloads/) — check **"Add Python to PATH"** during setup.
2. Run `build.bat` — it installs PyInstaller and compiles everything into a single file.
3. Find `dist\AutoClicker.exe` and double-click it. No Python, no pip, nothing else needed.

> Share or copy that `.exe` to any Windows PC and it will just work.

### Option B — Run from source

Requires Python 3.10 or newer installed with pip available.

1. Install the one dependency:

```
pip install pynput
```

2. Run the app:

```
python autoclicker.py
```

Or double-click `run.bat` — it installs `pynput` automatically and launches the app.

---

## Dependencies

| Package | What it does | Bundled in exe? |
|---|---|---|
| `pynput` | Global mouse/keyboard control and listening | Yes |
| `tkinter` | GUI framework | Yes (ships with Python) |

There are no other dependencies. Everything else used (`threading`, `json`, `uuid`, etc.) is part of the Python standard library.

---

## How to use

### Creating a preset

1. Click **+ New Preset** and enter a name (e.g. "Super Fast").
2. Click **Edit** on the row that appears.
3. Configure the settings in the editor below (see sections below).
4. Click **Save Preset**.

### Click Interval

Set how often the action fires using the four spinners:

```
[ Hours ] [ Minutes ] [ Seconds ] [ Milliseconds ]
```

For example: 0h 0m 0s 50ms = 20 clicks per second.

### Click Options — Mouse Button

1. Select **Mouse Button** as the click action.
2. Click **Record Click** — the button turns orange.
3. Physically press the mouse button you want (Left, Right, or Middle).
4. The button is recorded and displayed automatically.

### Click Options — Keyboard Key

1. Select **Keyboard Key** as the click action.
2. Click **Record Key** — the button turns orange.
3. Press any key on your keyboard (Space, E, F1, Enter, arrow keys, etc.).
4. Press **ESC** to cancel recording without changing the key.

### Click Type

- **Single** — fires the action once per interval.
- **Double** — fires the action twice per interval (double-click / double-press).

### Click Repeat

- **Repeat forever** — keeps going until you stop it.
- **Repeat N times** — automatically stops after the set number of actions.

### Cursor Position (mouse mode only)

- **Current cursor location** — clicks wherever your mouse is at that moment.
- **Fixed position** — always clicks at a specific X/Y coordinate.
  - Enter coordinates manually, or click **Pick Location on Screen** to use a full-screen crosshair picker.

### Preset Hotkey

Each preset can have its own hotkey that starts and stops it from anywhere on your screen:

1. Click **Record Key** in the PRESET HOTKEY section.
2. Press the key you want to use (e.g. F5).
3. Press **ESC** to cancel, or **Clear** to remove the hotkey.
4. Save the preset.

After saving, pressing that key anywhere (even when the app is minimized) toggles the preset on and off.

### Running presets

- Click **Start** on a preset row to start it manually.
- Click **Stop** (same button) to stop it.
- Use the preset's hotkey to toggle it from anywhere.
- Multiple presets can run at the same time with different hotkeys.

### Duplicating a preset

Open a preset for editing and click **Duplicate** to create a copy with a blank hotkey. Useful for making variants (e.g. "Super Fast" → "Super Fast (right click)").

---

## Files

| File | Purpose |
|---|---|
| `autoclicker.py` | Main application |
| `presets.json` | Saved presets (created automatically) |
| `requirements.txt` | Python dependencies |
| `run.bat` | Windows launcher — installs deps and starts the app |
# MultiPurpose_AutoClicker

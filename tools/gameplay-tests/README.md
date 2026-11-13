# Gameplay regression scene

Runs the actual desktop client, graphics renderer, local backend and game server
with an isolated `GameplayLab` profile under `build/gameplay-lab`. It does not send
input to the user's desktop or alter the installed game's saves.

Prepare the current client/server distributions in `bin`, build with
`gradlew desktop:dist server:dist --offline`, then:

```powershell
New-Item -ItemType Directory -Force build/gameplay-lab
javac -encoding UTF-8 -cp bin/client/brainout-desktop.jar -d build/gameplay-lab tools/gameplay-tests/GameplaySmoke.java
python tools/gameplay-tests/run.py
```

The runner currently expects the local JDK at `../tools/jdk-17.0.21+9`.
Success requires `GAMEPLAY_SMOKE_PASS` in `build/gameplay-lab/client.log`.
Checks all 122 attachments on all STG/MP40 skins, paired reload/chambering rules,
the +30% buckshot damage and disabled slide entry, and GPU per-pixel wall clipping.
It exports both complete mounted-attachment contact sheets, a hub frame and a
controlled visibility scene. Rendering on two actual remote PCs is not covered.

## Art and packaging

`tools/weapon-art/vanguard_modules.py` contains the native-resolution pixel
drawings; `vanguard-sprites/` holds their individual PNG exports.
`launcher/vanguard_attachments.py` adds them after the existing G11/conversions
passes, fits each attachment to the native skeleton, splits paired animation
tracks and refreshes the package CRC manifest.

For this installation the pass was applied to pristine installed v0.14.1
packages, preserving every original content definition except `sl-pri-stg` and
`sl-pri-mp40`. The originals and saves were backed up outside the repository.
Names/families reference Vanguard; artwork is original, not extracted from COD.
Optics use this game's accuracy/aim-distance system; they do not implement a new
thermal/night-vision renderer.

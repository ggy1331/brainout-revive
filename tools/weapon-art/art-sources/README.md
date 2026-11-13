# Weapon-specific artwork, revision 5

STG now loads **stg-parts-v5.png**, a new 39-piece source atlas generated with
the built-in image generator. References were mp40-parts-v3.png (the user's
preferred detail quality) and the revision-4 in-engine STG showcase (palette and
receiver proportions). The full request is recorded in stg-parts-v5.prompt.txt.
Explicit crop bounds are in stg-parts-v5.json. Stocks/barrels/muzzles are mirrored
to face right; each part is fitted once with nearest-neighbour sampling to the
weapon-specific STG_SIZES and mapped to each STG skin palette. The drum has a
curved side flange and separate feed neck. No external game artwork was imported.

MP40 retains its own atlas. Revision 5 adjusts every stock/barrel/muzzle/front
grip size and the visible optic saddle. Mount placement uses the actual alpha
edge of the attachment rather than its canvas centre, including asymmetrical
bipod, flashlight and bayonet clamps. Scope centres are STG x=40 / MP40 x=26 in
native sprite coordinates, seated on the receiver. STG magazine necks now overlap
the well. Front/muzzle/rear/stock seams overlap by one native pixel. The new
check_attachment_connections.py checks 625 contacts and barrel combinations
across all five skins from the final packed atlas.

## Revision 4 sources (retained for reference)

The two weapons now use independent asset sets:

- STG physical parts: editable native-grid drawings and native-game adaptations
  in `../stg_workshop.py`. The front assembly uses the STG's actual pixel shading;
  stocks adapt AKM, AK74 and FG42 parts, magazines adapt STG/RPK74 parts, and the
  slim drum is drawn in side elevation. Muzzles use native AK/M3GG components;
  BAR bipod and OTs grip details are fitted to STG-specific dimensions. The ten
  rear grips preserve the native STG's sloped outline and vary the material.
- STG optics: twenty distinct native-game optical bodies listed explicitly in
  `STG_NATIVE_OPTICS`, plus two drawn rear sights. Donor brackets are removed and
  replaced with low STG mounting feet. This list has no shared donors with MP40.
  The old generated optics atlas below is retained as historical source only.
- MP40 physical parts: original generated `mp40-parts-v3.png`; explicit component
  bounds are in its JSON file because the generator did not preserve every grid
  column. The exact prompt is saved alongside. Stocks, barrels and muzzle devices
  are flipped to the game's right-facing orientation during conversion.
- MP40 optics: distinct native-game optical bodies listed in `MP_OPTICS` in
  `../vanguard_modules.py`, adapted with short MP40 clamps. Native source artwork
  remains in the repository under its existing license. These are not COD assets.

Other image-generation requests were rejected; there is no generated STG parts
atlas at that stage. Those editable drawings remain in stg_workshop.py as
historical sources; only its two iron sights are used in revision 5.
All output colours are quantized separately against the corresponding weapon
and skin. Do not restore the old shared STG/MP40 palette or shared module drawing.
The exported default sets contain 61 different assets each; alternate-skin atlas
regions are generated at packaging time. Scope feet are alpha-trimmed, visibly
connected, and overlap the receiver by one native pixel. Underbarrel mounting
height follows the selected handguard through `vg-underbarrel`.

## Original optics atlas provenance

`vanguard-optics.png` is an original atlas created with the built-in image
generator, using a contact sheet of this repository's native STG, MP40, magazine
and scope sprites as a style reference. No Call of Duty artwork was used.
The generator rejected other requested part families; those remain editable
pixel drawings in `vanguard_modules.py` and were revised there.

Prompt: a transparent 4-column, 6-row atlas, 22 distinct sights in strict side
profile, ocular left and objective right. Reflectors must be edge-on slanted
plates, never front-facing circles. Match native BRAIN/OUT muted dark steel,
small shading clusters, slim mounts, no bright outlines, text or cast shadows.
Ordered designs: tall reflector; short vintage telescope; low slanted reflector;
roof reflex; prism; hinged telescope; thin scout telescope; tubular monocular;
variable bell scope; narrow reflector; tapered vintage scope; long straight
telescope; scope with upper reflex; offset Japanese scope; angular prism;
early night optic; bracketed reflector; tandem optic; offset vintage telescope;
wedge reflex; rear notch; adjustable rear aperture, all seen from the side.

`vanguard_modules.py` crops cells, fits them once to explicit native pixel
dimensions and quantizes colours against the game's own STG/MP40 sprites.
Final exports are in `../vanguard-sprites`. The game loads the packaged atlas,
not this high-resolution source image.

# Weapon-specific artwork, revision 3

The two weapons now use independent asset sets:

- STG physical parts: new native-grid drawings in `../stg_workshop.py`.
- STG optics: the original `vanguard-optics.png` atlas below, now extracted by
  connected regions rather than noisy cell-wide bounds. Tall donor brackets are
  replaced with short visible feet fitted to the STG receiver.
- MP40 physical parts: original generated `mp40-parts-v3.png`; explicit component
  bounds are in its JSON file because the generator did not preserve every grid
  column. The exact prompt is saved alongside. Stocks, barrels and muzzle devices
  are flipped to the game's right-facing orientation during conversion.
- MP40 optics: distinct native-game optical bodies listed in `MP_OPTICS` in
  `../vanguard_modules.py`, adapted with short MP40 clamps. Native source artwork
  remains in the repository under its existing license. These are not COD assets.

Other image-generation requests were rejected; there is no generated STG parts
atlas. The original editable STG drawings are the production source for that set.
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

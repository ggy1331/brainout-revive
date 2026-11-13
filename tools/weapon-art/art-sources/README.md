# Optics source, revision 2

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

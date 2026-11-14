"""Turn freshly built packages (scripts/make_data.py) into the release packages.

    python launcher/build_packages.py            # both client and server
    python launcher/build_packages.py client

For each side, in place in bin/<side>/packages:
  base.zip     -> equipment_package -> gameplay_package -> loadout_rules -> welrod_graft apply
               -> player_skins (skins added to the source actor.json) -> finalize_sidearms -> colt1911 (slide, magazine, staged reload)
               -> sidearms (the same for the other grip-magazine pistols)
               -> g11 (HK G11: own stances, magazine-from-the-top reload, cocking handle)
               -> conversions (weapon families: AK-74 -> AKS-74U, AK-12, AK-15, RPK-74, RPK-16)
  freeplay.zip -> welrod_graft freeplay
The untouched make_data output is kept as build/base-<side>-premod.zip and
build/freeplay-<side>-premod.zip, so the script can be run again safely.
"""
from pathlib import Path
import os
import shutil
import sys

LAUNCHER = Path(__file__).resolve().parent
ROOT = LAUNCHER.parent
sys.path.insert(0, str(LAUNCHER))
os.chdir(LAUNCHER)  # the scripts open helper files relative to this folder

import equipment_package
import gameplay_package
import loadout_rules
import welrod_graft
import colt1911
import sidearms
import g11
import conversions
import vanguard_attachments
import movement_refinement
import player_skins
from finalize_sidearms import finalize


def side(name, fresh):
    pk = ROOT / "bin" / name / "packages"
    tmp = ROOT / "build" / ("packages-" + name)
    tmp.mkdir(parents=True, exist_ok=True)
    keep = ROOT / "build" / ("base-%s-premod.zip" % name)
    keep_fp = ROOT / "build" / ("freeplay-%s-premod.zip" % name)
    if fresh:
        shutil.copyfile(pk / "base.zip", keep)
        shutil.copyfile(pk / "freeplay.zip", keep_fp)
    equipment_package.build(keep, tmp / "1-equipment.zip")
    gameplay_package.build(str(tmp / "1-equipment.zip"), str(tmp / "2-gameplay.zip"))
    loadout_rules.build(str(tmp / "2-gameplay.zip"), str(tmp / "3-loadout.zip"))
    welrod_graft.apply(tmp / "3-loadout.zip", tmp / "4-welrod.zip")
    player_skins.build(tmp / "4-welrod.zip", tmp / "4-skins.zip")
    finalize(tmp / "4-skins.zip", tmp / "5-final.zip")
    colt1911.build(tmp / "5-final.zip", tmp / "6-colt.zip")
    sidearms.build(tmp / "6-colt.zip", tmp / "7-sidearms.zip")
    g11.build(tmp / "7-sidearms.zip", tmp / "8-g11.zip")
    conversions.build(tmp / "8-g11.zip", tmp / "9-conversions.zip")
    vanguard_attachments.build(tmp / "9-conversions.zip", tmp / "10-vanguard.zip")
    movement_refinement.build(tmp / "10-vanguard.zip", pk / "base.zip")
    welrod_graft.freeplay(keep_fp, pk / "freeplay.zip")
    print(name, "packages ready")


if __name__ == "__main__":
    args = sys.argv[1:]
    # --again: reuse build/*-premod.zip instead of the current bin packages
    fresh = "--again" not in args
    names = [a for a in args if not a.startswith("--")] or ["client", "server"]
    for n in names:
        side(n, fresh)

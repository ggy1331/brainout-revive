"""Turn freshly built packages (scripts/make_data.py) into the release packages.

    python launcher/build_packages.py            # both client and server
    python launcher/build_packages.py client

For each side, in place in bin/<side>/packages:
  base.zip     -> equipment_package -> gameplay_package -> loadout_rules -> welrod_graft apply
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
    welrod_graft.apply(tmp / "3-loadout.zip", pk / "base.zip")
    welrod_graft.freeplay(keep_fp, pk / "freeplay.zip")
    print(name, "packages ready")


if __name__ == "__main__":
    args = sys.argv[1:]
    # --again: reuse build/*-premod.zip instead of the current bin packages
    fresh = "--again" not in args
    names = [a for a in args if not a.startswith("--")] or ["client", "server"]
    for n in names:
        side(n, fresh)

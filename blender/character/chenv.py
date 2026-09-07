"""Environment bootstrap for the NYCSim character lane (stage: character).

Puts ``blender/common`` (foundation ``nycsim_bpy``) and ``pipeline`` on ``sys.path``, enables the MPFB2 Blender
extension (``bl_ext.user_default.mpfb``) and exposes the lane's output directories.

Notes on running Blender here
----------------------------
Blender is the ``bpy`` **Python module** (4.5.13 LTS), not the ``blender`` executable.  Two consequences that every
script in this lane relies on:

* the MPFB2 extension installed under ``~/.config/blender/4.5/extensions/user_default/mpfb`` is *not* enabled
  automatically; :func:`enable_mpfb` does that (``addon_utils.enable``);
* the ``bpy`` module hangs on interpreter shutdown (a known bpy-as-module issue, reproduced by the repo's
  ``hang_repro.py``), so every entry point must finish with :func:`hard_exit`.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
CHAR_DIR = HERE.parent                      # blender/character
BLENDER_DIR = CHAR_DIR.parent               # blender
REPO_ROOT = Path(os.environ.get("NYCSIM_REPO_ROOT", BLENDER_DIR.parent))
for _p in (BLENDER_DIR / "common", REPO_ROOT / "pipeline", CHAR_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

MPFB_PACKAGE = "bl_ext.user_default.mpfb"
MPFB_ROOT = Path.home() / ".config" / "blender" / "4.5" / "extensions" / "user_default" / "mpfb"
MPFB_USER_DATA = Path.home() / ".config" / "blender" / "4.5" / "extensions" / ".user" / "user_default" / "mpfb" / "data"

OUT_DIR = REPO_ROOT / "blender_out" / "character"
CATALOG_DIR = OUT_DIR / "catalog"
ANIM_DIR = OUT_DIR / "anim"
VERIFY_DIR = REPO_ROOT / "docs" / "verification" / "character"
MOCAP_DIR = REPO_ROOT / "assets" / "character" / "cmu_mocap"
MH_DATA = REPO_ROOT / "data" / "raw" / "character_assets" / "mh_data"

log = logging.getLogger("nycsim.character")

_MPFB_ENABLED = False


def setup_logging(level: int = logging.INFO) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger().setLevel(level)


def enable_mpfb() -> object:
    """Enable the MPFB2 extension and return its module. Idempotent.

    Raises RuntimeError with a precise diagnosis if the extension is missing or fails to register, so that a
    fallback path (plain MakeHuman base mesh + Rigify) can be chosen by the caller with a real reason logged.
    """
    global _MPFB_ENABLED
    import addon_utils  # noqa: PLC0415 - only exists inside Blender

    if _MPFB_ENABLED:
        return sys.modules[MPFB_PACKAGE]
    if not (MPFB_ROOT / "blender_manifest.toml").exists():
        raise RuntimeError(f"MPFB2 extension not installed at {MPFB_ROOT}")
    module = addon_utils.enable(MPFB_PACKAGE, default_set=True, persistent=True)
    if module is None:
        raise RuntimeError(f"addon_utils.enable({MPFB_PACKAGE!r}) returned None - extension failed to register")
    missing = [p for p in ("clothes", "eyes", "teeth", "tongue", "hair", "skins", "eyebrows", "eyelashes")
               if not (MPFB_USER_DATA / p).exists()]
    if missing:
        raise RuntimeError(f"MakeHuman asset directories missing from MPFB user data {MPFB_USER_DATA}: {missing}")
    _MPFB_ENABLED = True
    log.info("MPFB2 enabled (%s), user data %s", getattr(module, "__file__", "?"), MPFB_USER_DATA)
    return module


def ensure_dirs() -> None:
    for d in (OUT_DIR, CATALOG_DIR, ANIM_DIR, VERIFY_DIR):
        d.mkdir(parents=True, exist_ok=True)


def hard_exit(code: int = 0) -> None:
    """Flush and terminate. ``bpy`` as a module deadlocks in its atexit handlers; ``os._exit`` is the only exit."""
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)

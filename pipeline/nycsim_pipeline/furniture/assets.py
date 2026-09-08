"""Which exported asset a ``props.parquet`` row is.

``props.parquet`` stores ``kind`` as the int16 code of :mod:`nycsim_pipeline.furniture.catalog`, and
that code is not the name of any file.  Turning a row into a mesh needs three lookups and two
vocabularies that do not quite agree:

1. ``data/processed/furniture/props_catalog.json`` maps the int16 code to a kind **name**;
2. ``blender_out/props/props_asset_catalog.json`` groups the exported assets by ``dataset_kind``,
   which spells several kinds differently (``utility_pole`` is exported as ``sign_post``) and does
   not have an asset at all for a dozen more (``billboard``, ``curb_ramp``, ...);
3. a tree is not chosen by kind at all but by its species and its measured height.

``blender/verify/scene.py`` worked this out once, for the renders.  Nothing else did, and
``build_levels.py`` -- the one consumer that puts props into the game -- took ``kind`` for a mesh
name and looked for ``/Game/NYCSim/Props/14/SM_14``.  Every prop in the world failed to resolve, and
the 44,427 street trees of the first-drive region failed twice over, because ``str(0 or "")`` is the
empty string and kind 0 is the tree.

This module is that logic, in one place, with no ``bpy`` in it, so the renderer, the manifest and
the editor's Python all answer the question the same way.  The manifest resolves each row here and
writes the answer into ``props.json``; the editor never has to know that ``sign_post`` is what a
utility pole is called.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Prop ``kind`` name -> ``dataset_kind`` of the exported asset catalogue.  The two vocabularies
#: agree for most kinds; the entries here are the ones that do not spell the same, and ``None``
#: marks a kind that has no exported prop asset -- either because another stage models it (the road
#: stage builds curb ramps into the pavement) or because it is not modelled at all.
PROP_KIND_ALIASES: dict[str, str | None] = {
    "waste_basket": "waste_basket",
    "street_lamp": "street_lamp",
    "bus_stop_sign": "road_sign",
    "rtpi_sign": "road_sign",
    "utility_pole": "sign_post",
    # An OSM advertising=billboard node is a roadside bulletin on posts. The kit has
    # billboard_rooftop and billboard_wall_mounted, and both are wrong at street level, so these 15
    # rows stay unplaced rather than become the wrong object (docs/DEVIATIONS.md J22).
    "billboard": None,
    # Modelled by the road stage, and this time that is true: ``blender/roads/build_pavement.py``
    # cuts each surveyed ramp into the kerb from its own published width and running slope
    # (pavement kind 8, docs/DEVIATIONS.md J21). It was not true when this table first said it --
    # the pavement had no ramp kind at all and the comment had never been checked against it.
    "curb_ramp": None,
    "artwork": None,
    "memorial": None,
    "drinking_fountain": None,
    "payphone": None,
    "vending_machine": None,
    "bike_shelter": "bus_shelter",
    "parks_comfort_station": None,
    "parks_recreation_center": None,
    "parks_building": None,
    "cooling_tower": None,
    "swimming_pool": None,
    "misc_structure": None,
    "subway_emergency_exit": "subway_vent_grate",
    "steam_vent": "steam_vent",
}

#: Street-tree species key used in the exported asset ids, keyed by the lower-cased Latin genus
#: or species found in ``props.parquet``.
TREE_SPECIES_KEYS: dict[str, str] = {
    "styphnolobium japonicum": "sophora",
    "sophora japonica": "sophora",
    "zelkova serrata": "zelkova",
    "gleditsia triacanthos": "honeylocust",
    "gleditsia triacanthos var. inermis": "honeylocust",
    "platanus x acerifolia": "planetree",
    "platanus acerifolia": "planetree",
    "pyrus calleryana": "callery_pear",
    "quercus palustris": "pin_oak",
    "acer platanoides": "norway_maple",
    "acer rubrum": "red_maple",
    "tilia cordata": "littleleaf_linden",
    "ginkgo biloba": "ginkgo",
}

#: Fallback when the census species has no modelled asset: the commonest NYC street tree.
TREE_FALLBACK_KEY = "honeylocust"

#: Prop kinds whose modelled asset lives in the **facade kit** rather than the props catalogue.
#:
#: The planimetric rooftop cooling towers are a surveyed dataset -- real footprints on real roofs --
#: and ``hvac_cooling_tower`` is a real modelled piece. It was placed nowhere: the procedural rooftop
#: set in ``facade/placements.py`` draws from bulkheads, AC units, exhaust fans, vent pipes and
#: satellite dishes, and never picks the cooling tower. So these rows add surveyed objects and
#: duplicate nothing.
KIND_TO_KIT_PIECE: dict[str, str] = {
    "cooling_tower": "hvac_cooling_tower",
}

#: The two height thresholds that pick a tree's size class, in metres.  They are the bin edges the
#: props kit exported its three sizes against.
TREE_SIZE_EDGES = (7.0, 12.0)

#: Height used when a tree row carries none -- the median of the 2015 census after allometry.
TREE_DEFAULT_HEIGHT_M = 8.0


def tree_asset_id(species: str, height_m: float, leaf_off: bool = False) -> tuple[str, bool]:
    """``(asset id, species was modelled)`` for a street tree.

    A species with no modelled asset falls back to the honeylocust rather than dropping the tree:
    a wrong species is a deviation, an absent tree is a hole in the street.
    """
    key = TREE_SPECIES_KEYS.get((species or "").strip().lower())
    exact = key is not None
    key = key or TREE_FALLBACK_KEY
    if height_m >= TREE_SIZE_EDGES[1]:
        size = "large"
    elif height_m >= TREE_SIZE_EDGES[0]:
        size = "medium"
    else:
        size = "small"
    return f"tree_{key}_{size}{'_bare' if leaf_off else ''}", exact


def clean_height(value: Any) -> float:
    """A row's ``height_m`` as a usable number, NaN and null included."""
    try:
        h = float(value)
    except (TypeError, ValueError):
        return TREE_DEFAULT_HEIGHT_M
    if math.isnan(h) or h <= 0.0:
        return TREE_DEFAULT_HEIGHT_M
    return h


@dataclass(frozen=True)
class PropAssets:
    """The exported prop assets, indexed the two ways a lookup needs them."""

    by_id: dict[str, dict]
    by_kind: dict[str, list[dict]]
    kind_names: dict[int, str]
    #: ``catalog_id`` -> kit piece, for the kinds whose asset is a facade kit piece.
    kit_by_id: dict[str, dict]

    def name_of(self, kind_id: int) -> str:
        return self.kind_names.get(int(kind_id), str(int(kind_id)))

    def resolve(self, kind_id: int, *, variant: Any = 0, species: str = "",
                height_m: Any = None, leaf_off: bool = False) -> tuple[dict | None, str]:
        """``(catalogue entry, reason)``; the entry is ``None`` when the row has no asset.

        ``reason`` is ``"ok"``, ``"species_substituted"`` or the kind name that could not be mapped,
        so a caller can count what it dropped instead of dropping it silently.
        """
        name = self.name_of(kind_id)
        if name == "tree":
            asset_id, exact = tree_asset_id(str(species or ""), clean_height(height_m), leaf_off)
            entry = self.by_id.get(asset_id)
            if entry is None:
                return None, name
            return entry, "ok" if exact else "species_substituted"
        piece = KIND_TO_KIT_PIECE.get(name)
        if piece is not None:
            entry = self.kit_by_id.get(piece)
            return (entry, "ok") if entry is not None else (None, name)
        alias = PROP_KIND_ALIASES.get(name, name)
        if alias is None:
            return None, name
        choices = self.by_kind.get(alias) or []
        if not choices:
            return None, name
        try:
            v = int(variant)
        except (TypeError, ValueError):
            v = 0
        return choices[v % len(choices)], "ok"


def load(processed: Path, blender_out: Path) -> PropAssets:
    """Read the two catalogues.  Missing files give an empty index rather than an exception."""
    by_id: dict[str, dict] = {}
    by_kind: dict[str, list[dict]] = {}
    cat_path = Path(blender_out) / "props" / "props_asset_catalog.json"
    if cat_path.is_file():
        doc = json.loads(cat_path.read_text())
        for e in doc.get("entries", []):
            by_id[e["id"]] = e
            by_kind.setdefault(str(e.get("dataset_kind") or ""), []).append(e)
    for entries in by_kind.values():
        entries.sort(key=lambda e: e["id"])
    kind_names: dict[int, str] = {}
    kinds_path = Path(processed) / "furniture" / "props_catalog.json"
    if kinds_path.is_file():
        doc = json.loads(kinds_path.read_text())
        kind_names = {int(k["id"]): str(k["name"]) for k in doc.get("kinds", [])}
    kit_by_id: dict[str, dict] = {}
    kit_path = Path(processed) / "facade" / "kit_ids.json"
    if kit_path.is_file():
        for piece in json.loads(kit_path.read_text()).get("pieces", []):
            cid = piece.get("catalog_id")
            if cid:
                kit_by_id[str(cid)] = {"id": cid, "glb": piece.get("glb"),
                                       "category": piece.get("category"), "source": "kit"}
    return PropAssets(by_id=by_id, by_kind=by_kind, kind_names=kind_names, kit_by_id=kit_by_id)

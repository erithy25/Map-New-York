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
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Prop ``kind`` name -> ``dataset_kind`` of the exported asset catalogue.  The two vocabularies
#: agree for most kinds; the entries here are the ones that do not spell the same, and ``None``
#: marks a kind that has no exported prop asset -- either because another stage models it (the road
#: stage builds curb ramps into the pavement) or because it is not modelled at all.
PROP_KIND_ALIASES: dict[str, str | None] = {
    "waste_basket": "waste_basket",
    "street_lamp": "street_lamp",
    # Its own asset since J58.  Aliased to ``road_sign`` before that, which resolves over the seven
    # regulatory signs and takes the alphabetically first: every one of the 13,341 GTFS bus stops
    # was a bare 12 x 18 in parking regulation plate, 0.23 m tall, with no post under it.
    "bus_stop_sign": "bus_stop_sign",
    # A real-time passenger information sign is a screen on a pole and there is no asset for one, so
    # the 491 rows stay unplaced rather than become a parking plate, which is what ``road_sign``
    # made them.  Same rule as ``billboard`` below (docs/DEVIATIONS.md J22, J58).
    "rtpi_sign": None,
    # An 11 m wooden distribution pole carrying power and telecom, drawn as a 2.44 m galvanised
    # u-channel sign post: not the wrong variant, the wrong object, and 4.5x the wrong size. The
    # kit has no utility pole, so the 924 rows stay unplaced until it does (J58).
    "utility_pole": None,
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
#: Kinds that have no prop asset **on purpose**, because another stage builds them as part of
#: something else. Counting these as "no asset" made two reports say the wrong thing at once: the
#: renderer listed 81 curb ramps as unmapped on a Bronx sheet whose pavement had every one of them
#: cut into it, and the manifest's ``prop_kinds_without_an_asset`` carried them as a gap. A row that
#: is deliberately built by a different stage is not a missing asset, and the two have to be
#: countable apart or the gap number stops meaning anything.
BUILT_ELSEWHERE: dict[str, str] = {
    "curb_ramp": "cut into the pavement mesh by blender/roads/build_pavement.py (J21)",
}
BUILT_ELSEWHERE_REASON = "built_elsewhere"


def is_built_elsewhere(reason: str) -> bool:
    """Does this ``resolve`` reason mean "another stage builds it" rather than "no asset"?"""
    return str(reason).split(":", 1)[0] == BUILT_ELSEWHERE_REASON

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


#: ``dataset_kind`` -> the variant code a row falls back to when its own code names no asset.
#:
#: This is a **rule, not a measurement**.  For ``street_lamp`` it is 1, the NYC DOT standard
#: octagonal pole with a cobra head on a davit arm, because that is the fixture the city puts on
#: an ordinary street and 14,690 of the 16,971 OSM lamp nodes say nothing at all about what they
#: carry (docs/DEVIATIONS.md J56).  It used to be whatever sorted first, which for lamps was the
#: ornamental Bishop's Crook -- a fixture NYC has a few thousand of, on named historic blocks.
DEFAULT_VARIANT: dict[str, int] = {"street_lamp": 1}


#: Tag an exported asset carries to declare which ``variant`` code it *is*, e.g. ``variant:2``.
VARIANT_TAG = re.compile(r"variant:(\d+)")


def declared_variants(entries: list[dict]) -> dict[int, str]:
    """``{variant code: asset id}`` from the ``variant:N`` tags a kind's assets carry.

    Empty where a kind declares nothing, which is every kind but ``street_lamp`` today.
    """
    out: dict[int, str] = {}
    for e in entries:
        for tag in e.get("tags") or []:
            m = VARIANT_TAG.fullmatch(str(tag))
            if m:
                out[int(m.group(1))] = str(e["id"])
    return out


@dataclass(frozen=True)
class PropAssets:
    """The exported prop assets, indexed the two ways a lookup needs them."""

    by_id: dict[str, dict]
    by_kind: dict[str, list[dict]]
    kind_names: dict[int, str]
    #: ``catalog_id`` -> kit piece, for the kinds whose asset is a facade kit piece.
    kit_by_id: dict[str, dict]
    #: ``dataset_kind`` -> ``{variant code: asset id}``, read from the assets' own ``variant:N``
    #: tags.  Empty for a kind that declares none, which is every kind but ``street_lamp`` today.
    variants_by_kind: dict[str, dict[int, str]] = field(default_factory=dict)

    def name_of(self, kind_id: int) -> str:
        return self.kind_names.get(int(kind_id), str(int(kind_id)))

    def resolve(self, kind_id: int, *, variant: Any = 0, species: str = "",
                height_m: Any = None, leaf_off: bool = False) -> tuple[dict | None, str]:
        """``(catalogue entry, reason)``; the entry is ``None`` when the row has no asset.

        ``reason`` is ``"ok"``, ``"species_substituted"``, ``"built_elsewhere"`` or the kind name
        that could not be mapped, so a caller can count what it dropped instead of dropping it
        silently -- and can tell a gap from a division of labour.
        """
        name = self.name_of(kind_id)
        if name in BUILT_ELSEWHERE:
            return None, f"{BUILT_ELSEWHERE_REASON}:{name}"
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
        declared = self.variants_by_kind.get(alias) or {}
        if declared:
            asset_id = declared.get(v)
            if asset_id is not None:
                entry = self.by_id.get(asset_id)
                if entry is not None:
                    return entry, "ok"
            # The code is outside the declared set -- 0 "unknown" for a kind whose assets all name
            # a real fixture, or a code no asset claims.  Fall back to the kind's own default and
            # say so, rather than let a modulo pick whichever id happens to sort into that slot.
            fallback = DEFAULT_VARIANT.get(alias)
            entry = self.by_id.get(declared.get(fallback, "")) if fallback is not None else None
            if entry is not None:
                return entry, f"variant_default:{v}"
            return choices[0], f"variant_unmapped:{v}"
        # No kind but street_lamp declares a map today; position in the id-sorted list is all
        # there is to go on, and it is only ever right by coincidence -- so it is not a modulo any
        # more either: a code past the end is reported, not wrapped.
        if 0 <= v < len(choices):
            return choices[v], "ok"
        return choices[0], f"variant_out_of_range:{v}"


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
    variants_by_kind = {k: declared_variants(v) for k, v in by_kind.items()}
    variants_by_kind = {k: v for k, v in variants_by_kind.items() if v}
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
    return PropAssets(by_id=by_id, by_kind=by_kind, kind_names=kind_names, kit_by_id=kit_by_id,
                      variants_by_kind=variants_by_kind)

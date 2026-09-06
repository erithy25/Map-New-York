"""Material library for vehicles.

Every engine-bound slot is a material whose *name is the slot name* (``LIGHT_HEAD_L``, ``GAUGE_SPEED``, ``MIRROR_GLASS``,
``PLATE_FACE`` ...), so the glb material list doubles as the binding table.

Shared textures: ``blender/common/textures.py`` (``get_texture_set``) is used when present for tyre rubber, leather,
fabric and brushed metal. Fallback Principled values (used when the module or a set is missing) are documented next
to each material below.
"""
from __future__ import annotations

import os
from pathlib import Path

import bpy

from . import env

nb = env.nb
log = env.log

RGBA = tuple[float, float, float, float]


def srgb_hex(hex_str: str, alpha: float = 1.0) -> RGBA:
    """'#F7B500' -> linear RGBA (Blender materials are linear)."""
    h = hex_str.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return (lin(r), lin(g), lin(b), alpha)


def _bsdf(mat: bpy.types.Material) -> bpy.types.ShaderNode:
    return mat.node_tree.nodes["Principled BSDF"]


def basic(name: str, rgb: RGBA | tuple[float, float, float], *, roughness: float = 0.5, metallic: float = 0.0, coat: float = 0.0,
          coat_roughness: float = 0.05, emission: RGBA | None = None, emission_strength: float = 0.0, alpha: float = 1.0,
          anisotropic: float = 0.0, specular_ior_level: float | None = None) -> bpy.types.Material:
    """Principled material; cached by name (identical name => same material, so slot names stay unique)."""
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing
    col = tuple(rgb) if len(rgb) == 4 else (*rgb, 1.0)
    mat = nb.pbr_material(name, base_color=col, roughness=roughness, metallic=metallic, emission=emission,
                          emission_strength=emission_strength, alpha=alpha)
    b = _bsdf(mat)
    if coat > 0:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = coat_roughness
    if anisotropic > 0:
        b.inputs["Anisotropic"].default_value = anisotropic
    if specular_ior_level is not None:
        b.inputs["Specular IOR Level"].default_value = specular_ior_level
    if alpha < 1.0:
        mat.blend_method = 'BLEND'
        mat.use_backface_culling = False
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = 'BLENDED'
    return mat


def paint(name: str, rgb: RGBA | tuple[float, float, float], *, metallic: float = 0.35, roughness: float = 0.30,
          coat: float = 1.0) -> bpy.types.Material:
    """Automotive paint: base colour under a clear coat (glTF: KHR_materials_clearcoat). Metallic paints use a
    moderate metallic weight for the flake reflectivity; solid colours (taxi yellow) pass metallic=0.05."""
    return basic(name, rgb, roughness=roughness, metallic=metallic, coat=coat, coat_roughness=0.04)


def textured(name: str, image_path: str | Path, *, roughness: float = 0.5, metallic: float = 0.0, coat: float = 0.0,
             emissive: bool = False, emission_strength: float = 1.0, alpha_from_image: bool = False,
             extra_maps: dict[str, str] | None = None) -> bpy.types.Material:
    """Image-textured material with identity UV mapping (UV 0..1 == whole image). ``emissive`` links the same image to
    Emission for screens, gauges and signs. ``extra_maps`` adds roughness/normal/metallic images."""
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing
    image_path = str(image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    textures = {"color": image_path}
    if extra_maps:
        textures.update({k: str(v) for k, v in extra_maps.items() if v})
    mat = nb.pbr_material(name, roughness=roughness, metallic=metallic, textures=textures, uv_scale_m=1.0)
    nt = mat.node_tree
    b = _bsdf(mat)
    if coat > 0:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.04
    tex_nodes = [n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.filepath == image_path]
    if tex_nodes:
        tex = tex_nodes[0]
        if emissive:
            nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = emission_strength
        if alpha_from_image:
            nt.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
            mat.blend_method = 'BLEND'
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = 'BLENDED'
    return mat


def shared_or_basic(name: str, shared_names: tuple[str, ...], fallback: dict, *, uv_scale_m: float = 0.5) -> bpy.types.Material:
    """Try the shared texture library under any of ``shared_names``; otherwise ``basic(name, **fallback)``."""
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing
    for sn in shared_names:
        ts = env.shared_texture_set(sn)
        if ts:
            try:
                mat = nb.pbr_material(name, base_color=(*fallback["rgb"][:3], 1.0), roughness=fallback.get("roughness", 0.5),
                                      metallic=fallback.get("metallic", 0.0), textures=ts, uv_scale_m=uv_scale_m)
                mat["nycsim_texture_set"] = sn
                return mat
            except FileNotFoundError as exc:
                log.warning("shared texture set %s unusable (%s); falling back", sn, exc)
    return basic(name, **fallback)


# --------------------------------------------------------------------------- the library
class Library:
    """Lazily-created, name-cached materials for one vehicle build (materials persist in bpy.data for the session)."""

    # ---- exterior
    def paint(self, rgb: RGBA | tuple[float, float, float], name: str = "BODY_PAINT", *, metallic: float = 0.35,
              roughness: float = 0.30) -> bpy.types.Material:
        return paint(name, rgb, metallic=metallic, roughness=roughness)

    def black_plastic(self) -> bpy.types.Material:  # bumper lowers, wheel liners, mirror caps
        return basic("TRIM_BLACK_PLASTIC", (0.012, 0.012, 0.013), roughness=0.62)

    def gloss_black(self) -> bpy.types.Material:  # B-pillars, grille surround
        return basic("TRIM_GLOSS_BLACK", (0.01, 0.01, 0.011), roughness=0.12, coat=1.0)

    def chrome(self) -> bpy.types.Material:
        return basic("CHROME", (0.92, 0.92, 0.92), roughness=0.08, metallic=1.0)

    def satin_alu(self) -> bpy.types.Material:  # window trim, roof rails
        return basic("SATIN_ALUMINIUM", (0.72, 0.72, 0.72), roughness=0.38, metallic=1.0)

    def brushed_metal(self) -> bpy.types.Material:
        # fallback: albedo 0.62 grey, metallic 1, roughness 0.35, anisotropic 0.6 (brushed along U)
        return shared_or_basic("BRUSHED_METAL", ("brushed_metal", "metal_brushed", "brushed_steel", "steel_brushed"),
                               dict(rgb=(0.62, 0.62, 0.62), roughness=0.35, metallic=1.0, anisotropic=0.6), uv_scale_m=0.3)

    def steel_painted(self, rgb=(0.35, 0.36, 0.37), name: str = "STEEL_PAINTED") -> bpy.types.Material:
        return basic(name, rgb, roughness=0.45, metallic=0.2)

    def glass(self, name: str = "GLASS", tint=(0.55, 0.65, 0.66), alpha: float = 0.30) -> bpy.types.Material:
        return basic(name, (*tint, alpha), roughness=0.03, metallic=0.0, alpha=alpha, coat=0.0, specular_ior_level=0.6)

    def glass_tinted(self) -> bpy.types.Material:  # privacy glass (rear of SUVs/vans)
        return basic("GLASS_TINTED", (0.05, 0.06, 0.07, 0.75), roughness=0.03, alpha=0.75, specular_ior_level=0.6)

    def lamp_lens_clear(self) -> bpy.types.Material:
        return basic("LAMP_LENS_CLEAR", (0.75, 0.78, 0.8, 0.28), roughness=0.05, alpha=0.28, specular_ior_level=0.7)

    def lamp_lens_red(self) -> bpy.types.Material:
        return basic("LAMP_LENS_RED", (0.55, 0.02, 0.02, 0.55), roughness=0.08, alpha=0.55)

    def lamp_housing(self) -> bpy.types.Material:
        return basic("LAMP_HOUSING", (0.02, 0.02, 0.022), roughness=0.25, metallic=0.6)

    def reflector(self) -> bpy.types.Material:
        return basic("LAMP_REFLECTOR", (0.85, 0.85, 0.85), roughness=0.15, metallic=1.0)

    def underside(self) -> bpy.types.Material:
        return basic("UNDERBODY", (0.02, 0.02, 0.02), roughness=0.9)

    def rubber(self) -> bpy.types.Material:  # seals, mud flaps
        return basic("RUBBER_SEAL", (0.008, 0.008, 0.008), roughness=0.85)

    def tyre(self, sidewall_texture: str | Path | None = None) -> bpy.types.Material:
        """Tyre rubber. Fallback albedo 0.02 (near-black), roughness 0.80. With a generated sidewall image the
        lettering rides in the colour map (UV: u around, v across the profile)."""
        name = "TYRE_RUBBER"
        existing = bpy.data.materials.get(name)
        if existing is not None:
            return existing
        if sidewall_texture and os.path.exists(str(sidewall_texture)):
            return textured(name, sidewall_texture, roughness=0.8)
        return shared_or_basic(name, ("tyre_rubber", "rubber", "rubber_black"), dict(rgb=(0.02, 0.02, 0.02), roughness=0.8), uv_scale_m=0.25)

    def alloy(self, name: str = "WHEEL_ALLOY") -> bpy.types.Material:
        return basic(name, (0.68, 0.69, 0.70), roughness=0.28, metallic=1.0, coat=0.6)

    def alloy_dark(self) -> bpy.types.Material:
        return basic("WHEEL_ALLOY_DARK", (0.18, 0.19, 0.20), roughness=0.35, metallic=1.0)

    def steel_wheel(self) -> bpy.types.Material:
        return basic("WHEEL_STEEL", (0.08, 0.08, 0.085), roughness=0.5, metallic=0.4)

    def brake_disc(self) -> bpy.types.Material:
        return basic("BRAKE_DISC", (0.52, 0.52, 0.52), roughness=0.42, metallic=1.0, anisotropic=0.5)

    def caliper(self, rgb=(0.14, 0.14, 0.15), name: str = "BRAKE_CALIPER") -> bpy.types.Material:
        return basic(name, rgb, roughness=0.5, metallic=0.3)

    def mirror_glass(self) -> bpy.types.Material:
        """``MIRROR_GLASS`` slot: UE replaces with a scene-capture material; here a perfect mirror."""
        return basic("MIRROR_GLASS", (0.96, 0.96, 0.96), roughness=0.0, metallic=1.0)

    # ---- light slots (emission default strength is the 'off' look; the engine drives intensity)
    def light(self, slot: str, rgb: tuple[float, float, float], *, strength: float = 0.0, alpha: float = 1.0) -> bpy.types.Material:
        return basic(slot, (*rgb, alpha), roughness=0.15, metallic=0.0, emission=(*rgb, 1.0), emission_strength=strength, alpha=alpha)

    def light_white(self, slot: str, strength: float = 0.0) -> bpy.types.Material:
        return self.light(slot, (0.95, 0.96, 1.0), strength=strength)

    def light_red(self, slot: str, strength: float = 0.0) -> bpy.types.Material:
        return self.light(slot, (1.0, 0.03, 0.02), strength=strength)

    def light_amber(self, slot: str, strength: float = 0.0) -> bpy.types.Material:
        return self.light(slot, (1.0, 0.45, 0.02), strength=strength)

    def light_blue(self, slot: str, strength: float = 0.0) -> bpy.types.Material:
        return self.light(slot, (0.05, 0.2, 1.0), strength=strength)

    # ---- interior
    def leather(self, rgb=(0.045, 0.040, 0.037), name: str = "LEATHER_BLACK", texture: str | Path | None = None) -> bpy.types.Material:
        """Seat leather. Fallback albedo ~0.04 warm black, roughness 0.48. A generated seam texture (colour) is used
        when given; the shared library set 'leather' is tried first when no texture is given."""
        existing = bpy.data.materials.get(name)
        if existing is not None:
            return existing
        if texture and os.path.exists(str(texture)):
            return textured(name, texture, roughness=0.48)
        return shared_or_basic(name, ("leather", "leather_black"), dict(rgb=rgb, roughness=0.48), uv_scale_m=0.5)

    def fabric(self, rgb=(0.32, 0.31, 0.30), name: str = "FABRIC_HEADLINER") -> bpy.types.Material:
        # fallback: light grey headliner cloth, roughness 0.95
        return shared_or_basic(name, ("fabric", "fabric_grey", "cloth"), dict(rgb=rgb, roughness=0.95), uv_scale_m=0.3)

    def carpet(self) -> bpy.types.Material:
        return shared_or_basic("CARPET", ("carpet", "carpet_black", "fabric_dark"), dict(rgb=(0.02, 0.02, 0.02), roughness=1.0), uv_scale_m=0.3)

    def dash_soft(self) -> bpy.types.Material:
        return basic("DASH_SOFT_TOUCH", (0.018, 0.018, 0.019), roughness=0.72)

    def dash_trim(self) -> bpy.types.Material:  # satin trim strips
        return basic("DASH_TRIM_SATIN", (0.42, 0.42, 0.43), roughness=0.4, metallic=0.8)

    def piano_black(self) -> bpy.types.Material:
        return basic("INTERIOR_PIANO_BLACK", (0.006, 0.006, 0.007), roughness=0.05, coat=1.0)

    def seatbelt(self) -> bpy.types.Material:
        return basic("SEATBELT_WEBBING", (0.02, 0.02, 0.022), roughness=0.9)

    def pedal_rubber(self) -> bpy.types.Material:
        return basic("PEDAL_RUBBER", (0.01, 0.01, 0.01), roughness=0.9)

    def screen(self, slot: str, image: str | Path, strength: float = 1.2) -> bpy.types.Material:
        return textured(slot, image, roughness=0.15, emissive=True, emission_strength=strength)

    def plate(self, image: str | Path) -> bpy.types.Material:
        return textured("PLATE_FACE", image, roughness=0.35, coat=0.4)

    def decal(self, name: str, image: str | Path, *, emissive: bool = False, strength: float = 1.0) -> bpy.types.Material:
        return textured(name, image, roughness=0.4, emissive=emissive, emission_strength=strength, alpha_from_image=True)

    def livery(self, name: str, image: str | Path, *, metallic: float = 0.05, roughness: float = 0.30) -> bpy.types.Material:
        return textured(name, image, roughness=roughness, metallic=metallic, coat=1.0)

    # ---- misc fleet
    def canvas(self, rgb=(0.05, 0.05, 0.06), name: str = "CANVAS") -> bpy.types.Material:
        return basic(name, rgb, roughness=0.9)

    def wood(self, rgb=(0.20, 0.12, 0.06), name: str = "WOOD_VARNISHED") -> bpy.types.Material:
        return basic(name, rgb, roughness=0.35, coat=0.8)

    def horse_coat(self, rgb=(0.16, 0.09, 0.05)) -> bpy.types.Material:
        return basic("HORSE_COAT_BAY", rgb, roughness=0.75)

    def diamond_plate(self) -> bpy.types.Material:
        return basic("DIAMOND_PLATE_ALU", (0.6, 0.6, 0.6), roughness=0.4, metallic=1.0)

    def led_matrix(self, slot: str, image: str | Path) -> bpy.types.Material:
        return textured(slot, image, roughness=0.3, emissive=True, emission_strength=2.5)

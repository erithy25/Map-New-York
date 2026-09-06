"""Material palette shared by the prop builders (one function per finish; cached per scene by name)."""
from __future__ import annotations

import _core as C


def galv():        return C.mat_textured("galvanized_steel", "metal_galvanized", 0.5, roughness=0.45, metallic=0.85)
def galv_dark():   return C.mat_textured("galvanized_steel_dark", "metal_galvanized", 0.5, tint="#8A8D90", roughness=0.5, metallic=0.85)
def aluminium():   return C.mat_textured("aluminium", "metal_galvanized", 0.5, tint="#C9CCCF", roughness=0.35, metallic=0.9)
def black_steel(): return C.mat_textured("black_powder_steel", "metal_black_powder", 0.5, roughness=0.5, metallic=0.4)
def brushed():     return C.mat_textured("brushed_stainless", "metal_brushed", 0.5, roughness=0.3, metallic=0.95)
def cast_iron():   return C.mat_textured("cast_iron", "metal_cast_iron_rust", 0.8, roughness=0.75, metallic=0.6)
def steel_plate(): return C.mat_textured("steel_plate", "metal_scratched_steel", 1.2, roughness=0.55, metallic=0.8)
def green_paint(): return C.mat_textured("green_painted_steel", "paint_green_rust", 0.6, tint="#7FA98C", roughness=0.55)
def concrete():    return C.mat_textured("concrete", "concrete_smooth", 1.0, roughness=0.85)
def concrete_rough(): return C.mat_textured("concrete_rough", "concrete_rough", 1.0, roughness=0.9)
def wood():        return C.mat_textured("wood_slats", "wood_planks", 1.0, tint="#B08A5A", roughness=0.6)
def asphalt():     return C.mat_textured("asphalt", "asphalt", 2.0, roughness=0.9)
def sidewalk():    return C.mat_textured("sidewalk_concrete", "concrete_sidewalk", 1.5, roughness=0.85)

# solid finishes
def signal_green(): return C.mat_solid("nyc_signal_green", C.NYC_SIGNAL_GREEN, 0.45)
def parks_green():  return C.mat_solid("nyc_parks_green", C.NYC_PARKS_GREEN, 0.5)
def mta_green():    return C.mat_solid("mta_railing_green", C.MTA_RAILING_GREEN, 0.5)
def black():        return C.mat_solid("black_paint", "#151515", 0.5)
def black_matte():  return C.mat_solid("black_matte", "#101010", 0.9)
def dark_grey():    return C.mat_solid("dark_grey", "#3A3C3F", 0.5, 0.3)
def white_paint():  return C.mat_solid("white_paint", "#E8E8E4", 0.4)
def silver_paint(): return C.mat_solid("silver_paint", "#B9BCBE", 0.35, 0.6)
def fdny_red():     return C.mat_solid("fdny_red", C.FDNY_RED, 0.4)
def usps_blue():    return C.mat_solid("usps_blue", C.USPS_BLUE, 0.4)
def dot_orange():   return C.mat_solid("dot_orange", C.DOT_ORANGE, 0.5)
def safety_orange():return C.mat_solid("safety_orange_pvc", "#FF5A1F", 0.6)
def brass():        return C.mat_solid("brass", "#B08D57", 0.35, 1.0)
def rubber():       return C.mat_solid("rubber_black", "#0C0C0C", 0.95)
def plastic_black():return C.mat_solid("plastic_black", "#111111", 0.35)
def bag_black():    return C.mat_solid("trash_bag_black", "#0A0A0C", 0.25)
def glass():        return C.mat_glass()
def glass_dark():   return C.mat_glass("glass_dark", "#4A5A66", 0.55)
def soil():         return C.mat_solid("soil", "#3B2A1A", 0.95)
def mulch():        return C.mat_solid("mulch", "#4A3222", 0.95)
def retro_white():  return C.mat_solid("retro_white", MUTCD_WHITE, 0.3)
def citibike_blue():return C.mat_solid("citibike_blue", "#1B4FA0", 0.4)

MUTCD_WHITE = C.MUTCD["white"]

# emissive (names are part of the runtime contract)
def lamp():          return C.mat_emissive("LAMP_EMISSIVE", "#FFF1D6", 12.0, base="#F4F0E6")
def lamp_warm():     return C.mat_emissive("LAMP_EMISSIVE", "#FFD9A0", 10.0, base="#F1E7D0")
def screen():        return C.mat_emissive("SCREEN_EMISSIVE", "#BFD8FF", 4.0, base="#20242A")
def led(name: str, hexcolor: str, strength: float = 6.0): return C.mat_emissive(f"LED_{name}", hexcolor, strength, base=hexcolor)
def globe_green():   return C.mat_emissive("LAMP_GLOBE_GREEN", "#25B04A", 6.0, base="#1E7A38")
def globe_red():     return C.mat_emissive("LAMP_GLOBE_RED", "#E23A2E", 6.0, base="#A02820")

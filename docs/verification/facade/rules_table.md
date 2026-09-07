# Facade classifier rule table (`facade-rules/1`)

101 ordered rules over real per-building attributes (ADR-004). The **first matching rule wins**; the last rule matches unconditionally so the table is exhaustive.

Columns: `#` order, `rule` stable rule name, `class` the `facade_class` written to `buildings.parquet`, `predicate` the condition, `hits` buildings claimed by the rule in the recorded run, `share` hits / total buildings.

| # | rule | class | facade_class id | predicate | hits | share |
|--:|---|--:|---|---|--:|--:|
| 0 | `accessory_garage` | 38 | `parking_garage_concrete` | feature_code == 5110 | 213,451 | 19.709 % |
| 1 | `transit_structure` | 55 | `subway_elevated_station_steel_1915` | bldg_class in U2,U6,U7,T2,T9 or feature_code in 1000..1006 | 2,124 | 0.196 % |
| 2 | `gas_station` | 48 | `gas_station_canopy` | bldg_class in G3,G4,G5 | 724 | 0.067 % |
| 3 | `parking_garage` | 38 | `parking_garage_concrete` | bldg_class in G0,G1,G6,G7,G9 | 2,453 | 0.226 % |
| 4 | `auto_shop` | 22 | `warehouse_concrete_1950` | bldg_class in G2,G8 | 2,600 | 0.240 % |
| 5 | `firehouse` | 44 | `firehouse_brick_1900` | bldg_class == Y1 | 350 | 0.032 % |
| 6 | `cast_iron_lpc_material` | 20 | `cast_iron_soho_1870` | lpc_material contains 'cast iron' and floors >= 4 | 308 | 0.028 % |
| 7 | `soho_cast_iron_district` | 20 | `cast_iron_soho_1870` | hist_district contains 'SoHo-Cast Iron' and floors >= 4 and year <= 1900 | 225 | 0.021 % |
| 8 | `tribeca_store_loft` | 56 | `cast_iron_tribeca_store_1860` | hist_district contains 'Tribeca' and floors 3..7 and year <= 1900 | 262 | 0.024 % |
| 9 | `ladies_mile_terracotta` | 23 | `terracotta_office_1905` | hist_district contains 'Ladies' Mile' and floors >= 6 | 224 | 0.021 % |
| 10 | `lpc_brownstone_rowhouse` | 3 | `brownstone_rowhouse_1880_4fl_stoop` | lpc_material contains 'brownstone'/'sandstone' and floors 3..5 and class in rowhouse set | 5,783 | 0.534 % |
| 11 | `lpc_brownstone_low` | 4 | `brownstone_rowhouse_1860_3fl_stoop` | lpc_material contains 'brownstone'/'sandstone' and floors <= 3 | 1,381 | 0.128 % |
| 12 | `lpc_wood_frame_house` | 31 | `brooklyn_frame_rowhouse_1900_siding` | lpc_material contains 'wood frame'/'clapboard'/'shingle' and floors <= 3 | 2,318 | 0.214 % |
| 13 | `lpc_tudor_revival` | 29 | `queens_tudor_1930` | lpc_style contains 'Tudor' | 386 | 0.036 % |
| 14 | `lpc_greek_revival` | 7 | `greek_revival_rowhouse_1840_3fl` | lpc_style contains 'Greek Revival' and floors <= 4 and year <= 1860 | 1,288 | 0.119 % |
| 15 | `lpc_federal` | 6 | `federal_rowhouse_1830_3fl_dormer` | lpc_style contains 'Federal' and floors <= 3 | 275 | 0.025 % |
| 16 | `lpc_beaux_arts_apt` | 9 | `prewar_apt_1910_beaux_arts_12fl` | lpc_style contains 'Beaux-Arts'/'neo-Renaissance' and floors >= 8 and class in apartment set | 415 | 0.038 % |
| 17 | `lpc_art_deco` | 10 | `bronx_art_deco_apt_1935` | lpc_style contains 'Art Deco' and floors 4..12 | 100 | 0.009 % |
| 18 | `lpc_gothic_church` | 35 | `church_stone_gothic_1880` | lpc_style contains 'Gothic' and class in M1,M9 | 127 | 0.012 % |
| 19 | `lpc_queen_anne_frame` | 31 | `brooklyn_frame_rowhouse_1900_siding` | lpc_style contains 'Queen Anne' and floors <= 3 and borough in BK,QN,SI | 374 | 0.035 % |
| 20 | `church_gothic_stone` | 35 | `church_stone_gothic_1880` | class in M1,M9 and year <= 1920 and footprint_area >= 250 | 615 | 0.057 % |
| 21 | `church_brick` | 36 | `church_brick_romanesque_1890` | class in M1,M2,M3,M4,M9 | 5,460 | 0.504 % |
| 22 | `school_prewar` | 39 | `school_brick_1920` | class in W1,W2,W3,W4,W5,W7,W8,W9 and year <= 1945 | 1,909 | 0.176 % |
| 23 | `school_postwar` | 40 | `school_brick_1960` | class in W1..W9 except W6 | 1,905 | 0.176 % |
| 24 | `university_modern` | 54 | `brown_brick_office_1985_midrise` | class == W6 | 482 | 0.045 % |
| 25 | `hospital_modern` | 41 | `hospital_glass_2000` | class in I1..I9 and (year >= 1985 or floors >= 8) | 539 | 0.050 % |
| 26 | `hospital_prewar` | 39 | `school_brick_1920` | class in I1..I9 and year <= 1945 | 568 | 0.052 % |
| 27 | `hospital_postwar` | 54 | `brown_brick_office_1985_midrise` | class in I1..I9 | 527 | 0.049 % |
| 28 | `civic_prewar` | 39 | `school_brick_1920` | class in N,P,J,Y,Z (except Y1) and year <= 1945 | 2,477 | 0.229 % |
| 29 | `civic_postwar` | 40 | `school_brick_1960` | class in N,P,J,Y,Z (except Y1) | 2,245 | 0.207 % |
| 30 | `self_storage` | 46 | `self_storage_metal_panel_2000` | class == E7 or (class in E* and year >= 1990) | 1,531 | 0.141 % |
| 31 | `daylight_factory` | 45 | `daylight_factory_concrete_1920` | class in F*,L1,L2,L3 and year 1900..1935 and floors >= 4 | 137 | 0.013 % |
| 32 | `industrial_loft_brick` | 21 | `industrial_loft_brick_1910` | class in L*,F*,RW and year <= 1930 and floors >= 4 | 4 | 0.000 % |
| 33 | `warehouse_low` | 22 | `warehouse_concrete_1950` | class in E*,F*,L*,RW and floors <= 3 | 9,132 | 0.843 % |
| 34 | `loft_converted` | 21 | `industrial_loft_brick_1910` | class in L*,F*,E*,RW | 181 | 0.017 % |
| 35 | `big_box_retail` | 47 | `big_box_retail_precast_1990` | class in K3,K5,K6,K8 or (class in K* and footprint_area >= 1800 and floors <= 2 and year >= 1975) | 1,169 | 0.108 % |
| 36 | `limestone_bank` | 24 | `limestone_bank_1915` | class in K4,O7,O9,K1 and year 1900..1940 and floors <= 6 and footprint_area >= 200 | 4,924 | 0.455 % |
| 37 | `taxpayer_corner` | 37 | `bodega_corner_taxpayer_1_2fl` | class in K1,K2,K9,S1,S9,RS and floors <= 2 | 14,592 | 1.347 % |
| 38 | `retail_mixed_prewar` | 37 | `bodega_corner_taxpayer_1_2fl` | class in K* and floors <= 3 and year <= 1975 | 4,669 | 0.431 % |
| 39 | `retail_midrise` | 54 | `brown_brick_office_1985_midrise` | class in K* | 1,645 | 0.152 % |
| 40 | `hotel_prewar` | 43 | `hotel_masonry_1925` | class in H* and year <= 1940 | 532 | 0.049 % |
| 41 | `hotel_modern` | 42 | `hotel_glass_2010` | class in H* | 666 | 0.061 % |
| 42 | `supertall_office` | 18 | `supertall_glass_2015` | class in O*,RB and floors >= 55 and year >= 2005 | 8 | 0.001 % |
| 43 | `office_curtain_2010` | 17 | `glass_curtain_office_2010` | class in O*,RB and year >= 2000 and floors >= 10 | 61 | 0.006 % |
| 44 | `office_curtain_1970` | 16 | `glass_curtain_office_1970` | class in O*,RB and year 1962..1988 and floors >= 15 | 160 | 0.015 % |
| 45 | `office_international_1960` | 19 | `international_style_office_1960` | class in O*,RB and year 1950..1968 and floors >= 10 | 80 | 0.007 % |
| 46 | `office_art_deco_setback` | 25 | `limestone_office_1930_art_deco_setback` | class in O*,RB and year 1926..1945 and floors >= 18 | 130 | 0.012 % |
| 47 | `office_masonry_setback` | 26 | `masonry_office_1920_setback` | class in O*,RB and year 1916..1935 and floors >= 9 | 350 | 0.032 % |
| 48 | `office_terracotta_1905` | 23 | `terracotta_office_1905` | class in O*,RB and year <= 1925 and floors >= 7 | 541 | 0.050 % |
| 49 | `office_brown_brick_1985` | 54 | `brown_brick_office_1985_midrise` | class in O*,RB and year 1969..1999 | 825 | 0.076 % |
| 50 | `office_lowrise_prewar` | 26 | `masonry_office_1920_setback` | class in O*,RB and year <= 1945 | 3,498 | 0.323 % |
| 51 | `office_generic` | 54 | `brown_brick_office_1985_midrise` | class in O*,RB | 1,589 | 0.147 % |
| 52 | `supertall_residential` | 18 | `supertall_glass_2015` | class in D*,R4,RR,RM and floors >= 50 and year >= 2005 | 61 | 0.006 % |
| 53 | `nycha_campus_tower` | 13 | `nycha_tower_brick_1960` | floors >= 6 and year 1935..1975 and n_bldgs_on_lot >= 3 and footprint_area >= 400 and class in C/D/R/S | 2,601 | 0.240 % |
| 54 | `condo_midrise_2010` | 50 | `condo_midrise_2010_glass_brick` | class in D*,R4,RR,RM and year >= 2000 and floors 6..24 | 4,370 | 0.403 % |
| 55 | `condo_tower_2010` | 50 | `condo_midrise_2010_glass_brick` | class in D*,R4,RR,RM,RX and year >= 2000 and floors 25..49 | 278 | 0.026 % |
| 56 | `brown_brick_condo_1985` | 15 | `brown_brick_condo_1985_25fl` | class in D*,R4,RR and year 1976..1999 and floors >= 10 | 257 | 0.024 % |
| 57 | `mitchell_lama_slab` | 14 | `mitchell_lama_slab_1970_concrete` | class in D*,R4 and year 1962..1980 and floors >= 14 | 521 | 0.048 % |
| 58 | `postwar_white_brick` | 11 | `postwar_white_brick_1960_20fl` | class in D*,R4 and year 1955..1975 and floors >= 11 and borough == MN | 225 | 0.021 % |
| 59 | `postwar_red_brick_elevator` | 12 | `postwar_red_brick_1950_6fl_elevator` | class in D*,R4 and year 1945..1975 | 3,463 | 0.320 % |
| 60 | `prewar_beaux_arts_apt` | 9 | `prewar_apt_1910_beaux_arts_12fl` | class in D*,C6 and year 1898..1918 and floors >= 9 and borough == MN | 245 | 0.023 % |
| 61 | `art_deco_apt` | 10 | `bronx_art_deco_apt_1935` | class in D*,C* and year 1928..1942 and floors 4..12 | 9,503 | 0.877 % |
| 62 | `prewar_apt_1925` | 8 | `prewar_apt_1925_brick_limestone_6_12fl` | class in D*,C6,C1,C7,R4 and year 1915..1940 and floors >= 6 | 3,311 | 0.306 % |
| 63 | `garden_apt` | 51 | `garden_apt_1940_brick_2fl` | class in C9,C6,D1,C1,R2 and floors <= 4 and n_bldgs_on_lot >= 2 and year 1925..1965 | 13,454 | 1.242 % |
| 64 | `old_law_tenement_class` | 1 | `tenement_1880_brick_5fl_fire_escape` | class == C4 | 2,821 | 0.260 % |
| 65 | `old_law_tenement_era` | 1 | `tenement_1880_brick_5fl_fire_escape` | class in C1,C2,C7,S3,S4,S5,C0 and year 1879..1901 and floors 4..7 and borough in MN,BX,BK,QN | 3,822 | 0.353 % |
| 66 | `new_law_tenement` | 2 | `tenement_1905_new_law_6fl` | class in C1,C2,C7,C5,S5,S4,D1 and year 1902..1929 and floors 4..8 | 13,195 | 1.218 % |
| 67 | `bushwick_frame_3fl` | 32 | `bushwick_frame_3fl_1900` | class in C0,C2,C3,S3,B* and year 1885..1925 and floors == 3 and borough in BK,QN and (frame belt NTA or class B2) | 16,414 | 1.516 % |
| 68 | `fedders_special` | 33 | `fedders_special_2005` | class in C0,C1,C2,C3,B2,D1,RM and year >= 1998 and floors 3..6 | 19,306 | 1.783 % |
| 69 | `townhouse_modern` | 49 | `townhouse_modern_2015_glass_metal` | class in C0,C1,C7,D0,D1,RM,R* and year >= 2005 and floors 3..8 | 206 | 0.019 % |
| 70 | `walkup_prewar_tenement` | 2 | `tenement_1905_new_law_6fl` | class in C* and year <= 1945 and floors 4..7 | 4,376 | 0.404 % |
| 71 | `walkup_postwar` | 12 | `postwar_red_brick_1950_6fl_elevator` | class in C*,S* and floors 4..7 | 5,111 | 0.472 % |
| 72 | `federal_rowhouse` | 6 | `federal_rowhouse_1830_3fl_dormer` | class in A4,B1,C0,S2 and year <= 1840 and floors <= 3 | 47 | 0.004 % |
| 73 | `greek_revival_rowhouse` | 7 | `greek_revival_rowhouse_1840_3fl` | class in A4,B1,B3,C0,S2 and year 1830..1858 and floors 3..4 | 537 | 0.050 % |
| 74 | `brownstone_rowhouse_1860` | 4 | `brownstone_rowhouse_1860_3fl_stoop` | class in A4,B1,B3,C0,S2 and year 1845..1875 and floors <= 3 and borough in MN,BK and attached | 591 | 0.055 % |
| 75 | `brownstone_rowhouse_1880` | 3 | `brownstone_rowhouse_1880_4fl_stoop` | class in A4,A9,B1,B3,C0,C1,S2 and year 1855..1895 and floors 3..5 and borough in MN,BK,BX and attached | 1,566 | 0.145 % |
| 76 | `limestone_rowhouse_1900` | 5 | `limestone_rowhouse_1900_4fl_bowfront` | class in A4,A9,B1,B3,C0,S2 and year 1890..1915 and floors 3..4 and borough in MN,BK,BX and attached | 12,523 | 1.156 % |
| 77 | `brooklyn_frame_rowhouse` | 31 | `brooklyn_frame_rowhouse_1900_siding` | class in B2,B9,A9,C0,S2 and year 1880..1925 and floors 2..3 and borough in BK,QN,SI and (frame belt or B2) | 51,408 | 4.747 % |
| 78 | `rowhouse_brick_1920` | 34 | `rowhouse_brick_1920_2fl_flat_roof` | class in A5,B1,B2,B3,S2 and year 1900..1945 and floors 2..3 and attached | 125,942 | 11.629 % |
| 79 | `tudor_belt_house` | 29 | `queens_tudor_1930` | class in A*,B* and year 1918..1945 and NTA in the Tudor belt | 12,285 | 1.134 % |
| 80 | `stucco_mediterranean` | 52 | `stucco_mediterranean_1925` | class in A*,B* and year 1915..1940 and (lpc_material stucco or osm material stucco) | 59 | 0.005 % |
| 81 | `mansion_stone` | 53 | `stone_rubble_mansion_1900` | class in A3,A7,W3,N9,M9 and footprint_area >= 300 and floors >= 2 and year <= 1940 | 78 | 0.007 % |
| 82 | `queens_brick_2fam` | 28 | `queens_brick_2fam_1930` | class in B1,A5,B3 and year 1918..1948 and borough in QN,BX,BK,SI | 33,933 | 3.133 % |
| 83 | `queens_vinyl_2fam` | 27 | `queens_vinyl_2fam_1950` | class in B2,B3,B9,A2,A5,A1,A9 and year 1945..1979 | 122,958 | 11.353 % |
| 84 | `brick_house_postwar` | 28 | `queens_brick_2fam_1930` | class in B1,A5 attached and year >= 1946 and borough in QN,BX,BK,SI | 66,805 | 6.168 % |
| 85 | `si_qn_single_family_siding` | 30 | `staten_island_sf_1970_siding` | class in A*,B* and year >= 1960 and borough in SI,QN,BX | 33,520 | 3.095 % |
| 86 | `house_modern_generic` | 30 | `staten_island_sf_1970_siding` | class in A*,B*,R1,R2,R3,R6 and year >= 1960 | 13,574 | 1.253 % |
| 87 | `house_frame_prewar` | 31 | `brooklyn_frame_rowhouse_1900_siding` | class in A*,B* and year <= 1925 and detached | 51,249 | 4.732 % |
| 88 | `house_brick_prewar` | 34 | `rowhouse_brick_1920_2fl_flat_roof` | class in A*,B* | 60,554 | 5.591 % |
| 89 | `fallback_supertall` | 18 | `supertall_glass_2015` | floors >= 50 and year >= 2005 | 5 | 0.000 % |
| 90 | `fallback_tower_modern` | 17 | `glass_curtain_office_2010` | floors >= 20 and year >= 1990 | 94 | 0.009 % |
| 91 | `fallback_tower_postwar` | 13 | `nycha_tower_brick_1960` | floors >= 12 and year 1940..1989 | 314 | 0.029 % |
| 92 | `fallback_tower_prewar` | 26 | `masonry_office_1920_setback` | floors >= 10 | 616 | 0.057 % |
| 93 | `fallback_mid_modern` | 50 | `condo_midrise_2010_glass_brick` | floors >= 6 and year >= 1990 | 326 | 0.030 % |
| 94 | `fallback_mid_postwar` | 12 | `postwar_red_brick_1950_6fl_elevator` | floors >= 6 and year >= 1945 | 256 | 0.024 % |
| 95 | `fallback_mid_prewar` | 8 | `prewar_apt_1925_brick_limestone_6_12fl` | floors >= 6 | 1,303 | 0.120 % |
| 96 | `fallback_low_prewar_masonry` | 2 | `tenement_1905_new_law_6fl` | floors 3..5 and year <= 1929 | 16,762 | 1.548 % |
| 97 | `fallback_low_modern` | 33 | `fedders_special_2005` | floors 3..5 and year >= 1990 | 3,156 | 0.291 % |
| 98 | `fallback_low_postwar` | 12 | `postwar_red_brick_1950_6fl_elevator` | floors 3..5 | 30,984 | 2.861 % |
| 99 | `fallback_small_suburban` | 30 | `staten_island_sf_1970_siding` | floors <= 2 and borough in QN,SI | 14,169 | 1.308 % |
| 100 | `fallback_small_masonry` | 34 | `rowhouse_brick_1920_2fl_flat_roof` | always true | 25,553 | 2.359 % |

## Rationale per rule

**0. `accessory_garage` -> 38 `parking_garage_concrete`**  
*predicate:* `feature_code == 5110`  
OTI planimetric feature code 5110 is a detached (accessory) garage: a one-storey box with a vehicle door and no windows. 19.7 % of all NYC footprints. No dedicated kit class exists yet — see REPORT gap G-2.

**1. `transit_structure` -> 55 `subway_elevated_station_steel_1915`**  
*predicate:* `bldg_class in U2,U6,U7,T2,T9 or feature_code in 1000..1006`  
Elevated subway stations, train sheds, piers and other transportation structures (PLUTO U/T classes and the OTI 'other structure' feature codes) are steel-and-canopy structures, not masonry shells.

**2. `gas_station` -> 48 `gas_station_canopy`**  
*predicate:* `bldg_class in G3,G4,G5`  
PLUTO G3/G4/G5 are gasoline stations with/without retail or service: a small kiosk under a steel canopy.

**3. `parking_garage` -> 38 `parking_garage_concrete`**  
*predicate:* `bldg_class in G0,G1,G6,G7,G9`  
Multi-storey and licensed parking garages: cast-in-place or precast concrete decks with open spandrels.

**4. `auto_shop` -> 22 `warehouse_concrete_1950`**  
*predicate:* `bldg_class in G2,G8`  
Auto-body shops and car dealerships are single-storey masonry/concrete boxes with roll-down vehicle doors.

**5. `firehouse` -> 44 `firehouse_brick_1900`**  
*predicate:* `bldg_class == Y1`  
FDNY firehouses: 2-3 storey brick with limestone trim, a bracketed cornice and an apparatus door at grade. The 1880-1930 municipal type is still the dominant stock.

**6. `cast_iron_lpc_material` -> 20 `cast_iron_soho_1870`**  
*predicate:* `lpc_material contains 'cast iron' and floors >= 4`  
A designation report naming cast iron as the primary material is direct evidence of a cast-iron front (SoHo / Ladies' Mile / Tribeca store-and-loft buildings, 1855-1890).

**7. `soho_cast_iron_district` -> 20 `cast_iron_soho_1870`**  
*predicate:* `hist_district contains 'SoHo-Cast Iron' and floors >= 4 and year <= 1900`  
The SoHo-Cast Iron Historic District is by designation the largest concentration of cast-iron facades in the world; its 1855-1890 store-and-loft buildings are 5-6 storeys over a full-width cast-iron ground floor.

**8. `tribeca_store_loft` -> 56 `cast_iron_tribeca_store_1860`**  
*predicate:* `hist_district contains 'Tribeca' and floors 3..7 and year <= 1900`  
Tribeca's designated store-and-loft blocks (1850-1875) are marble/limestone-fronted with cast-iron piers at the ground floor — the Washington Market dry-goods type.

**9. `ladies_mile_terracotta` -> 23 `terracotta_office_1905`**  
*predicate:* `hist_district contains 'Ladies' Mile' and floors >= 6`  
The Ladies' Mile Historic District is the 1880-1915 cast-iron/terracotta emporium and loft belt; its tall buildings are Chicago-tripartite terracotta piles.

**10. `lpc_brownstone_rowhouse` -> 3 `brownstone_rowhouse_1880_4fl_stoop`**  
*predicate:* `lpc_material contains 'brownstone'/'sandstone' and floors 3..5 and class in rowhouse set`  
A designation report naming brownstone/sandstone on a 3-5 storey rowhouse is direct material evidence of the Italianate/neo-Grec brownstone type (1855-1895).

**11. `lpc_brownstone_low` -> 4 `brownstone_rowhouse_1860_3fl_stoop`**  
*predicate:* `lpc_material contains 'brownstone'/'sandstone' and floors <= 3`  
Pre-1875 brownstones are three storeys over a basement; the 1845-1875 Anglo-Italianate type.

**12. `lpc_wood_frame_house` -> 31 `brooklyn_frame_rowhouse_1900_siding`**  
*predicate:* `lpc_material contains 'wood frame'/'clapboard'/'shingle' and floors <= 3`  
A designation report naming a wood frame is direct evidence of the balloon-frame house type; today almost all carry vinyl or aluminium siding over the original clapboard.

**13. `lpc_tudor_revival` -> 29 `queens_tudor_1930`**  
*predicate:* `lpc_style contains 'Tudor'`  
Tudor Revival: stucco-and-half-timber gables over a brick base, steeply pitched roof — the Jackson Heights / Forest Hills Gardens / Riverdale garden-suburb type.

**14. `lpc_greek_revival` -> 7 `greek_revival_rowhouse_1840_3fl`**  
*predicate:* `lpc_style contains 'Greek Revival' and floors <= 4 and year <= 1860`  
Greek Revival rowhouses (1830-1855): red brick, brownstone trim, low stoop, dentilled wood cornice, 6/6 sash.

**15. `lpc_federal` -> 6 `federal_rowhouse_1830_3fl_dormer`**  
*predicate:* `lpc_style contains 'Federal' and floors <= 3`  
Federal rowhouses (1790-1840): 2.5 storeys, Flemish-bond brick, dormered pitched roof, 6/6 sash.

**16. `lpc_beaux_arts_apt` -> 9 `prewar_apt_1910_beaux_arts_12fl`**  
*predicate:* `lpc_style contains 'Beaux-Arts'/'neo-Renaissance' and floors >= 8 and class in apartment set`  
Beaux-Arts apartment houses (1898-1918) are limestone-faced with rusticated bases and heavy modillion cornices — Riverside Drive, Central Park West, Broadway.

**17. `lpc_art_deco` -> 10 `bronx_art_deco_apt_1935`**  
*predicate:* `lpc_style contains 'Art Deco' and floors 4..12`  
Art Deco apartment houses (1928-1942): polychrome brick, corner casement windows, stepped parapets — the Grand Concourse and the Brooklyn/Queens boulevards.

**18. `lpc_gothic_church` -> 35 `church_stone_gothic_1880`**  
*predicate:* `lpc_style contains 'Gothic' and class in M1,M9`  
Gothic Revival churches: rock-faced ashlar or brownstone, pointed-arch traceried windows, a tower or spire.

**19. `lpc_queen_anne_frame` -> 31 `brooklyn_frame_rowhouse_1900_siding`**  
*predicate:* `lpc_style contains 'Queen Anne' and floors <= 3 and borough in BK,QN,SI`  
Queen Anne frame houses of the 1880-1900 streetcar suburbs (Ditmas Park, Prospect Park South, Douglaston).

**20. `church_gothic_stone` -> 35 `church_stone_gothic_1880`**  
*predicate:* `class in M1,M9 and year <= 1920 and footprint_area >= 250`  
Large 19th-century churches are stone (rock-faced ashlar, brownstone or granite) with a steeply pitched nave roof and a spire.

**21. `church_brick` -> 36 `church_brick_romanesque_1890`**  
*predicate:* `class in M1,M2,M3,M4,M9`  
Smaller and later churches, missions, rectories and convents are brick Romanesque or vernacular with round-arched openings.

**22. `school_prewar` -> 39 `school_brick_1920`**  
*predicate:* `class in W1,W2,W3,W4,W5,W7,W8,W9 and year <= 1945`  
The C.B.J. Snyder-era public-school type (1895-1940): red brick with limestone trim, quoins, a heavy cornice, large 6/6 sash and a flat parapet roof.

**23. `school_postwar` -> 40 `school_brick_1960`**  
*predicate:* `class in W1..W9 except W6`  
Post-1950 schools: tan brick, ribbon windows, low parapet, rooftop mechanical.

**24. `university_modern` -> 54 `brown_brick_office_1985_midrise`**  
*predicate:* `class == W6`  
College and university buildings outside a designated campus core are 1960-1995 brown-brick/precast midrise.

**25. `hospital_modern` -> 41 `hospital_glass_2000`**  
*predicate:* `class in I1..I9 and (year >= 1985 or floors >= 8)`  
Modern hospital and clinic buildings: curtain wall or metal panel over a masonry podium, large rooftop plant.

**26. `hospital_prewar` -> 39 `school_brick_1920`**  
*predicate:* `class in I1..I9 and year <= 1945`  
Prewar hospitals and dispensaries share the institutional masonry type with the Snyder schools.

**27. `hospital_postwar` -> 54 `brown_brick_office_1985_midrise`**  
*predicate:* `class in I1..I9`  
1945-1985 hospitals and nursing homes: brown brick / precast midrise slabs.

**28. `civic_prewar` -> 39 `school_brick_1920`**  
*predicate:* `class in N,P,J,Y,Z (except Y1) and year <= 1945`  
Prewar civic buildings — libraries, museums, lodges, theatres, courthouses, police stations, asylums — are masonry with a cornice and monumental openings.

**29. `civic_postwar` -> 40 `school_brick_1960`**  
*predicate:* `class in N,P,J,Y,Z (except Y1)`  
Postwar civic buildings: tan brick / precast with ribbon glazing and rooftop plant.

**30. `self_storage` -> 46 `self_storage_metal_panel_2000`**  
*predicate:* `class == E7 or (class in E* and year >= 1990)`  
Self-storage conversions and new-builds: corrugated/ribbed metal panel over a concrete frame, minimal glazing.

**31. `daylight_factory` -> 45 `daylight_factory_concrete_1920`**  
*predicate:* `class in F*,L1,L2,L3 and year 1900..1935 and floors >= 4`  
The reinforced-concrete daylight factory (Kahn system, 1908-1935): concrete frame with wide steel-sash industrial windows filling the bays — Long Island City, Bush Terminal, the Bronx industrial belt.

**32. `industrial_loft_brick` -> 21 `industrial_loft_brick_1910`**  
*predicate:* `class in L*,F*,RW and year <= 1930 and floors >= 4`  
The 1895-1930 masonry loft: load-bearing red brick with brick-pier bays, corbelled cornice, water tower, fire escapes and a loading dock — DUMBO, the Garment District, Long Island City.

**33. `warehouse_low` -> 22 `warehouse_concrete_1950`**  
*predicate:* `class in E*,F*,L*,RW and floors <= 3`  
Single- and two-storey warehouses and light-manufacturing sheds: concrete or brick walls, roll-down loading doors, parapet roof.

**34. `loft_converted` -> 21 `industrial_loft_brick_1910`**  
*predicate:* `class in L*,F*,E*,RW`  
Remaining loft / factory / warehouse stock keeps the masonry loft treatment. MapPLUTO ``RM`` is a *mixed residential/commercial condo*, not a loft, and is deliberately excluded — it is handled by the condo rules.

**35. `big_box_retail` -> 47 `big_box_retail_precast_1990`**  
*predicate:* `class in K3,K5,K6,K8 or (class in K* and footprint_area >= 1800 and floors <= 2 and year >= 1975)`  
Department stores, franchise/shopping-centre retail and big boxes: precast tilt-up panels, a tall parapet sign band, a canopy over the entrance and a rooftop mechanical field.

**36. `limestone_bank` -> 24 `limestone_bank_1915`**  
*predicate:* `class in K4,O7,O9,K1 and year 1900..1940 and floors <= 6 and footprint_area >= 200`  
The 1900-1935 neighbourhood bank: limestone or granite temple front, engaged columns or pilasters, a single very tall banking-hall storey.

**37. `taxpayer_corner` -> 37 `bodega_corner_taxpayer_1_2fl`**  
*predicate:* `class in K1,K2,K9,S1,S9,RS and floors <= 2`  
The 'taxpayer': a one- or two-storey brick store row built to carry the taxes on a lot held for later development, and the corner bodega/deli type it produced across the outer boroughs.

**38. `retail_mixed_prewar` -> 37 `bodega_corner_taxpayer_1_2fl`**  
*predicate:* `class in K* and floors <= 3 and year <= 1975`  
Remaining low-rise store buildings keep the taxpayer treatment.

**39. `retail_midrise` -> 54 `brown_brick_office_1985_midrise`**  
*predicate:* `class in K*`  
Taller and later retail buildings: brown brick / precast with a glazed retail base.

**40. `hotel_prewar` -> 43 `hotel_masonry_1925`**  
*predicate:* `class in H* and year <= 1940`  
The 1905-1935 masonry hotel: brick over a limestone base, setbacks above the 1916 street wall, a marquee canopy and a heavy cornice.

**41. `hotel_modern` -> 42 `hotel_glass_2010`**  
*predicate:* `class in H*`  
Post-1990 hotels: curtain wall or metal panel with a canopy and a glazed lobby/bar at grade.

**42. `supertall_office` -> 18 `supertall_glass_2015`**  
*predicate:* `class in O*,RB and floors >= 55 and year >= 2005`  
Post-2005 supertalls: full unitised curtain wall, slender setback profile, mechanical crowns.

**43. `office_curtain_2010` -> 17 `glass_curtain_office_2010`**  
*predicate:* `class in O*,RB and year >= 2000 and floors >= 10`  
Post-2000 office towers: unitised curtain wall on a 4.2 m floor-to-floor module with a glazed lobby and a mechanical crown (Hudson Yards, the far West Side, Downtown Brooklyn, Long Island City).

**44. `office_curtain_1970` -> 16 `glass_curtain_office_1970`**  
*predicate:* `class in O*,RB and year 1962..1988 and floors >= 15`  
The 1961 Zoning Resolution's plaza bonus produced the 1962-1988 glass-and-aluminium slab set back behind an open plaza — Sixth Avenue, Water Street, Third Avenue.

**45. `office_international_1960` -> 19 `international_style_office_1960`**  
*predicate:* `class in O*,RB and year 1950..1968 and floors >= 10`  
International Style curtain-wall offices (Lever House 1952, Seagram 1958 and their imitators): green or grey glass in a bronze/aluminium grid on a travertine podium.

**46. `office_art_deco_setback` -> 25 `limestone_office_1930_art_deco_setback`**  
*predicate:* `class in O*,RB and year 1926..1945 and floors >= 18`  
The 1916 Zoning Resolution's setback envelope plus the Art Deco vocabulary produced the 1926-1940 limestone and brick ziggurat with a crown — Wall Street, Midtown, Court Square.

**47. `office_masonry_setback` -> 26 `masonry_office_1920_setback`**  
*predicate:* `class in O*,RB and year 1916..1935 and floors >= 9`  
1916-1935 masonry office buildings below tower height: tan brick over a limestone base, setbacks, a modillion cornice and a retail base.

**48. `office_terracotta_1905` -> 23 `terracotta_office_1905`**  
*predicate:* `class in O*,RB and year <= 1925 and floors >= 7`  
The 1895-1925 skeleton-frame office: terracotta and limestone cladding in a Chicago-tripartite base/shaft/capital composition with a projecting cornice.

**49. `office_brown_brick_1985` -> 54 `brown_brick_office_1985_midrise`**  
*predicate:* `class in O*,RB and year 1969..1999`  
The 1970-1999 brown-brick and precast midrise office — the dominant outer-borough and secondary-Manhattan office stock.

**50. `office_lowrise_prewar` -> 26 `masonry_office_1920_setback`**  
*predicate:* `class in O*,RB and year <= 1945`  
Remaining prewar office buildings keep the masonry setback treatment.

**51. `office_generic` -> 54 `brown_brick_office_1985_midrise`**  
*predicate:* `class in O*,RB`  
Remaining office buildings: brown brick / precast midrise.

**52. `supertall_residential` -> 18 `supertall_glass_2015`**  
*predicate:* `class in D*,R4,RR,RM and floors >= 50 and year >= 2005`  
Post-2005 supertall residential (Billionaires' Row, 57th Street, Downtown Brooklyn): curtain wall with limestone or metal spandrels, 3.4 m floor-to-floor.

**53. `nycha_campus_tower` -> 13 `nycha_tower_brick_1960`**  
*predicate:* `floors >= 6 and year 1935..1975 and n_bldgs_on_lot >= 3 and footprint_area >= 400 and class in C/D/R/S`  
NYCHA and Mitchell-Lama campuses are superblocks: several identical red-brick towers on one very large tax lot, cross-shaped or slab plan, no cornice, no storefront, aluminium sliders.

**54. `condo_midrise_2010` -> 50 `condo_midrise_2010_glass_brick`**  
*predicate:* `class in D*,R4,RR,RM and year >= 2000 and floors 6..24`  
The 2000s+ condo midrise: glass-and-brick or glass-and-metal facade, balconies, a canopy and a retail or lobby base.

**55. `condo_tower_2010` -> 50 `condo_midrise_2010_glass_brick`**  
*predicate:* `class in D*,R4,RR,RM,RX and year >= 2000 and floors 25..49`  
Post-2000 residential towers between 25 and 49 storeys: a glazed-and-masonry condo shaft over a retail or lobby base. The kit has no 2000s stone-clad residential tower, so the limestone-faced examples (15 Central Park West and its imitators) take this class — stated as gap G-4.

**56. `brown_brick_condo_1985` -> 15 `brown_brick_condo_1985_25fl`**  
*predicate:* `class in D*,R4,RR and year 1976..1999 and floors >= 10`  
The 1980s-90s brown-brick condo tower with punched windows, balconies and setbacks — the Upper East Side, Battery Park City, Downtown Brooklyn.

**57. `mitchell_lama_slab` -> 14 `mitchell_lama_slab_1970_concrete`**  
*predicate:* `class in D*,R4 and year 1962..1980 and floors >= 14`  
Mitchell-Lama and urban-renewal slabs (1962-1980): exposed concrete frame with brick infill, balconies, through-wall AC sleeves.

**58. `postwar_white_brick` -> 11 `postwar_white_brick_1960_20fl`**  
*predicate:* `class in D*,R4 and year 1955..1975 and floors >= 11 and borough == MN`  
The Manhattan white-glazed-brick tower (1955-1975): white or ivory glazed brick, aluminium sliders, balconies, a canopy — Second and Third Avenue, the Upper East Side.

**59. `postwar_red_brick_elevator` -> 12 `postwar_red_brick_1950_6fl_elevator`**  
*predicate:* `class in D*,R4 and year 1945..1975`  
The postwar six-storey red-brick elevator apartment house — the dominant 1945-1975 outer-borough type.

**60. `prewar_beaux_arts_apt` -> 9 `prewar_apt_1910_beaux_arts_12fl`**  
*predicate:* `class in D*,C6 and year 1898..1918 and floors >= 9 and borough == MN`  
Beaux-Arts apartment houses (1898-1918): limestone base and upper facade, rusticated ground floor, balconies and a heavy modillion cornice.

**61. `art_deco_apt` -> 10 `bronx_art_deco_apt_1935`**  
*predicate:* `class in D*,C* and year 1928..1942 and floors 4..12`  
Art Deco apartment houses (1928-1942): brick polychromy, corner casement windows, stepped parapet — the Grand Concourse, Ocean Parkway, Jackson Heights.

**62. `prewar_apt_1925` -> 8 `prewar_apt_1925_brick_limestone_6_12fl`**  
*predicate:* `class in D*,C6,C1,C7,R4 and year 1915..1940 and floors >= 6`  
The prewar apartment house (1915-1940): red brick over a limestone base, setbacks above the 1916 street wall, casement pairs, a canopy and a modillion cornice.

**63. `garden_apt` -> 51 `garden_apt_1940_brick_2fl`**  
*predicate:* `class in C9,C6,D1,C1,R2 and floors <= 4 and n_bldgs_on_lot >= 2 and year 1925..1965`  
Garden apartments (1925-1965): two- and three-storey red-brick blocks set in landscaped superblocks — Jackson Heights, Sunnyside Gardens, Parkchester, Bay Terrace.

**64. `old_law_tenement_class` -> 1 `tenement_1880_brick_5fl_fire_escape`**  
*predicate:* `class == C4`  
MapPLUTO class C4 is literally 'old law tenement': the 1879-1901 dumbbell plan on a 25 x 100 ft lot, red brick, segmental-arched openings, iron fire escape.

**65. `old_law_tenement_era` -> 1 `tenement_1880_brick_5fl_fire_escape`**  
*predicate:* `class in C1,C2,C7,S3,S4,S5,C0 and year 1879..1901 and floors 4..7 and borough in MN,BX,BK,QN`  
Multiple dwellings built between the 1879 Tenement House Act and the 1901 New Law are Old Law tenements: 5-6 storeys, 25 ft frontage, four windows across, fire escape on the street face.

**66. `new_law_tenement` -> 2 `tenement_1905_new_law_6fl`**  
*predicate:* `class in C1,C2,C7,C5,S5,S4,D1 and year 1902..1929 and floors 4..8`  
New Law tenements (1901 Tenement House Act - 1929): wider lot, interior courts, 5-7 storeys, buff/tan brick with limestone trim and a pressed-metal dentil cornice.

**67. `bushwick_frame_3fl` -> 32 `bushwick_frame_3fl_1900`**  
*predicate:* `class in C0,C2,C3,S3,B* and year 1885..1925 and floors == 3 and borough in BK,QN and (frame belt NTA or class B2)`  
The three-storey Brooklyn/Queens frame tenement (Bushwick, Ridgewood, Greenpoint, Astoria): balloon frame with a pressed-metal cornice, now sided in vinyl or aluminium; a store often occupies the corner ground floor.

**68. `fedders_special` -> 33 `fedders_special_2005`**  
*predicate:* `class in C0,C1,C2,C3,B2,D1,RM and year >= 1998 and floors 3..6`  
The 2000s infill multiple dwelling ('Fedders special'): tan or beige brick with through-wall AC sleeves punched under every window, a token balcony and a garage at grade.

**69. `townhouse_modern` -> 49 `townhouse_modern_2015_glass_metal`**  
*predicate:* `class in C0,C1,C7,D0,D1,RM,R* and year >= 2005 and floors 3..8`  
The 2005+ boutique townhouse/condo: metal panel and glass with full-height windows, balconies and a storefront or lobby base — Williamsburg, Long Island City, Chelsea.

**70. `walkup_prewar_tenement` -> 2 `tenement_1905_new_law_6fl`**  
*predicate:* `class in C* and year <= 1945 and floors 4..7`  
Remaining prewar 4-7 storey walk-up apartment houses take the New Law tenement treatment.

**71. `walkup_postwar` -> 12 `postwar_red_brick_1950_6fl_elevator`**  
*predicate:* `class in C*,S* and floors 4..7`  
Postwar 4-7 storey walk-ups: red brick, aluminium sliders, parapet roof.

**72. `federal_rowhouse` -> 6 `federal_rowhouse_1830_3fl_dormer`**  
*predicate:* `class in A4,B1,C0,S2 and year <= 1840 and floors <= 3`  
Federal rowhouses (1790-1840): 2.5 storeys, Flemish-bond red brick, brownstone lintels, dormered pitched roof — Greenwich Village, the Lower East Side, Vinegar Hill.

**73. `greek_revival_rowhouse` -> 7 `greek_revival_rowhouse_1840_3fl`**  
*predicate:* `class in A4,B1,B3,C0,S2 and year 1830..1858 and floors 3..4`  
Greek Revival rowhouses (1830-1855): red brick with brownstone trim, a low stoop, pilastered doorway and a dentilled wood cornice.

**74. `brownstone_rowhouse_1860` -> 4 `brownstone_rowhouse_1860_3fl_stoop`**  
*predicate:* `class in A4,B1,B3,C0,S2 and year 1845..1875 and floors <= 3 and borough in MN,BK and attached`  
The pre-1875 Italianate brownstone: three storeys over an English basement, a high stoop, bracketed cornice, 2/2 sash — Brooklyn Heights, Cobble Hill, the Village.

**75. `brownstone_rowhouse_1880` -> 3 `brownstone_rowhouse_1880_4fl_stoop`**  
*predicate:* `class in A4,A9,B1,B3,C0,C1,S2 and year 1855..1895 and floors 3..5 and borough in MN,BK,BX and attached`  
The neo-Grec / Renaissance Revival brownstone (1875-1895): four storeys over a basement, high stoop, pressed-metal bracketed cornice — Park Slope, Bed-Stuy, Harlem, Clinton Hill.

**76. `limestone_rowhouse_1900` -> 5 `limestone_rowhouse_1900_4fl_bowfront`**  
*predicate:* `class in A4,A9,B1,B3,C0,S2 and year 1890..1915 and floors 3..4 and borough in MN,BK,BX and attached`  
The turn-of-the-century limestone rowhouse: a bow or swell front in Indiana limestone with a stone modillion cornice — Park Slope, Crown Heights, Sunset Park, the Grand Concourse.

**77. `brooklyn_frame_rowhouse` -> 31 `brooklyn_frame_rowhouse_1900_siding`**  
*predicate:* `class in B2,B9,A9,C0,S2 and year 1880..1925 and floors 2..3 and borough in BK,QN,SI and (frame belt or B2)`  
The two- and three-storey frame rowhouse of the 1880-1925 streetcar belt: clapboard or shingle (now vinyl) over a balloon frame, a pressed-metal cornice and a wooden stoop.

**78. `rowhouse_brick_1920` -> 34 `rowhouse_brick_1920_2fl_flat_roof`**  
*predicate:* `class in A5,B1,B2,B3,S2 and year 1900..1945 and floors 2..3 and attached`  
The 1900-1945 attached brick rowhouse: two storeys, flat roof behind a corbelled parapet, a projecting brick or wood bay over a low stoop — Ridgewood, Bay Ridge, Bensonhurst, Astoria, Woodhaven.

**79. `tudor_belt_house` -> 29 `queens_tudor_1930`**  
*predicate:* `class in A*,B* and year 1918..1945 and NTA in the Tudor belt`  
The planned garden-suburb Tudor of 1918-1940 (Forest Hills Gardens, Jackson Heights, Jamaica Estates, Riverdale/Fieldston, Todt Hill): stucco with half-timbering over brick, steep slate/tile roof.

**80. `stucco_mediterranean` -> 52 `stucco_mediterranean_1925`**  
*predicate:* `class in A*,B* and year 1915..1940 and (lpc_material stucco or osm material stucco)`  
The 1920s Mediterranean / Spanish Colonial Revival house: stucco walls, clay-tile hipped roof, arched openings — Jackson Heights, Forest Hills, Ditmas Park, Staten Island's south shore.

**81. `mansion_stone` -> 53 `stone_rubble_mansion_1900`**  
*predicate:* `class in A3,A7,W3,N9,M9 and footprint_area >= 300 and floors >= 2 and year <= 1940`  
Free-standing stone mansions and institutional houses (Riverdale, Todt Hill, Prospect Park South, Fort Greene): rock-faced stone with a steep slate roof and dormers.

**82. `queens_brick_2fam` -> 28 `queens_brick_2fam_1930`**  
*predicate:* `class in B1,A5,B3 and year 1918..1948 and borough in QN,BX,BK,SI`  
The interwar brick two-family: PLUTO class B1 is by definition *brick*; a projecting brick or wood bay, soldier-course lintels, a corbelled parapet and a garage under the stoop.

**83. `queens_vinyl_2fam` -> 27 `queens_vinyl_2fam_1950`**  
*predicate:* `class in B2,B3,B9,A2,A5,A1,A9 and year 1945..1979`  
The postwar detached/semi-detached two-family: PLUTO class B2 is by definition *frame*; vinyl or aluminium siding over the frame, a low-pitched roof, a picture window and an attached garage.

**84. `brick_house_postwar` -> 28 `queens_brick_2fam_1930`**  
*predicate:* `class in B1,A5 attached and year >= 1946 and borough in QN,BX,BK,SI`  
MapPLUTO class B1 is by definition a *brick* two-family: the post-war outer-borough B1 stock is the same brick box as the interwar type, so it must never fall through to a sided-frame class.

**85. `si_qn_single_family_siding` -> 30 `staten_island_sf_1970_siding`**  
*predicate:* `class in A*,B* and year >= 1960 and borough in SI,QN,BX`  
The post-1960 Staten Island / eastern Queens single family: vinyl siding with a brick veneer water table, a low-pitched roof, an attached garage.

**86. `house_modern_generic` -> 30 `staten_island_sf_1970_siding`**  
*predicate:* `class in A*,B*,R1,R2,R3,R6 and year >= 1960`  
Post-1960 one- and two-family houses elsewhere in the city take the same sided-frame treatment.

**87. `house_frame_prewar` -> 31 `brooklyn_frame_rowhouse_1900_siding`**  
*predicate:* `class in A*,B* and year <= 1925 and detached`  
Detached pre-1925 frame houses across Brooklyn, Queens and Staten Island: clapboard/shingle (now vinyl) with a wood cornice and a porch.

**88. `house_brick_prewar` -> 34 `rowhouse_brick_1920_2fl_flat_roof`**  
*predicate:* `class in A*,B*`  
Remaining one- and two-family houses: the interwar brick type.

**89. `fallback_supertall` -> 18 `supertall_glass_2015`**  
*predicate:* `floors >= 50 and year >= 2005`  
Any remaining post-2005 building above 50 storeys is a curtain-walled supertall.

**90. `fallback_tower_modern` -> 17 `glass_curtain_office_2010`**  
*predicate:* `floors >= 20 and year >= 1990`  
Any remaining post-1990 tower is curtain-walled.

**91. `fallback_tower_postwar` -> 13 `nycha_tower_brick_1960`**  
*predicate:* `floors >= 12 and year 1940..1989`  
Remaining 1940-1989 towers take the postwar brick tower treatment.

**92. `fallback_tower_prewar` -> 26 `masonry_office_1920_setback`**  
*predicate:* `floors >= 10`  
Remaining tall buildings take the prewar masonry setback treatment.

**93. `fallback_mid_modern` -> 50 `condo_midrise_2010_glass_brick`**  
*predicate:* `floors >= 6 and year >= 1990`  
Remaining post-1990 midrise: glass-and-brick condo treatment.

**94. `fallback_mid_postwar` -> 12 `postwar_red_brick_1950_6fl_elevator`**  
*predicate:* `floors >= 6 and year >= 1945`  
Remaining postwar midrise: red-brick elevator apartment treatment.

**95. `fallback_mid_prewar` -> 8 `prewar_apt_1925_brick_limestone_6_12fl`**  
*predicate:* `floors >= 6`  
Remaining prewar and unknown-year midrise: prewar apartment treatment.

**96. `fallback_low_prewar_masonry` -> 2 `tenement_1905_new_law_6fl`**  
*predicate:* `floors 3..5 and year <= 1929`  
Remaining prewar 3-5 storey buildings: New Law tenement treatment.

**97. `fallback_low_modern` -> 33 `fedders_special_2005`**  
*predicate:* `floors 3..5 and year >= 1990`  
Remaining post-1990 3-5 storey buildings: the 2000s infill type.

**98. `fallback_low_postwar` -> 12 `postwar_red_brick_1950_6fl_elevator`**  
*predicate:* `floors 3..5`  
Remaining 3-5 storey buildings: postwar brick treatment.

**99. `fallback_small_suburban` -> 30 `staten_island_sf_1970_siding`**  
*predicate:* `floors <= 2 and borough in QN,SI`  
Remaining Queens / Staten Island low structures: sided frame treatment.

**100. `fallback_small_masonry` -> 34 `rowhouse_brick_1920_2fl_flat_roof`**  
*predicate:* `always true`  
Exhaustive fallback: a low masonry structure. Guarantees that no building leaves the classifier unclassified.

"""Target landmark list (ARCHITECTURE §4.6 / brief §4.2) with WGS84 coordinates and published roof heights.

Each entry: ``id`` (slug), ``name``, ``lon``/``lat`` (WGS84), ``radius`` (m, coordinate search radius),
``name_re`` (regex against the OTI footprint ``name`` field), ``lpc_re`` (regex against the LPC individual landmark
site name; every footprint whose centroid lies in the matching site polygon is taken), ``min_h``/``max_h`` (height
filter for coordinate matches), ``pick`` (``tallest`` | ``largest`` | ``nearest`` | ``all``), ``expected_h`` (published
roof height in metres, for the deviation report; ``None`` when the published figure is a spire/architectural height
that the LiDAR roof field cannot be compared to), ``group`` (optional group id: a union row is emitted per group).

Coordinates are building centres taken from the buildings' published geographic coordinates; the search radius and
height filters make each match unambiguous in dense Midtown/Downtown.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LandmarkSpec:
    id: str
    name: str
    lon: float
    lat: float
    radius: float = 60.0
    name_re: str = ""
    lpc_re: str = ""
    min_h: float = 0.0
    max_h: float = 1e9
    pick: str = "largest"
    expected_h: float | None = None
    group: str = ""
    min_area: float = 0.0


L = LandmarkSpec
LANDMARKS: list[LandmarkSpec] = [
    # ---- supertalls / towers (LiDAR height_roof compared against published roof heights) ----
    L("empire_state_building", "Empire State Building", -73.985656, 40.748433, 80, r"Empire State Building", r"^Empire State Building$", 300, pick="tallest", expected_h=381.0),
    L("chrysler_building", "Chrysler Building", -73.975311, 40.751652, 60, r"Chrysler Building", r"^Chrysler Building$", 200, pick="tallest", expected_h=282.0),
    L("one_wtc", "One World Trade Center", -74.013382, 40.712742, 90, r"Tower 1 World Trade|One World Trade|1 World Trade", "", 350, pick="tallest", expected_h=417.0, group="wtc_site"),
    L("wtc_3", "3 World Trade Center", -74.010600, 40.710000, 70, r"Tower 3 World Trade|3 World Trade", "", 250, pick="tallest", expected_h=329.0, group="wtc_site"),
    L("wtc_4", "4 World Trade Center", -74.012000, 40.709900, 70, r"Tower 4 World Trade|4 World Trade", "", 200, pick="tallest", expected_h=298.0, group="wtc_site"),
    L("wtc_7", "7 World Trade Center", -74.011700, 40.713300, 70, r"7 World Trade", "", 150, pick="tallest", expected_h=226.0, group="wtc_site"),
    L("wtc_oculus", "World Trade Center Transportation Hub (Oculus)", -74.011300, 40.711500, 60, r"Oculus|Transportation Hub", "", 20, 90, pick="largest", group="wtc_site"),
    L("wtc_memorial_museum", "National September 11 Memorial Museum Pavilion", -74.012500, 40.711500, 60, r"Memorial Museum|9/11 Museum", "", 10, 60, pick="largest", group="wtc_site"),
    L("flatiron_building", "Flatiron Building", -73.989699, 40.741061, 60, r"Flatiron", r"^Flatiron Building$", 50, pick="tallest", expected_h=87.0),
    L("grand_central_terminal", "Grand Central Terminal", -73.977229, 40.752726, 90, r"Grand Central Terminal", r"^Grand Central Terminal$", 0, pick="largest", min_area=3000),
    L("rockefeller_center_30_rock", "30 Rockefeller Plaza", -73.978674, 40.758740, 80, r"RCA Building|30 Rockefeller|Comcast Building|GE Building", "", 200, pick="tallest", expected_h=260.0, group="rockefeller_center"),
    L("radio_city_music_hall", "Radio City Music Hall", -73.979939, 40.759950, 60, r"Radio City", r"^Radio City Music Hall", 0, pick="largest", group="rockefeller_center", min_area=2000),
    L("st_patricks_cathedral", "St. Patrick's Cathedral", -73.975993, 40.758465, 70, r"Patrick'?s Cathedral", r"^Saint Patrick's Cathedral Complex$", 0, pick="all", min_area=500),
    L("one_vanderbilt", "One Vanderbilt", -73.978537, 40.752971, 70, r"One Vanderbilt|1 Vanderbilt", "", 350, pick="tallest", expected_h=427.0),
    L("hudson_yards_30", "30 Hudson Yards", -74.001100, 40.753900, 70, r"30 Hudson Yards", "", 300, pick="tallest", expected_h=387.0, group="hudson_yards"),
    L("hudson_yards_10", "10 Hudson Yards", -74.001900, 40.752200, 70, r"10 Hudson Yards", "", 200, 320, pick="tallest", expected_h=273.0, group="hudson_yards"),
    L("hudson_yards_35", "35 Hudson Yards", -74.001900, 40.754700, 65, r"35 Hudson Yards", "", 250, 340, pick="tallest", expected_h=308.0, group="hudson_yards"),
    L("hudson_yards_55", "55 Hudson Yards", -74.000000, 40.754700, 65, r"55 Hudson Yards", "", 180, 280, pick="tallest", expected_h=237.0, group="hudson_yards"),
    L("hudson_yards_50", "50 Hudson Yards", -73.999400, 40.753900, 65, r"50 Hudson Yards", "", 250, pick="tallest", expected_h=308.0, group="hudson_yards"),
    L("hudson_yards_15", "15 Hudson Yards", -74.003300, 40.753600, 60, r"15 Hudson Yards", "", 200, pick="tallest", expected_h=279.0, group="hudson_yards"),
    L("the_vessel", "Vessel (Hudson Yards)", -74.002200, 40.753800, 45, r"Vessel", "", 25, 80, pick="nearest", group="hudson_yards"),
    L("the_met", "Metropolitan Museum of Art", -73.963244, 40.779437, 120, r"Metropolitan Museum", r"^Metropolitan Museum of Art$", 0, pick="all", min_area=1000),
    L("guggenheim_museum", "Solomon R. Guggenheim Museum", -73.958971, 40.782980, 60, r"Guggenheim", r"^Solomon R\. Guggenheim Museum$", 0, pick="all", min_area=300),
    L("amnh", "American Museum of Natural History", -73.973988, 40.781324, 150, r"Natural History", r"^American Museum of Natural History$", 0, pick="all", min_area=1000),
    L("lincoln_center", "Lincoln Center for the Performing Arts", -73.983400, 40.772500, 130, r"Lincoln Center|Metropolitan Opera|Geffen Hall|Avery Fisher|Koch Theater|New York State Theater", "", 15, pick="all", min_area=2500),
    L("madison_square_garden", "Madison Square Garden", -73.993439, 40.750504, 90, r"Madison Square Garden", "", 30, pick="largest", min_area=5000),
    L("nypl_main", "New York Public Library, Stephen A. Schwarzman Building", -73.982253, 40.753182, 90, r"New York Public Library", r"^New York Public Library, Astor, Lenox and Tilden Foundations$", 0, pick="largest", min_area=3000),
    L("woolworth_building", "Woolworth Building", -74.008398, 40.712400, 60, r"Woolworth", r"^Woolworth Building$", 150, pick="tallest", expected_h=241.0),
    L("city_hall", "New York City Hall", -74.006058, 40.712775, 70, r"City Hall", r"^City Hall$", 0, pick="largest", min_area=1000),
    L("municipal_building", "Manhattan Municipal Building", -74.004072, 40.712808, 80, r"Municipal Building", r"^Municipal Building$", 100, pick="tallest", expected_h=177.0),
    L("nyse", "New York Stock Exchange", -74.011265, 40.706877, 70, r"Stock Exchange", r"^New York Stock Exchange$", 0, pick="largest", min_area=800),
    L("trinity_church", "Trinity Church", -74.012174, 40.708120, 60, r"Trinity Church", r"^Trinity Church and Graveyard$", 0, pick="largest", min_area=300),
    L("the_dakota", "The Dakota", -73.976285, 40.776563, 60, r"Dakota", r"^Dakota Apartments$", 0, pick="largest", min_area=1500),
    L("the_plaza", "The Plaza Hotel", -73.974345, 40.764541, 70, r"Plaza Hotel", r"^Plaza Hotel$", 40, pick="largest", expected_h=76.0),
    L("apollo_theater", "Apollo Theater", -73.950095, 40.810022, 50, r"Apollo Theat", r"^Apollo Theater$", 0, pick="largest", min_area=300),
    L("yankee_stadium", "Yankee Stadium", -73.926175, 40.829643, 180, r"Yankee Stadium", "", 15, pick="largest", min_area=10000),
    L("citi_field", "Citi Field", -73.845821, 40.757088, 180, r"Citi Field", "", 15, pick="largest", min_area=10000),
    L("barclays_center", "Barclays Center", -73.975225, 40.682661, 130, r"Barclays", "", 15, pick="largest", min_area=8000),
    L("432_park_avenue", "432 Park Avenue", -73.971737, 40.761570, 60, r"432 Park", "", 380, pick="tallest", expected_h=426.0),
    L("111_west_57th", "111 West 57th Street (Steinway Tower)", -73.977603, 40.764662, 60, r"111 West 57|Steinway", "", 380, pick="tallest", expected_h=435.0),
    L("central_park_tower", "Central Park Tower", -73.980904, 40.766486, 60, r"Central Park Tower", "", 420, pick="tallest", expected_h=472.0),
    L("one57", "One57", -73.979140, 40.765320, 60, r"One57|157 West 57", "", 250, 340, pick="tallest", expected_h=306.0),
    L("220_central_park_south", "220 Central Park South", -73.980659, 40.767176, 50, r"220 Central Park", "", 250, 350, pick="tallest", expected_h=290.0),
    L("53w53", "53 West 53rd Street (MoMA Tower)", -73.977650, 40.761780, 60, r"53 West 53|53W53|MoMA Tower", "", 280, pick="tallest", expected_h=320.0),
    L("un_secretariat", "United Nations Secretariat Building", -73.968100, 40.749000, 90, r"United Nations|Secretariat", "", 120, pick="tallest", expected_h=155.0),
    L("domino_sugar_refinery", "Domino Sugar Refinery", -73.967580, 40.714345, 90, r"Domino", r"Havemeyers? (&|and) Elder", 20, pick="largest", min_area=1500),
    L("one_times_square", "One Times Square", -73.986378, 40.756542, 45, r"One Times Square|1 Times Square", "", 80, pick="tallest", expected_h=110.0, group="times_square_screens"),
    L("bank_of_america_tower", "Bank of America Tower (One Bryant Park)", -73.984688, 40.755514, 70, r"Bank of America Tower|One Bryant Park", "", 200, pick="tallest", expected_h=288.0),
    L("hearst_tower", "Hearst Tower", -73.982560, 40.766530, 60, r"Hearst", r"^Hearst Magazine Building$", 100, pick="tallest", expected_h=182.0),
    L("seagram_building", "Seagram Building", -73.972077, 40.758392, 60, r"Seagram", r"^Seagram Building$", 100, pick="tallest", expected_h=157.0),
    L("lever_house", "Lever House", -73.973590, 40.759460, 50, r"Lever House", r"^Lever House$", 50, pick="tallest", expected_h=94.0),
    L("citigroup_center", "Citigroup Center (601 Lexington Avenue)", -73.970380, 40.758480, 70, r"Citigroup Center|Citicorp", r"^Citicorp Center", 200, pick="tallest", expected_h=279.0),
    L("metlife_building", "MetLife Building (200 Park Avenue)", -73.976530, 40.753630, 80, r"Met ?Life Building|Pan Am Building|200 Park Ave", "", 200, pick="tallest", expected_h=246.0),
    L("ellis_island_main", "Ellis Island Main Immigration Building", -74.039750, 40.699360, 130, r"Ellis Island", "", 10, pick="largest", min_area=2000),
    L("coney_island_cyclone", "Coney Island Cyclone", -73.977790, 40.574650, 80, r"Cyclone", r"^The Cyclone$", 0, pick="all", group="coney_island"),
    L("coney_island_wonder_wheel", "Wonder Wheel", -73.978800, 40.573700, 60, r"Wonder Wheel", r"^Wonder Wheel$", 0, pick="all", group="coney_island"),
    # ---- Times Square screen buildings ----
    L("four_times_square", "4 Times Square (Condé Nast Building)", -73.986600, 40.756100, 55, r"Conde.?Nast|4 Times Square", "", 150, pick="tallest", expected_h=247.0, group="times_square_screens"),
    L("three_times_square", "3 Times Square (Reuters Building)", -73.987300, 40.756600, 45, r"Reuters|3 Times Square", "", 100, pick="tallest", expected_h=174.0, group="times_square_screens"),
    L("five_times_square", "5 Times Square", -73.987300, 40.755300, 45, r"5 Times Square|Ernst & Young", "", 120, pick="tallest", expected_h=178.0, group="times_square_screens"),
    L("times_square_tower", "Times Square Tower (7 Times Square)", -73.986800, 40.755000, 45, r"Times Square Tower|7 Times Square", "", 150, pick="tallest", expected_h=221.0, group="times_square_screens"),
    L("1500_broadway", "1500 Broadway", -73.986000, 40.757300, 40, r"1500 Broadway", "", 60, pick="tallest", group="times_square_screens"),
    L("1501_broadway", "Paramount Building (1501 Broadway)", -73.987100, 40.757500, 45, r"Paramount Building|1501 Broadway", r"^Paramount Building$", 80, pick="tallest", expected_h=137.0, group="times_square_screens"),
    L("1515_broadway", "1515 Broadway (Paramount Plaza)", -73.986500, 40.758100, 50, r"Minskoff|1515 Broadway|Paramount Plaza", "", 120, pick="tallest", expected_h=168.0, group="times_square_screens"),
    L("1535_broadway", "1535 Broadway (Marriott Marquis)", -73.985700, 40.758700, 50, r"Marriott Marquis|1535 Broadway", "", 120, pick="tallest", expected_h=175.0, group="times_square_screens"),
    L("1540_broadway", "1540 Broadway (Bertelsmann Building)", -73.984800, 40.758400, 45, r"Bertelsmann|1540 Broadway", "", 150, pick="tallest", expected_h=224.0, group="times_square_screens"),
    L("1585_broadway", "1585 Broadway (Morgan Stanley Building)", -73.985200, 40.759700, 45, r"Morgan Stanley Building|1585 Broadway", "", 150, pick="tallest", expected_h=208.0, group="times_square_screens"),
    L("tsx_broadway", "TSX Broadway (1568 Broadway)", -73.984800, 40.759400, 35, r"TSX|1568 Broadway", "", 100, pick="tallest", group="times_square_screens"),
    L("20_times_square", "20 Times Square (701 Seventh Avenue)", -73.984700, 40.760100, 40, r"20 Times Square|701 Seventh", "", 100, pick="tallest", group="times_square_screens"),
]

GROUP_NAMES = {
    "wtc_site": "World Trade Center site",
    "hudson_yards": "Hudson Yards",
    "rockefeller_center": "Rockefeller Center",
    "times_square_screens": "Times Square screen buildings",
    "coney_island": "Coney Island amusement structures",
}

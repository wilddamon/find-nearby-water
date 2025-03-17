# A list of tags to query the Overpass (Open Street Map) API to search for
# water-related features. These selection of these tags were informed by
# * https://wiki.openstreetmap.org/wiki/Swimming_and_bathing
# https://wiki.openstreetmap.org/wiki/Map_features#Water
# https://wiki.openstreetmap.org/wiki/Map_features#Waterway
# https://wiki.openstreetmap.org/wiki/Map_features#Water_related
# https://wiki.openstreetmap.org/wiki/Map_features#Leisure
# https://wiki.openstreetmap.org/wiki/Map_features#Sport
# https://wiki.openstreetmap.org/wiki/Key:swimming_pool

TAGS = {
    "natural": [
        "water",  # inland water bodies
        "bay",
        "beach",
        "blowhole",
        "coastline",
        "shoal",
        "spring",
        "wetland",
        # These three may be useful for finding rock fishing points.
        "peninsula",
        "isthmus",
        "cape",
    ],
    "water": True,
    "waterway": [
        "river",
        "stream",
        "tidal_channel",
        "canal",
        "drain",
        "ditch",
        "dam",
        "weir",
        "waterfall",
    ],
    "leisure": [
        "swimming_pool",
        "swimming_area",
        "water_park",
        "paddling_pool",
        "marina",
        "hot_tub",
        "bathing_place",
    ],
    "man_made": [
        "breakwater",
        "bridge",
        "pier",
        "storage_tank",
        "tailings_pond",
        "water_well",
    ],
    "sport": [
        "swimming",  # marks indoor facilities used for these sports
        "scuba_diving",
    ],
    "amenity": [
        "fountain",
        "dive_centre",
        "public_bath",
        "spa",
    ],
    "swimming_pool": True,
    "animal": ["swimming"],
    "club": ["surf_life_saving"],
    "emergency": ["lifeguard"],
    "playground": ["splash_pad"],
}

# Notes:
# water: True expands to
# water: [
#     'river',
#     'oxbow',
#     'canal',
#     'ditch',
#     'lock',
#     'fish_pass',
#     'lake',
#     'reservoir',
#     'pond',
#     'basin',
#     'lagoon',
#     'stream_pool',
#     'reflecting_pool',
#     'moat',
#     'wastewater',
# ]
#
# swimming_pool: True expands to:
# swimming_pool: [
#     'inground',
#     'indoor',
#     'outdoor',
#     'swimming',
#     'plunge',
#     'wading',
#     'diving',
#     'rock_pool',
#     'wave_pool',
# ]

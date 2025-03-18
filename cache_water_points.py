# Fetches the water features within a large radius and caches them in a csv file.

import argparse
import collections
import sys
import logging

import geopandas
import osmnx
import pandas
from shapely.geometry import Point

import water_tags

# Effectively suppreses warnings so they don't show on the command line
logging.captureWarnings(True)


RADIUS_METRES = 500
OUTPUT_WIDTH = 100
MAX_ACCURACY_METRES = 111

_cached_features = None


def get_cached_features_near_point(patient_id, radius, max_features=None):
    global _cached_features
    if _cached_features is None:
        _cached_features = pandas.read_csv("data/cached_water_features.csv")

    row = _cached_features[_cached_features["patient_id"] == patient_id]
    assert len(row) == 1

    row = row.iloc[0]

    relevant_count = 0
    for i in range(min(row["water_count"], OUTPUT_WIDTH)):
        if row[f"water_distance_{i}"] > radius:
            relevant_count = i - 1 if i > 0 else 0
            break
    
    if max_features is not None:
        row = row[: (max_features * 4) + 1]
        if relevant_count < max_features:
            # Clear out further away features
            for i in range(relevant_count + 1, max_features):
                row[f"water_name_{i}"] = None
                row[f"water_type_{i}"] = None
                row[f"water_distance_{i}"] = None
                row[f"water_lifeguard_{i}"] = None
    else:
        row = row[: (relevant_count * 4) + 1]

    row["water_count"] = min(relevant_count, max_features)
    return row


def row_to_type(row):
    # Special case leisure: sports_centre with sport: swimming -> swimming_pool
    result = ""
    if (
        "leisure" in row
        and row["leisure"] == "sports_centre"
        and "sport" in row
        and row["sport"] == "swimming"
    ):
        return "swimming_pool"

    if "emergency" in row and row["emergency"] == "lifeguard":
        return "lifeguard"

    # Prioritise the man_made tag over others.
    if "man_made" in row and (
        row["man_made"] == "breakwater" or row["man_made"] == "pier"
    ):
        return row["man_made"]

    if "playground" in row and row["playground"] == "splash_pad":
        return "splash_pad"

    if "swimming_pool" in row and row["swimming_pool"] == "animal":
        return "animal_swimming_pool"

    # Fountain/reflecting pool - some specify both, some have only
    # reflecting_pool. Below prioritises fountain if both present.
    if "amenity" in row:
        if row["amenity"] == "fountain":
            return "fountain"
        if (
            row["amenity"] == "public_bath"
            and "leisure" in row
            and row["leisure"] == "swimming_area"
        ):
            return "swimming_area"
    if "water" in row and row["water"] == "reflecting_pool":
        return "reflecting_pool"

    for key in water_tags.TAGS:
        if key not in row or pandas.isna(row[key]):
            continue
        if (
            key == "sport"
            or (key == "natural" and row[key] == "water")
            or (key == "water" and row[key] == "shallow")
        ):
            # Skip, it will also be tagged with something else.
            continue
        if key == "swimming_pool":
            if result != "" and result != "swimming_pool":
                print(f"multirows detected: have {result}, key {key}")
                print(row)
            result = "swimming_pool"
        elif key == "animal":
            if result != "":
                print(f"multirows detected: have {result}, key {key}")
                print(row)
            result = f"{key}_{row[key]}"
        elif key == "water":
            if result != "":
                print(f"multirows detected: have {result}, key {key}")
                print(row)
            result = row[key]
        elif row[key] in water_tags.TAGS[key]:
            if result != "" and result != row[key]:
                print(f"multirows detected: have {result}, key {key}")
                print(row)
            result = row[key]

    # Infer from the name of the feature if possible. This is not exhaustive,
    # and may need more additions for other data.
    if (
        result == ""
        and "name" in row
        and pandas.notna(row["name"])
        and "lake" in row["name"].lower()
    ):
        return "lake"
    if result == "" and "sport" in row and row["sport"] == "scuba_diving":
        return "scuba_diving"
    if result == "lagoon,_lake":
        # Probably a mistake; Curl Curl Lagoon is tagged thus.
        return "lagoon"

    # Some things are tagged with "natural:water" with no other rows.
    if result == "" and "natural" in row and pandas.notna(row["natural"]):
        return f"natural:{row['natural']}"
    return result


# Attempt to infer the privacy of a swimming pool.
# Notable problems include:
#     - hotel pools without a tourism tag, which have access:customers.
def infer_pool_privacy(row, display=False):
    access = None
    if "access" in row and pandas.notna(row["access"]):
        access = row["access"]
    if pandas.isna(access) and "ownership" in row and pandas.notna(row["ownership"]):
        access = row["ownership"]

    if (
        access == "private"
        or access == "no"
        or access == "permissive"
        or access == "unknown"
    ):
        return "private"

    if "tourism" in row and (
        # Hotels etc are usually private
        row["tourism"] == "hotel" or row["tourism"] == "caravan_site"
    ):
        return "private"

    if access == "yes" or access == "customers" or access == "public":
        return "public"
    if (
        "leisure" in row
        and row["leisure"] == "sports_centre"
        and "sport" in row
        and row["sport"] == "swimming"
    ):
        return "public"

    if (
        "leisure" in row
        and row["leisure"] == "swimming_pool"
        and ("name" not in row or pandas.isna(row["name"]))
        and pandas.isna(access)
    ):
        # Unnamed swimming pools are usually private
        return "private"

    if (
        "leisure" in row
        and row["leisure"] == "swimming_pool"
        and "name" in row
        and pandas.notna(row["name"])
        and pandas.isna(access)
    ):
        # Named swimming pools are usually public
        return "public"

    if (
        row["leisure"] == "swimming_area"
        or row["leisure"] == "water_park"
        or row["leisure"] == "sports_centre"
    ):
        # swimming areas, water parks, and sports centres are usually public
        return "public"

    if (
        "name" in row
        and pandas.notna(row["name"])
        and row["sport"] == "swimming"
        and ("access" not in row or pandas.isna(row["access"]))
    ):
        return "public"

    if "water" in row and row["water"] == "stream_pool":
        return "public"

    if display:
        print(f"Unable to infer pool privacy. Access: {access}; row:")
        print(row)

    return None


def pool_type_from_row(row):
    return row["swimming_pool"] if "swimming_pool" in row else None


def lifeguard_from_row(row):
    for key in ["lifeguard", "supervised"]:
        if key in row:
            return row[key]
    return None


def calc_distance_to_point(gdf, lat, lng):
    # EPSG 3308 is a NSW-specific projection that corresponds to GDA94 Lambert.
    # https://www.spatial.nsw.gov.au/surveying/geodesy/projections
    # Point(x, y) -> Point(lng, lat)
    point = geopandas.GeoSeries([Point(lng, lat)], crs=gdf.crs).to_crs(epsg=3308)

    def distance_to_point(geometry):
        return geometry.distance(point).round(2)

    gdf["distance"] = gdf.to_crs(epsg=3308)["geometry"].apply(distance_to_point)


def latlng_accuracy(lat, lng):
    # https://en.wikipedia.org/wiki/Decimal_degrees
    if lat is None or lng is None:
        return None

    # take the least accurate for lat and lng.
    accuracy = min(len(str(lat).split(".")[1]), len(str(lng).split(".")[1]))

    # Map to distance.
    return 111000 / pow(10, accuracy - 1)


def dedupe_pools_inside_leisure_centre(gdf):
    # Dedupe swimming pools and buildings inside leisure centres.
    # Find pools:
    if "leisure" not in gdf:
        # No leisure centre.
        return gdf
    mask = gdf["leisure"] == "swimming_pool"
    if "building" in gdf:
        mask = mask | (gdf["building"] == "yes")
    pools_or_buildings = gdf[mask]
    sports_centres = gdf[gdf["leisure"] == "sports_centre"]
    to_delete = []
    for i in range(len(sports_centres)):
        sports_centre = sports_centres.iloc[i]
        for j in range(len(pools_or_buildings)):
            p = pools_or_buildings.iloc[j]
            # Check the pool or building isn't the sports_centre itself.
            if sports_centre.equals(p):
                continue
            if p.geometry.within(sports_centre.geometry):
                to_delete.append(pools_or_buildings.index[j])
    if len(to_delete) > 0:
        return gdf.drop(index=to_delete)
    return gdf


def dedupe_beach_coastline_gdf(gdf):
    # Finding a beach often also implies finding a coastline. We only care about
    # the beach, so remove the coastline result.
    if "natural" not in gdf:
        # No beach.
        return gdf
    beach = (gdf["natural"] == "beach").sum() > 0
    if not beach:
        return gdf
    coastline = gdf[gdf["natural"] == "coastline"]
    return gdf.drop(index=coastline.index)


def find_water_near_point(lat, lng, radius):
    accuracy = latlng_accuracy(lat, lng)
    if accuracy > MAX_ACCURACY_METRES:
        return None

    try:
        gdf = osmnx.features.features_from_point(
            (lat, lng),
            water_tags.TAGS,
            dist=radius,
        )
    except osmnx.features.InsufficientResponseError:
        return None

    gdf = dedupe_pools_inside_leisure_centre(gdf)
    gdf = dedupe_beach_coastline_gdf(gdf)

    # Remove clubs except lifesaving
    if "club" in gdf:
        clubs = gdf[gdf["club"].notna() & (gdf["club"] != "surf_life_saving")]
        gdf = gdf.drop(index=clubs.index)

    # Dedupe Port Jackson / other things in and around Sydney Harbour.
    if "name" in gdf and len(gdf) > 1:
        port_jackson = gdf[gdf["name"] == "Port Jackson"]
        gdf = gdf.drop(index=port_jackson.index)

    # Remove covered reservoirs, pipelines, and storage tanks that do not hold water.
    if "man_made" in gdf:
        covered_man_made = gdf[
            (gdf["man_made"] == "reservoir_covered") | (gdf["man_made"] == "pipeline")
        ]
        gdf = gdf.drop(index=covered_man_made.index)

        if "content" in gdf:
            storage_tanks = gdf[
                (gdf["man_made"] == "storage_tank")
                & ~(
                    gdf["content"].isna()
                    | (gdf["content"].str.contains("water", na=False))
                )
            ]
            gdf = gdf.drop(index=storage_tanks.index)
        if "location" in gdf:
            underground_tanks = gdf[
                (gdf["man_made"] == "storage_tank")
                & ~(gdf["location"].isna() | (gdf["location"] == "underground"))
            ]
            gdf = gdf.drop(index=underground_tanks.index)

    calc_distance_to_point(gdf, lat, lng)

    return gdf


def find_water_near_points(in_data, radius):
    gdfs = collections.defaultdict(list)
    for idx in in_data.index:
        patient_id = in_data.at[idx, "patient_id"]
        lat = in_data.at[idx, "Pickup_Latitude"]
        lng = in_data.at[idx, "Pickup_Longitude"]
        if pandas.isna(lat) or pandas.isna(lng):
            gdfs[(patient_id, (lat, lng))] = None
        else:
            print(f"Finding water for {patient_id} near {lat},{lng}")
            gdfs[(patient_id, (lat, lng))] = find_water_near_point(lat, lng, radius)
    return gdfs


def output_row(patient_id, latlng, gdf, out_data):
    out_data["patient_id"].append(patient_id)
    if pandas.isna(latlng[0]) or pandas.isna(latlng[1]):
        out_data["accuracy_metres"].append(None)
    else:
        out_data["accuracy_metres"].append(latlng_accuracy(latlng[0], latlng[1]))
    if gdf is None:
        out_data["water_count"].append(0)
    else:
        gdf = gdf.sort_values(by="distance")
        if len(gdf) > OUTPUT_WIDTH:
            print(f"gdf is longer than OUTPUT_WIDTH: {len(gdf)}")
        out_data["water_count"].append(len(gdf))

    for i in range(OUTPUT_WIDTH):
        if gdf is not None and i < len(gdf):
            row = gdf.iloc[i]
            name = row["name"] if "name" in row else None
            feature_type = row_to_type(row)

            out_data[f"water_name_{i}"].append(name)
            out_data[f"water_type_{i}"].append(feature_type)
            out_data[f"water_distance_{i}"].append(row["distance"])
            out_data[f"water_lifeguard_{i}"].append(lifeguard_from_row(row))
        else:
            out_data[f"water_name_{i}"].append(None)
            out_data[f"water_type_{i}"].append(None)
            out_data[f"water_distance_{i}"].append(None)
            out_data[f"water_lifeguard_{i}"].append(None)


def write_csv(path, gdfs):
    output = collections.defaultdict(list)
    for (patient_id, latlng) in gdfs:
        output_row(patient_id, latlng, gdfs[(patient_id, latlng)], output)
    pandas.DataFrame(output).set_index("patient_id").to_csv(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("--limit_points", type=int, required=False)
    args = parser.parse_args()

    print("Regenerating cached water features")
    # osmnx.settings.use_cache = False

    latlngs = pandas.read_csv(args.filename)
    if args.limit_points and args.limit_points < len(latlngs):
        latlngs = latlngs.head(args.limit_points)

    gdfs = find_water_near_points(latlngs, RADIUS_METRES)
    write_csv("data/cached_water_features.csv", gdfs)


if __name__ == "__main__":
    sys.exit(main())

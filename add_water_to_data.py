# Adds the found water features to a given file, and accumulates some stats
# about what was found.

import argparse
import collections
import sys
import tabulate

import pandas

import cache_water_points 


# The radius to use in different types of locations. In our data,
# "Major Cities of Australia" and "Inner Regional" classifications are treated
# as "Metropolitan" areas. "Outer Regional", "Remote" and "Very Remote" are
# all considered "Regional".
METRO_RADIUS = 100
REGIONAL_RADIUS = 500

# The maximum number of features to retain.
MAX_FEATURES = 50


def find_cache_water_points(in_data, radius, regional_radius):
    features = {}
    for i in range(len(in_data)):
        if i % 1000 == 0:
            print(f"Checked {i} points")
        row = in_data.iloc[i]
        point_id = row["patient_id"]
        remoteness = row["incident_remoteness_code"]
        if pandas.isna(row["Pickup_Latitude"]) or pandas.isna(row["Pickup_Longitude"]):
            features[point_id] = None
            continue
        latlng = (row["Pickup_Latitude"], row["Pickup_Longitude"])
        if remoteness >= 2:  # Corresponds to outer regional, remote, very remote
            features[point_id] = cache_water_points.get_cached_features_near_point(
                point_id, regional_radius, max_features=MAX_FEATURES
            )
        else:
            features[point_id] = cache_water_points.get_cached_features_near_point(
                point_id, radius, max_features=MAX_FEATURES
            )
    return features


def run(in_data, in_filename):
    num_missing = (
        in_data["Pickup_Latitude"].isna() | in_data["Pickup_Longitude"].isna()
    ).sum()

    features = find_cache_water_points(
        in_data, METRO_RADIUS, REGIONAL_RADIUS,
    )
    features_df = pandas.DataFrame(features).transpose().set_index("patient_id")
    water_found_points = features_df[features_df["water_count"] > 0]

    print(f"Found water near {len(water_found_points)} of {len(in_data)}")
    print(f"Lat/lng was missing for {num_missing} rows")

    in_data = in_data.set_index("patient_id", verify_integrity=True)

    out_data = in_data.join(features_df)
    out_data.to_csv(f"outputs/{in_filename}-with-water.csv")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("--limit_points", type=int, required=False)
    args = parser.parse_args()

    print(f"Adding water data to {args.filename}")

    in_data = pandas.read_csv(args.filename)
    if args.limit_points and args.limit_points < len(in_data):
        in_data = in_data.head(args.limit_points)

    in_filename = args.filename.split("/")[-1]
    in_filename = in_filename.split(".")[-2]

    run(
        in_data,
        in_filename,
    )


if __name__ == "__main__":
    sys.exit(main())

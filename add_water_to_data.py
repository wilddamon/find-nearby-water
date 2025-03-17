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


def accumulate_stats(features):
    names_counter = collections.Counter()
    place_types_counter = collections.Counter()
    num_places_found_counter = collections.Counter()

    for latlng in features:
        row = features[latlng]
        if row is None:
            continue
        count = row["water_count"]
        if count is None:
            count = 0
        for i in range(count):
            name = row[f"water_name_{i}"]
            if pandas.notna(name):
                names_counter[name] += 1

            water_type = row[f"water_type_{i}"]
            place_types_counter[water_type] += 1
        num_places_found_counter[count] += 1
    return names_counter, place_types_counter, num_places_found_counter


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
    features_df = pandas.DataFrame(features)

    print("Generating statistics")
    (
        place_names_counter,
        place_types_counter,
        num_places_found_counter,
    ) = accumulate_stats(features)
    features_df = features_df.transpose()
    water_found_points = features_df[features_df["water_count"] > 0]

    outstring = f"Found water near {len(water_found_points)} of {len(in_data)}\n"
    outstring += f"Lat/lng was missing for {num_missing} rows\n"
    outstring += (
        tabulate.tabulate(
            sorted(place_types_counter.items(), key=lambda item: item[1], reverse=True),
            headers=["Place type", "Count"],
        )
        + "\n\n"
    )
    outstring += (
        tabulate.tabulate(
            sorted(place_names_counter.items(), key=lambda item: item[1], reverse=True),
            headers=["Place name", "Count"],
        )
        + "\n\n"
    )
    outstring += (
        tabulate.tabulate(
            sorted(num_places_found_counter.items(), key=lambda item: item[0]),
            headers=["Number of places found", "Count"],
        )
        + "\n\n"
    )
    print(outstring)
    with open(f"outputs/{in_filename}-stats.txt", 'w') as f:
        f.write(outstring)

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

import argparse
import collections
import pandas
import sys

import surf_clubs


water_columns = [
    "water_distance",
    "water_lifeguard",
    "water_name",
    "water_type",
]


def print_stats(l):
    s = pandas.Series(l)
    print(f"Min: {s.min()}")
    print(f"Max: {s.max()}")
    print(f"Mean: {s.mean():.2f}")
    print(f"Median: {s.median()}")
    print(f"IQR: {s.quantile(0.25)} - {s.quantile(0.75)}")


def get_water_fields(data, idx, col_name):
    num_water = data.at[idx, "water_count"]
    if pandas.isna(num_water):
        return []
    result = []
    for i in range(int(num_water)):
        result.append(data.at[idx, f"{col_name}_{i}"])
    return result


def remove_indexes(l, indexes_to_remove):
    indexes_to_remove = sorted(indexes_to_remove)
    for i in range(len(indexes_to_remove)):
        r = indexes_to_remove[i] - i
        l = l[:r] + l[r + 1 :]
    return l


def remove_all_indexes(water_fields, indexes_to_remove):
    for colname in water_columns:
        water_fields[colname] = remove_indexes(water_fields[colname], indexes_to_remove)


def remove_fields(water_fields, colname, to_remove):
    indexes_to_remove = []
    for i in range(len(water_fields[colname])):
        for r in to_remove:
            if water_fields[colname][i] == r:
                indexes_to_remove.append(i)
                break
    remove_all_indexes(water_fields, indexes_to_remove)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("--limit_points", type=int, required=False)
    args = parser.parse_args()

    data = pandas.read_csv(args.filename)
    data.set_index("patient_id", inplace=True)
    if args.limit_points and args.limit_points < len(data):
        data = data.head(args.limit_points)

    # Create the base for a new output
    data_no_water = data.copy()
    cols_to_drop = []
    for colname in water_columns:
        for i in range(50):
            cols_to_drop.append(f"{colname}_{i}")
    data_no_water = data_no_water.drop(columns=cols_to_drop)
    for colname in water_columns:
        for i in range(8):
            data_no_water.insert(len(data_no_water.columns), f"{colname}_{i}", None)

    # pre counts
    pre_max_water_count = 0
    # post counts
    max_water_count = 0
    unnamed_water_series = []
    for idx in data.index:
        water_fields = {}
        for colname in water_columns:
            water_fields[colname] = get_water_fields(data, idx, colname)

        if len(water_fields["water_distance"]) > pre_max_water_count:
            pre_max_water_count = len(water_fields["water_distance"])

        # Disregard piers and bridges (doesn't add anything)
        remove_fields(water_fields, "water_type", ["pier", "bridge"])

        # Convert all lifeguard only to corresponding beach name.
        # Remove any lifeguards with no name.
        to_remove = []
        for i in range(len(water_fields["water_type"])):
            if water_fields["water_type"][i] == "lifeguard":
                if pandas.notna(water_fields["water_name"][i]):
                    water_fields["water_name"][i] = surf_clubs.convert_lifeguard_name(
                        water_fields["water_name"][i]
                    )
                    water_fields["water_type"][i] = "beach"
                else:
                    to_remove.append(i)
        remove_all_indexes(water_fields, to_remove)

        # Correct untyped water points.
        for i in range(len(water_fields["water_type"])):
            water_type = water_fields["water_type"][i]
            name = water_fields["water_name"][i]
            if water_type == "natural:water" and pandas.notna(name):
                if (
                    name == "Berrara Creek"
                    or name == "Kooloonbung Creek"
                    or name == "Mooball Creek"
                    or name == "Tallow Creek"
                    or name == "Muddy Creek"
                ):
                    water_fields["water_type"][i] = "creek"
                elif (
                    name == "Middle Basin"
                    or name == "Seals for the Wild"
                    or name == "Northern Water Feature"
                    or name == "Mill Pond"
                ):
                    water_fields["water_type"][i] = "pond"
                elif name == "Wagonga Inlet":
                    water_fields["water_type"][i] = "harbour"
                elif (
                    name == "Boomerang Bay"
                    or name == "Olympic Pool"
                    or name == "Rapid River"
                ):
                    water_fields["water_type"][i] = "swimming_pool"
                elif name == "Terranora Broadwater" or name == "Green Pool":
                    water_fields["water_type"][i] = "lake"
                elif name == "Sussex Inlet":
                    water_fields["water_type"][i] = "inlet"
                elif name == "Darling Harbour Woodward Water Feature":
                    water_fields["water_type"][i] = "fountain"
                elif name == "Engadine Avenue Wetland":
                    water_fields["water_type"][i] = "wetland"
                elif name == "Port Hunter / Yohaaba":
                    water_fields["water_name"][i] = "Hunter River"
                    water_fields["water_type"][i] = "river"
                elif name == "Toddlers":
                    water_fields["water_type"][i] = "swimming_pool"
                    water_fields["water_name"][i] = "Cootamundra Pool"
                else:
                    unnamed_water_series.append(name)

        # Disregard more distant instances of the same water type
        to_remove = []
        types_found = {}
        for i in range(len(water_fields["water_type"])):
            water_type = water_fields["water_type"][i]
            water_distance = water_fields["water_distance"][i]
            if water_type in types_found and water_distance >= types_found[water_type][0]:
                to_remove.append(i)
            elif water_type in types_found and water_distance < types_found[water_type][0]:
                to_remove.append(types_found[water_type][1])
                types_found[water_type] = (water_distance, i)
            else:
                types_found[water_type] = (water_distance, i)
        remove_all_indexes(water_fields, to_remove)

        # Save to the new dataset.
        data_no_water.at[idx, "water_count"] = len(water_fields["water_distance"])
        for colname in ["water_distance", "water_type", "water_name", "water_lifeguard"]:
            for i in range(len(water_fields["water_type"])):
                data_no_water.at[idx, f"{colname}_{i}"] = water_fields[colname][i]

        water_count = len(water_fields["water_distance"])
        if water_count > max_water_count:
            max_water_count = water_count


    print(f"Total number of points: {len(data)}")
    print(f"Point with most water points nearby (pre-processing): {pre_max_water_count}")
    print(f"Point with most water points nearby (post-processing): {max_water_count}")

    print("unnamed water:")
    print(unnamed_water_series)

    # Output the new dataset to csv.
    data_no_water.to_csv(
        f"{args.filename[:-4]}-processed.csv"
    )


if __name__ == "__main__":
    sys.exit(main())

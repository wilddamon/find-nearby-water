# Applies a heuristic for prioritising which feature is most likely to be
# involved when multiple water features are returned. The ordering is based
# on age-stratified data from the following report covering 20 years of
# fatal drowning in Australia.
# https://www.royallifesaving.com.au/research-and-policy/drowning-research/analysis-of-unintentional-drowning-in-australia-2002-2022

import argparse
import pandas
import sys


water_columns = [
    "water_distance",
    "water_lifeguard",
    "water_name",
    "water_type",
]


def map_ranking(age, water_type):
    if age < 5:
        rankings = [
            # Pool 51%
            "swimming_pool",
            # Bathtub 16%
            # Lake/dam 11%
            "lake",
            "dam",
            "pond",
            "natural:water",
            "reservoir",
            # Other 11%
            "drain",
            "storage_tank",
            "ditch",
            "wetland",
            # Beach 1%
            # Beach should take priority over others where present
            "beach",
            # River/creek 9%
            "river",
            "creek",
            "stream",
            "stream_pool",
            "canal",
            "weir",
            # Ocean/harbour 1%
            "ocean",
            "harbour",
            "bay",
            "lagoon",
            "inlet",
            "swimming_area",
            "breakwater",
            "marina",
            "scuba_diving",
            # Misc odd ones
            "fountain",
            "reflecting_pool",
            "splash_pad",
            "water_park",
            "wastewater",
        ]
    elif age < 15:
        rankings = [
            # Pool 24%
            "swimming_pool",
            # Beach 10%
            # Beach should take priority over others where present
            "beach",
            # Lake/dam 16%
            "lake",
            "dam",
            "pond",
            "natural:water",
            "reservoir",
            # Bath 8%
            # Ocean/harbour 6%
            "ocean",
            "harbour",
            "bay",
            "lagoon",
            "inlet",
            "swimming_area",
            "breakwater",
            "marina",
            "scuba_diving",
            # River/creek 2%
            "river",
            "creek",
            "stream",
            "stream_pool",
            "waterfall",
            "canal",
            "weir",
            # Rocks 3%
            "coastline",
            "cape",
            # Other 31%
            "drain",
            "storage_tank",
            "ditch",
            "wetland",
            # Misc odd ones
            "fountain",
            "reflecting_pool",
            "splash_pad",
            "water_park",
            "wastewater",
        ]
    elif age < 25:
        rankings = [
            # Beach 21%
            # Beach should take priority over others where present
            "beach",
            # River/creek 33%
            "river",
            "creek",
            "stream",
            "stream_pool",
            "waterfall",
            "canal",
            "weir",
            # Ocean/harbour 11%
            "ocean",
            "harbour",
            "bay",
            "lagoon",
            "inlet",
            "swimming_area",
            "breakwater",
            "marina",
            "scuba_diving",
            # Rocks 11%
            "coastline",
            "cape",
            # Lake/dam 9%
            "lake",
            "dam",
            "pond",
            "natural:water",
            "reservoir",
            # Pool 8%
            "swimming_pool",
            # Bath 4%
            # Other 3%
            "drain",
            "storage_tank",
            "ditch",
            "wetland",
            # Misc odd ones
            "fountain",
            "reflecting_pool",
            "splash_pad",
            "water_park",
            "wastewater",
        ]
    elif age < 65:
        rankings = [
            # Beach 21%
            # Beach should take priority over others where present
            "beach",
            # River/creek 28%
            "river",
            "creek",
            "stream",
            "stream_pool",
            "waterfall",
            "canal",
            "weir",
            # Ocean/harbour 20%
            "ocean",
            "harbour",
            "bay",
            "lagoon",
            "inlet",
            "swimming_area",
            "breakwater",
            "marina",
            "scuba_diving",
            # Rocks 9%
            "coastline",
            "cape",
            # Lake/dam 8%
            "lake",
            "dam",
            "pond",
            "natural:water",
            "reservoir",
            # Pool 7%
            "swimming_pool",
            # Bath 5%
            # Other 2%
            "drain",
            "storage_tank",
            "ditch",
            "wetland",
            # Misc odd ones
            "fountain",
            "reflecting_pool",
            "splash_pad",
            "water_park",
            "wastewater",
        ]
    elif age >= 65:
        rankings = [
            # Beach 21%
            # Beach should take priority over others where present
            "beach",
            # River/creek 26%
            "river",
            "creek",
            "stream",
            "stream_pool",
            "waterfall",
            "canal",
            "weir",
            # Ocean/harbour 17%
            "ocean",
            "harbour",
            "bay",
            "lagoon",
            "inlet",
            "swimming_area",
            "breakwater",
            "marina",
            "scuba_diving",
            # Pool 15%
            "swimming_pool",
            # Lake/dam 9%
            "lake",
            "dam",
            "pond",
            "natural:water",
            "reservoir",
            # Bath 6%
            # Rocks 3%
            "coastline",
            "cape",
            # Other 5%
            "drain",
            "storage_tank",
            "ditch",
            "wetland",
            # Misc odd ones
            "fountain",
            "reflecting_pool",
            "splash_pad",
            "water_park",
            "wastewater",
        ]
    else:
        # Generic all-age risks
        rankings = [
            # Beach 1019
            "beach",
            # River/creek 1499
            "river",
            "creek",
            "stream",
            "stream_pool",
            "waterfall",
            "canal",
            "weir",
            # Ocean/harbour 906
            "ocean",
            "harbour",
            "bay",
            "lagoon",
            "inlet",
            "swimming_area",
            "breakwater",
            "marina",
            "scuba_diving",
            # Pool 783
            "swimming_pool",
            # Lake/dam 522
            "lake",
            "dam",
            "pond",
            "natural:water",
            "reservoir",
            # Rocks 378
            "coastline",
            "cape",
            # Bath 359
            # Other 217 + Unknown9
            "drain",
            "storage_tank",
            "ditch",
            "wetland",
            # Misc odd ones
            "fountain",
            "reflecting_pool",
            "splash_pad",
            "water_park",
            "wastewater",
        ]
    ranking = rankings.index(water_type)
    return ranking


def apply_heuristic(idx, age, remoteness, water_types, water_distances):
    if len(water_types) == 1:
        return 0

    if len(water_types) > 1:
        result = 0
        result_rank = map_ranking(age, water_types[0])
        for i in range(1, len(water_types)):
            if (remoteness <= 1 and water_distances[i] - water_distances[0] > 20) or (
                remoteness > 1 and water_distances[i] - water_distances[0] > 50
            ):
                # Stop, unlikely to be that much further away
                break
            rank = map_ranking(age, water_types[i])
            if rank < result_rank:
                result = i
                result_rank = rank
        if water_types[result] != water_types[0]:
            print(f"{idx}; {age}; {remoteness}:\n{water_types}\n{water_distances}")
            print(f"Result: {water_types[result]}, {water_distances[result]}")
        return result


def get_water_fields(data, idx, col_name):
    num_water = data.at[idx, "water_count"]
    if pandas.isna(num_water):
        return []
    result = []
    for i in range(int(num_water)):
        result.append(data.at[idx, f"{col_name}_{i}"])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("--limit_points", type=int, required=False)
    args = parser.parse_args()

    data = pandas.read_csv(args.filename)
    if args.limit_points and args.limit_points < len(data):
        data = data.head(args.limit_points)

    for idx in data.index:
        water_fields = {}
        for colname in water_columns:
            water_fields[colname] = get_water_fields(data, idx, colname)

        result_idx = apply_heuristic(
            data.at[idx, "patient_id"],
            data.at[idx, "age_years"],
            data.at[idx, "incident_remoteness_code"],
            water_fields["water_type"],
            water_fields["water_distance"],
        )
        data.at[idx, "prioritised_feature_index"] = result_idx

    data.to_csv(f"{args.filename[:-4]}-heuristic-applied.csv")


if __name__ == "__main__":
    sys.exit(main())

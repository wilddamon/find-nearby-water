import argparse
import collections
import datetime
import os
import sys
import urllib.parse
import webbrowser

import folium
import geopandas
import osmnx
import pandas

import cache_water_points
import water_tags


def retrieve_value_from_gdf_row(row, tag, result_dict):
    if tag in row and not pandas.isna(row[tag]):
        result_dict[tag] = row[tag]


def non_null_tags_from_gdf(gdf):
    if gdf is None:
        return []

    items_retrieved = []
    for i in range(len(gdf)):
        row = gdf.iloc[i]
        result = {}
        for tag in water_tags.TAGS:
            retrieve_value_from_gdf_row(row, tag, result)
        retrieve_value_from_gdf_row(row, "name", result)
        retrieve_value_from_gdf_row(row, "access", result)
        retrieve_value_from_gdf_row(row, "ownership", result)
        retrieve_value_from_gdf_row(row, "depth", result)
        retrieve_value_from_gdf_row(row, "lifeguard", result)
        # Finds surf_life_saving
        retrieve_value_from_gdf_row(row, "club", result)

        # pool privacy
        if (
            "leisure" in result and result["leisure"] == "swimming_pool"
            or "swimming" in result and result["swimming_pool"] == "swimming"
        ):
            result["inferred_pool_privacy"] = cache_water_points.infer_pool_privacy(
                row)

        items_retrieved.append(result)
    # Remove identical items
    return [dict(t) for t in {tuple(d.items()) for d in items_retrieved}]


def plot_points(in_data, m, color="", tags=None):
    for i in range(len(in_data)):
        latlng = in_data[i]
        if latlng is None:
            continue
        popup = f"{latlng}"
        if tags is not None:
            popup += f"\n{tags[i]}"
        folium.Marker(latlng, icon=folium.Icon(color=color), popup=popup).add_to(m)


def find_water_near_points(in_data, radius, regional_radius):
    gdfs = collections.defaultdict(list)
    for i in range(len(in_data)):
        if i > 0 and i % 10 == 0:
            print(f"Checked {i} points")
        row = in_data.iloc[i]
        point_id = row["patient_id"]
        remoteness = row["incident_remoteness_code"]
        if pandas.isna(row["Pickup_Latitude"]) or pandas.isna(row["Pickup_Longitude"]):
            gdfs[point_id] = None
            continue
        latlng = (row["Pickup_Latitude"], row["Pickup_Longitude"])
        if remoteness >= 2:  # Corresponds to outer regional, remote, very remote
            gdfs[point_id] = cache_water_points.find_water_near_point(
                row["Pickup_Latitude"], row["Pickup_Longitude"], regional_radius
            )
        else:
            gdfs[point_id] = cache_water_points.find_water_near_point(
                row["Pickup_Latitude"], row["Pickup_Longitude"], radius
            )
    return gdfs


def run(in_data, radius, regional_radius, output_dir=None, open_in_browser=False):
    print(f"Finding water near {len(in_data)} points")
    gdfs = find_water_near_points(in_data, radius, regional_radius)
    print(f"Found water. Plotting...")
    num_missing = (
        in_data["Pickup_Latitude"].isna() | in_data["Pickup_Longitude"].isna()
    ).sum()

    water_found_points = []
    water_not_found_points = []
    geodataframe = None
    tags_arr = []
    for point_id in gdfs:
        print(f"Plotting {point_id}")
        gdf = gdfs[point_id]
        row = in_data[in_data["patient_id"] == point_id]
        assert len(row) == 1
        latlng = (row.iloc[0]["Pickup_Latitude"], row.iloc[0]["Pickup_Longitude"])
        if pandas.isna(latlng[0]) or pandas.isna(latlng[1]):
            # Can't plot.
            continue
        if gdf is None:
            water_not_found_points.append(latlng)
            continue

        tags = non_null_tags_from_gdf(gdf)
        water_found_points.append(latlng)

        # Generate visualisation.
        if open_in_browser or output_dir:
            cols = ["geometry", "type", "name", "leisure", "natural", "waterway", "access", "man_made", "swimming_pool", "sport", "tourism"]
            used_cols = []
            for col in cols:
                if col in gdf.columns:
                    used_cols.append(col)
            gdf = gdf[used_cols]
            if geodataframe is None:
                geodataframe = gdf
            else:
                geodataframe = pandas.concat([geodataframe, gdf])
            tags_arr.append(tags)

    if open_in_browser or output_dir:
        m = geodataframe.explore(color="red", tooltip=True)
        plot_points(water_found_points, m, "red", tags_arr)
        plot_points(water_not_found_points, m, "blue")
        if output_dir is None:
            # Showing in the browser happens later if output_dir is not None.
            m.show_in_browser()

    if output_dir:
        dt = datetime.datetime.now()
        filename_notype = os.path.realpath(
            output_dir + f"water-near-points-{dt.strftime('%Y-%m-%dT%H-%M')}"
        )
        map_path = filename_notype + ".html"
        print(f"saving to {map_path}")
        m.save(map_path)
        if open_in_browser:
            url = urllib.parse.quote(map_path)
            print(f"opening {url}")
            webbrowser.open("file://" + url)
    return gdfs


def main():
    parser = argparse.ArgumentParser(
        prog="plot_points_from_csv",
        description="gets water features from a specified radius around points,"
        + "and plots them on a map.",
    )
    parser.add_argument("filename")
    parser.add_argument("radius", type=int)
    parser.add_argument("--regional_radius", type=int)
    parser.add_argument("--limit_points", type=int, required=False)
    parser.add_argument("--output_dir", required=False)
    parser.add_argument(
        "--open", required=False, action=argparse.BooleanOptionalAction, default=True
    )
    args = parser.parse_args()

    print(f"Generating visualisation for points in {args.filename}")

    in_data = pandas.read_csv(args.filename)
    if args.limit_points and args.limit_points < len(in_data):
        in_data = in_data.head(args.limit_points)

    regional_radius = (
        args.radius if args.regional_radius is None else args.regional_radius
    )

    run(
        in_data,
        args.radius,
        regional_radius,
        output_dir=args.output_dir,
        open_in_browser=args.open,
    )


if __name__ == "__main__":
    sys.exit(main())

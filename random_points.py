import collections
import geopandas
import osmnx
import pandas
import random
from shapely.geometry import Point

# Get geometries for each local council area
council_data = pandas.read_csv("data/all_council_areas_with_population.csv")
council_data["osmid"] = council_data["id"].apply(lambda s: "r" + str(s))
geometry = []
for idx in council_data.index:
    print(f"Fetching geometry for {council_data.at[idx, 'updated name']}")
    council_id = council_data.at[idx, "osmid"]
    geometry.append(
        osmnx.geocode_to_gdf(council_id, by_osmid=True).iloc[0].geometry
    )
council_data = geopandas.GeoDataFrame(
    data=council_data, geometry=geometry, crs="epsg:4326"
)


def random_point_in_geom(geom):
    bounds = geom.bounds
    lat_range = bounds[1] - bounds[3]
    lat_centre = (bounds[3] + bounds[1]) / 2
    lng_range = bounds[2] - bounds[0]
    lng_centre = (bounds[0] + bounds[2]) / 2

    for i in range(10):
        lat =    (random.random() - 0.5) * lat_range + lat_centre
        lng =    (random.random() - 0.5) * lng_range + lng_centre
        # Check it is actually within the bound before returning.
        if geom.contains(Point(lng, lat)):
            return (lat, lng)
    print(f"Couldn't generate point in LGA bounds! {bounds} {lat}, {lng}")
    return (lat, lng)


# Generate random points in each LGA
# Rate of 10/100,000 population if coastal, 1 if not
points = []
for idx in council_data.index:
    print(f"Creating random points for {council_data.at[idx, 'updated name']}")
    pop = council_data.at[idx, "population"]
    if council_data.at[idx, "coastal"]:
        num_points = round(pop / 100000 * 10)
    else:
        num_points = round(pop / 100000 * 1)

    # Generate random points
    for i in range(num_points):
        points.append(random_point_in_geom(council_data.at[idx, "geometry"]))

print(f"Generated {len(points)} points")


# Make a DataFrame to output to.
result_df = collections.defaultdict(list)
for i in range(len(points)):
    result_df["patient_id"].append(f"PPN{i}")
    result_df["Pickup_Latitude"].append(points[i][0])
    result_df["Pickup_Longitude"].append(points[i][1])
    # Add a random remoteness classification
    result_df["incident_remoteness_code"].append(round(random.random() * 4))
    # Add a random age
    result_df["age_years"].append(round(random.random() * 100))

# Save result to csv file.
pandas.DataFrame(data=result_df).set_index("patient_id").to_csv("data/random_lat_lngs.csv")


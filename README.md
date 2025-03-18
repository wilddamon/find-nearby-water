# Utilities for searching OpenStreetMap data for nearby water bodies that might be involved in drowning.
These were used in a study of drowning-related ambulance dispatch locations to try and identify whether a 
natural water body was involved in the incident.

For obvious reasons, the actual ambulance data cannot be included in this repository. However, the included
script can be used to generate random data that is the same shape as our dataset so you can try out our scripts.
The scripts should be run in the order described below (except for random\_points.py (optional to regenerate
the random data; and water\_tags.py does not need to be run).

Dependencies:  
* osmnx <https://osmnx.readthedocs.io/>  
* pandas <https://pandas.pydata.org/>
* geopandas <https://geopandas.org/>
* shapely <https://shapely.readthedocs.io/>
* tabulate <https://pypi.org/project/tabulate/> 

# random\_points.py
Generates some random data to use with the scripts. Includes a patient identifcation number, a
latitude/longitude pair that the ambulance was "dispatched" to, a random remoteness classification, and
a random age for the patient. Outputs a .csv file into the "data" directory. An example file is already
checked in to this repository for your convenience.


# cache_water_points.py
Takes a csv file containing patient_id, Pickup_Latitude, and Pickup_Longitude, and fetches up to 100
nearby water features within a 500m radius of the pickup point. It stores these in
"data/cached\_water\_features.csv".

Options:
*filename* (required) the path to a .csv file containing the data.
*--limit_points=n* limits the number of points to the first n. Useful for testing changes.

Usage:
  
    python cache_water_points.py <filename>
  
For example, this takes the example random lat/lngs file checked into this repository, and fetches 
water features for the first 10 points:
  
    python cache_water_points.py data/random_lat_lngs.csv --limit_points=10
  
# add\_water\_to\_data.py
Takes a csv file containing patient_id, Pickup_Latitude, and Pickup_Longitude, and fetches from the
cached data (resulting from cache\_water\_points.py) water features within the METRO_RADIUS and
REGIONAL_RADIUS specified in the file (100m and 500m). It outputs the results to a file in the outputs
directory.

Options:
*filename* (required) the path to a .csv file containing the input data.
*--limit_points=n* limits the number of points to the first n. Useful for testing changes.

Usage:
  
    python add_water_to_data.py <filename>
  
For example, this takes the example random lat/lngs file checked into this repository, and fetches 
relevant water features for the first 10 points, and outputs a file named
"random\_lat\_lngs-with-water.csv":
  
    python add_water_to_data.py data/random_lat_lngs.csv
  
# process\_locations.py
Takes the result from add\_water\_to\_data.py, and removes piers/bridges, replaces surf life saving
clubs with their nearest beach, corrects some untyped water features, and removes more distant
instances of the same water type. Outputs the result to a file in the outputs directory.

Options:
*filename* (required) the path to a .csv file containing the input data.
*--limit_points=n* limits the number of points to the first n. Useful for testing changes.

Usage

    python process_locations.py <filename>

For example, this takes the result from add\_water\_to\_data.py (after running on the random data
included), processes it, then outputs a "outputs/random\_lat\_lngs-with-water-processed.csv.

    python process_locations.py outputs/random_lat_lngs-with-water.csv

# prioritise\_location\_type.py
Takes the result from process\_locations.py, and applies a prioritisation heuristic on any results
that include more than one water feature. The feature that should be prioritised is added in a new
column "prioritised_feature_index" in the output file "{input_file}-heuristic-applied.csv".

Usage:
  
    python prioritise_location_type.py <filename>

# water\_tags.py
Defines which Open Street Maps tags to query. The selection of these tags was
informed by reading the following OSM wiki pages:  
* <https://wiki.openstreetmap.org/wiki/Swimming_and_bathing>  
* <https://wiki.openstreetmap.org/wiki/Map_features#Water>  
* <https://wiki.openstreetmap.org/wiki/Map_features#Waterway>  
* <https://wiki.openstreetmap.org/wiki/Map_features#Water_related>  
* <https://wiki.openstreetmap.org/wiki/Map_features#Leisure>  
* <https://wiki.openstreetmap.org/wiki/Map_features#Sport>  
* <https://wiki.openstreetmap.org/wiki/Key:swimming_pool>  
  
Note that water: True and swimming\_pool: True expand to  
  
```python
water: [  
    'river',  
    'oxbow',  
    'canal',  
    'ditch',  
    'lock',  
    'fish_pass',  
    'lake',  
    'reservoir',  
    'pond',  
    'basin',  
    'lagoon',  
    'stream_pool',  
    'reflecting_pool',  
    'moat',    
    'wastewater',  
]    
swimming_pool: [  
    'inground',  
    'indoor',  
    'outdoor',  
    'swimming',  
    'plunge',  
    'wading',  
    'diving',  
    'rock_pool',  
    'wave_pool',  
]    
```

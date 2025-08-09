from pprint import pp
import re

import pandas as pd
import polyline
import numpy as np
from shapely import Polygon
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points
from scipy.spatial.distance import directed_hausdorff
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import tqdm
from src.app.config import settings
from src.database.adapter import Database
from src.database.models import Activity, NameSuggestion, PromptResponse
from src.tasks.etl.naming_etl import NameSuggestionETL

db = Database(
    settings.postgres_connection_string,
    encryption_key=settings.encryption_key,
)

# https://www.strava.com/activities/14795428452
activity_id = 14795428452

activity = db.get_activity_by_id(activity_id)

athlete_id = activity.athlete_id

date = activity.start_date.strftime("%Y-%m-%d")
two_years_ago = (activity.start_date - pd.DateOffset(years=5)).strftime("%Y-%m-%d")
activities = db.get_activities_by_date_range(
    athlete_id=athlete_id,
    after=two_years_ago,
    before=date,
)
len(activities)

# filter sport type
activities = [a for a in activities if a.sport_type == activity.sport_type]
len(activities)

activities = [a for a in activities if a.map_summary_polyline is not None and a.map_summary_polyline != ""]
len(activities)

activities = [a for a in activities if a.activity_id != activity.activity_id]  # Exclude the main activity

def to_linestring(map_summary_polyline):
    """Convert a polyline string to a Shapely LineString object."""
    if map_summary_polyline is None or map_summary_polyline == "":
        return None
    try:
        decoded = polyline.decode(map_summary_polyline)
        if len(decoded) > 1:  # Need at least 2 points for a line
            return LineString(decoded)
    except Exception as e:
        print(f"Error decoding polyline to LineString: {e}")
    return None

def calculate_route_features(linestring):
    """Calculate various features of a route for similarity comparison."""
    if linestring is None or linestring.is_empty:
        return None
    
    coords = list(linestring.coords)
    if len(coords) < 2:
        return None
    
    # Basic geometric features
    length = linestring.length
    bounds = linestring.bounds  # (minx, miny, maxx, maxy)
    width = bounds[2] - bounds[0]  # longitude span
    height = bounds[3] - bounds[1]  # latitude span
    
    # Start and end points
    start_point = coords[0]
    end_point = coords[-1]
    
    # Calculate if it's a loop (start and end close together)
    start_end_distance = Point(start_point).distance(Point(end_point))
    is_loop = start_end_distance < (length * 0.1)  # Within 10% of total length
    
    # Direction features (bearing from start to end)
    if not is_loop:
        delta_lat = end_point[1] - start_point[1]
        delta_lon = end_point[0] - start_point[0]
        bearing = np.arctan2(delta_lon, delta_lat)
    else:
        bearing = 0  # No meaningful bearing for loops
    
    # Complexity measure (number of significant direction changes)
    complexity = calculate_complexity(coords)
    
    return {
        'length': length,
        'width': width,
        'height': height,
        'start_point': start_point,
        'end_point': end_point,
        'is_loop': is_loop,
        'bearing': bearing,
        'complexity': complexity,
        'bounds': bounds
    }

def calculate_complexity(coords):
    """Calculate route complexity based on direction changes."""
    if len(coords) < 3:
        return 0
    
    angles = []
    for i in range(1, len(coords) - 1):
        p1, p2, p3 = coords[i-1], coords[i], coords[i+1]
        
        # Calculate angle between segments
        v1 = (p2[0] - p1[0], p2[1] - p1[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        
        # Skip if vectors are too small (GPS noise)
        if (v1[0]**2 + v1[1]**2) < 1e-10 or (v2[0]**2 + v2[1]**2) < 1e-10:
            continue
            
        dot_product = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = np.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = np.sqrt(v2[0]**2 + v2[1]**2)
        
        cos_angle = np.clip(dot_product / (mag1 * mag2), -1, 1)
        angle = np.arccos(cos_angle)
        angles.append(angle)
    
    # Return normalized complexity (average angular change)
    return np.mean(angles) if angles else 0

def hausdorff_similarity(line1, line2, max_distance_threshold=0.01):
    """Calculate similarity using Hausdorff distance."""
    if line1 is None or line2 is None:
        return 0
    
    try:
        coords1 = np.array(line1.coords)
        coords2 = np.array(line2.coords)
        
        # Calculate directed Hausdorff distances
        dist1 = directed_hausdorff(coords1, coords2)[0]
        dist2 = directed_hausdorff(coords2, coords1)[0]
        hausdorff_dist = max(dist1, dist2)
        
        # Convert to similarity score (0-1, where 1 is identical)
        similarity = max(0, 1 - (hausdorff_dist / max_distance_threshold))
        return similarity
    except Exception as e:
        print(f"Error calculating Hausdorff distance: {e}")
        return 0

def feature_similarity(features1, features2):
    """Calculate similarity based on route features."""
    if features1 is None or features2 is None:
        return 0
    
    scores = []
    
    # Length similarity (normalized by larger length)
    max_length = max(features1['length'], features2['length'])
    if max_length > 0:
        length_sim = 1 - abs(features1['length'] - features2['length']) / max_length
        scores.append(length_sim * 0.3)  # 30% weight
    
    # Bounds similarity (overlap ratio)
    bounds1, bounds2 = features1['bounds'], features2['bounds']
    overlap_area = max(0, min(bounds1[2], bounds2[2]) - max(bounds1[0], bounds2[0])) * \
                   max(0, min(bounds1[3], bounds2[3]) - max(bounds1[1], bounds2[1]))
    area1 = (bounds1[2] - bounds1[0]) * (bounds1[3] - bounds1[1])
    area2 = (bounds2[2] - bounds2[0]) * (bounds2[3] - bounds2[1])
    union_area = area1 + area2 - overlap_area
    bounds_sim = overlap_area / union_area if union_area > 0 else 0
    scores.append(bounds_sim * 0.2)  # 20% weight
    
    # Loop similarity
    loop_sim = 1.0 if features1['is_loop'] == features2['is_loop'] else 0.0
    scores.append(loop_sim * 0.1)  # 10% weight
    
    # Bearing similarity (for non-loops)
    if not features1['is_loop'] and not features2['is_loop']:
        bearing_diff = abs(features1['bearing'] - features2['bearing'])
        bearing_diff = min(bearing_diff, 2*np.pi - bearing_diff)  # Handle wrap-around
        bearing_sim = 1 - (bearing_diff / np.pi)
        scores.append(bearing_sim * 0.2)  # 20% weight
    else:
        scores.append(0.2)  # Neutral score for loops
    
    # Complexity similarity
    max_complexity = max(features1['complexity'], features2['complexity'])
    if max_complexity > 0:
        complexity_sim = 1 - abs(features1['complexity'] - features2['complexity']) / max_complexity
        scores.append(complexity_sim * 0.2)  # 20% weight
    else:
        scores.append(0.2)  # Both routes are simple
    
    return sum(scores)

def calculate_route_similarity(line1, line2, features1=None, features2=None):
    """
    Calculate comprehensive route similarity using multiple methods.
    Returns a score between 0 and 1, where 1 is identical routes.
    """
    if line1 is None or line2 is None:
        return 0
    
    # Calculate features if not provided
    if features1 is None:
        features1 = calculate_route_features(line1)
    if features2 is None:
        features2 = calculate_route_features(line2)
    
    if features1 is None or features2 is None:
        return 0
    
    # Early filtering: if routes are very different in basic properties, skip expensive calculations
    length_ratio = min(features1['length'], features2['length']) / max(features1['length'], features2['length'])
    if length_ratio < 0.5:  # Routes differ by more than 2x in length
        return 0
    
    # Check if bounding boxes overlap at all
    bounds1, bounds2 = features1['bounds'], features2['bounds']
    if (bounds1[2] < bounds2[0] or bounds2[2] < bounds1[0] or 
        bounds1[3] < bounds2[1] or bounds2[3] < bounds1[1]):
        return 0  # No overlap in bounding boxes
    
    # Calculate different similarity measures
    feature_sim = feature_similarity(features1, features2)
    hausdorff_sim = hausdorff_similarity(line1, line2)
    
    # Combine similarities with weights
    combined_similarity = (feature_sim * 0.6 + hausdorff_sim * 0.4)
    
    return combined_similarity

# Convert polylines to LineStrings for better route comparison
activity_line_data = to_linestring(activity.map_summary_polyline)
line_data = {a.activity_id: to_linestring(a.map_summary_polyline) for a in activities if a.map_summary_polyline is not None and a.map_summary_polyline != ""}

# Check if the main activity has valid geometry
if activity_line_data is None:
    print("Error: Main activity has no valid polyline data")
    exit(1)

# Calculate features for the main activity
main_features = calculate_route_features(activity_line_data)
if main_features is None:
    print("Error: Could not calculate features for main activity")
    exit(1)

# Find similar activities using improved route similarity
similar_activities = []
similarity_threshold = 0.8  # Adjust this threshold as needed (0.0 to 1.0)

for a in tqdm.tqdm(activities, desc="Finding similar activities"):
    if a.activity_id == activity.activity_id:
        continue
    if line_data.get(a.activity_id) is None:
        continue
    
    try:
        current_line = line_data[a.activity_id]
        current_features = calculate_route_features(current_line)
        
        if current_features is None:
            continue
            
        # Calculate comprehensive similarity
        similarity_score = calculate_route_similarity(
            activity_line_data, 
            current_line, 
            main_features, 
            current_features
        )
        
        if similarity_score >= similarity_threshold:
            similar_activities.append((a, similarity_score))
            
    except Exception as e:
        print(f"Error calculating similarity for activity {a.activity_id}: {e}")
        continue

# Sort by similarity score (highest first)
similar_activities.sort(key=lambda x: x[1], reverse=True)


print(f"Found {len(similar_activities)} similar activities for activity {activity.activity_id} ({activity.name})")
print(f"Main activity: {activity.name} ({activity.start_date})")
# Display the top similar activities
for similar_activity, score in similar_activities[:10]:
    print(f"- Activity ID: {similar_activity.activity_id}, Date: {similar_activity.start_date}, Name: {similar_activity.name}, Similarity Score: {score:.4f}")

for similar_activity, score in similar_activities:
    print(f"- {similar_activity.name}")

# plot the main activity and similar activities on a leaflet map
import folium

m = folium.Map(location=[activity.start_lat, activity.start_lng], zoom_start=15,
            #    tiles='CartoDB dark_matter',
               tiles='CartoDB positron',
            #    tiles='Stamen Watercolor'
)

# Add custom JavaScript for line highlighting
highlight_js = """
<script>
var highlightedLine = null;
var originalStyle = null;

function highlightLine(e) {
    var layer = e.target;
    
    // Reset previously highlighted line
    if (highlightedLine && originalStyle) {
        highlightedLine.setStyle(originalStyle);
    }
    
    // Store original style
    originalStyle = {
        color: layer.options.color,
        weight: layer.options.weight,
        opacity: layer.options.opacity
    };
    
    // Highlight current line
    layer.setStyle({
        color: '#FFD700',
        weight: 6,
        opacity: 1.0
    });
    
    highlightedLine = layer;
}

// Add click event listener to all polylines after map loads
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        // Find all polylines and add click events
        if (window[Object.keys(window).find(key => key.startsWith('map_'))]) {
            var map = window[Object.keys(window).find(key => key.startsWith('map_'))];
            map.eachLayer(function(layer) {
                if (layer instanceof L.Polyline) {
                    layer.on('click', highlightLine);
                }
            });
        }
    }, 1000);
});
</script>
"""

def add_activity_to_map(similar_activity, color='blue', activity_id=None):
    """Add an activity's route to the map."""
    line = to_linestring(similar_activity.map_summary_polyline)
    if line is not None:
        # line.coords contains (lat, lon) tuples, folium expects [lat, lon]
        polyline = folium.PolyLine(
            locations=[[lat, lon] for lat, lon in line.coords],
            color=color,
            weight=3,
            opacity=0.7,
            popup=f"Activity: {similar_activity.name}<br>Date: {similar_activity.start_date}<br>ID: {similar_activity.activity_id}"
        )
        polyline.add_to(m)

    start_coords = line.coords[0]
    folium.Marker(
        location=start_coords,
        popup=f"{similar_activity.name} ({similar_activity.start_date})",
        icon=folium.Icon(color=color)
    ).add_to(m)



# Add similar activities (limit to top 10 to avoid overcrowding)
for similar_activity, score in similar_activities:
    add_activity_to_map(similar_activity, color='green')  # Similar activities in green

# Add the main activity first (in red)
add_activity_to_map(activity, color='red')

# Add the custom JavaScript to the map
m.get_root().html.add_child(folium.Element(highlight_js))

m.save("similar_activities_map.html")
print("Map saved to similar_activities_map.html")
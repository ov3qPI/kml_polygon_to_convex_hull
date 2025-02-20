import os
from osgeo import ogr
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

def extract_polygons_from_kml(input_kml):
    """Extracts polygons from a KML file and converts them to Shapely geometries."""
    driver = ogr.GetDriverByName("KML")
    datasource = driver.Open(input_kml, 0)  # Open in read-only mode

    if datasource is None:
        raise ValueError("Failed to open the KML file.")

    layer = datasource.GetLayer()
    polygons = []

    print("\nExtracted Features:")
    for feature in layer:
        geom = feature.GetGeometryRef()
        if geom is not None:
            geom_type = geom.GetGeometryName()
            feature_name = feature.GetField("Name") or "Unnamed Feature"
            print(f" - Name: {feature_name}, Geometry Type: {geom_type}")

            if geom_type == "POLYGON":
                exterior_ring = geom.GetGeometryRef(0)  # Get outer ring
                if exterior_ring is not None:
                    coords = [(exterior_ring.GetPoint(i)[0], exterior_ring.GetPoint(i)[1]) for i in range(exterior_ring.GetPointCount())]
                    shapely_geom = Polygon(coords)
                    polygons.append(shapely_geom)

            elif geom_type == "MULTIPOLYGON":
                multipolygons = []
                for i in range(geom.GetGeometryCount()):
                    sub_geom = geom.GetGeometryRef(i).GetGeometryRef(0)  # Get outer ring
                    if sub_geom is not None:
                        coords = [(sub_geom.GetPoint(j)[0], sub_geom.GetPoint(j)[1]) for j in range(sub_geom.GetPointCount())]
                        multipolygons.append(Polygon(coords))
                shapely_geom = MultiPolygon(multipolygons)
                polygons.append(shapely_geom)

    print(f"\nExtracted {len(polygons)} polygons.")
    return polygons

def validate_and_fix_polygon(polygon):
    """Fix invalid geometries by applying a buffer(0) operation."""
    if not polygon.is_valid:
        print("Invalid geometry detected. Attempting to fix...")
        polygon = polygon.buffer(0)  # Fix self-intersections
    return polygon

def create_convex_hull(input_kml):
    """Generates a convex hull from extracted polygons and saves it as a KML file."""
    polygons = extract_polygons_from_kml(input_kml)

    if not polygons:
        print("\nNo valid polygons found in the KML file.")
        raise ValueError("No polygons found to create a convex hull.")

    # Validate and fix geometries
    valid_polygons = [validate_and_fix_polygon(poly) for poly in polygons if isinstance(poly, Polygon) and not poly.is_empty]

    if not valid_polygons:
        print("No valid polygons found after validation.")
        return

    combined = unary_union(valid_polygons)
    convex_hull = combined.convex_hull

    if convex_hull.is_empty:
        print("Error: Convex hull calculation resulted in an empty geometry.")
        return

    print("\nConvex Hull successfully created.")

    # Create output KML
    driver = ogr.GetDriverByName("KML")
    output_kml = os.path.splitext(input_kml)[0] + "_convex_hull.kml"

    datasource = driver.CreateDataSource(output_kml)
    layer = datasource.CreateLayer("Convex_Hull", geom_type=ogr.wkbPolygon)

    feature_defn = layer.GetLayerDefn()
    feature = ogr.Feature(feature_defn)
    hull_geom = ogr.CreateGeometryFromWkt(convex_hull.wkt)

    if hull_geom is None:
        print("Failed to create convex hull geometry!")
        return

    feature.SetGeometry(hull_geom)
    layer.CreateFeature(feature)

    # Clean up
    feature = None
    datasource = None

    print(f"\nConvex hull KML saved to: {output_kml}")

if __name__ == "__main__":
    input_kml_path = input("Enter the path to the input KML file: ").strip()
    if os.path.exists(input_kml_path):
        create_convex_hull(input_kml_path)
    else:
        print("The specified file does not exist.")
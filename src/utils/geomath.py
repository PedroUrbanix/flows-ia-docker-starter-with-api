
from shapely.geometry import shape, mapping, Point, LineString
from shapely.ops import unary_union, transform
from pyproj import Transformer

_T_W84_to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
_T_3857_to_W84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform

def as_shapely_fc(geojson: dict):
    feats = []
    for f in geojson.get("features", []):
        g = f.get("geometry")
        if not g: continue
        feats.append( (shape(g), f.get("properties", {})) )
    return feats

def to_featurecollection(objs):
    out = {"type":"FeatureCollection","features":[]}
    for geom, props in objs:
        out["features"].append({
            "type":"Feature",
            "properties": props or {},
            "geometry": mapping(geom)
        })
    return out

def to_3857(geom):
    return transform(_T_W84_to_3857, geom)

def to_4326(geom):
    return transform(_T_3857_to_W84, geom)

def union_3857(geoms):
    return unary_union([to_3857(g) for g in geoms])

def line_endpoints_wgs84(line: LineString):
    x0,y0 = line.coords[0]
    x1,y1 = line.coords[-1]
    return Point(x0,y0), Point(x1,y1)

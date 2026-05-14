from pymongo import MongoClient
from pymongo.errors import BulkWriteError
from shapely.geometry import shape
from shapely.validation import make_valid
from dotenv import load_dotenv
import geopandas as gpd
import json, os

load_dotenv()

MS_PATH = f"{os.environ['DATA_DIR']}/Colombia.geojsonl"

db = MongoClient(os.environ["MONGO_URI"])[os.environ.get("MONGO_DB", "upme_solar")]
db.buildings_microsoft.delete_many({})
print("✓ Colección limpia — iniciando carga Microsoft\n")

def area_m2(geom):
    try:
        return round(float(
            gpd.GeoSeries([geom], crs="EPSG:4326")
              .to_crs("EPSG:3857").area.iloc[0]
        ), 2)
    except:
        return 0.0

def insertar_batch(batch):
    """Inserta lote — si hay geometrías que MongoDB rechaza, las salta."""
    try:
        db.buildings_microsoft.insert_many(batch, ordered=False)
        return len(batch), 0
    except BulkWriteError as e:
        insertados = e.details.get("nInserted", 0)
        rechazados = len(e.details.get("writeErrors", []))
        return insertados, rechazados

batch = []
total, reparados, omitidos, rechazados_mongo = 0, 0, 0, 0

with open(MS_PATH, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            shp = shape(json.loads(line))

            if not shp.is_valid:
                shp = make_valid(shp)
                reparados += 1

            if shp is None or shp.is_empty:
                omitidos += 1
                continue

            geom = json.loads(
                gpd.GeoSeries([shp]).to_json()
            )["features"][0]["geometry"]

            batch.append({
                "source":   "microsoft",
                "area_m2":  area_m2(shp),
                "height":   None,
                "cod_mpio": None,
                "geometry": geom
            })

        except Exception:
            omitidos += 1
            continue

        if len(batch) >= 5000:
            ins, rec = insertar_batch(batch)
            total += ins
            rechazados_mongo += rec
            batch = []
            print(f"  … {total:,} insertados | reparados: {reparados:,} | rechazados: {rechazados_mongo:,}", end="\r")

# Último lote
if batch:
    ins, rec = insertar_batch(batch)
    total += ins
    rechazados_mongo += rec

print(f"\n\n✓ Total insertado  : {total:,}")
print(f"  Reparados        : {reparados:,}")
print(f"  Omitidos         : {omitidos:,}")
print(f"  Rechazados MongoDB: {rechazados_mongo:,}")
print(f"  En DB            : {db.buildings_microsoft.count_documents({}):,}")

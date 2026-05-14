"""
UPME Solar Project — MongoDB Schema Setup v3
Correcciones:
  - MGN columnas en minúsculas (mpio_cdpmp)
  - Google GDB con driver explícito
  - Microsoft GeoJSONL parser robusto
"""

from pymongo import MongoClient, GEOSPHERE, ASCENDING, UpdateOne
from pymongo.errors import CollectionInvalid
from dotenv import load_dotenv
import geopandas as gpd
import pandas as pd
import json, os

load_dotenv()

# ─────────────────────────────────────────────
# RUTAS — configuradas via .env
# ─────────────────────────────────────────────
BASE       = os.environ["DATA_DIR"]
MGN_PATH   = f"{BASE}/MGN_ADM_MPIO_GRAFICO.geojson"
PDET_EXCEL = f"{BASE}/MunicipiosPDET.xlsx"
MS_PATH    = f"{BASE}/Colombia.geojsonl"
GOOGLE_GDB = f"{BASE}/col_buildings.gdb" if os.path.exists(f"{BASE}/col_buildings.gdb") \
             else f"{BASE}/col_buildings"

# ─────────────────────────────────────────────
# CONEXIÓN — configurada via .env
# ─────────────────────────────────────────────
client = MongoClient(os.environ["MONGO_URI"])
db     = client[os.environ.get("MONGO_DB", "upme_solar")]
try:
    client.admin.command("ping")
    print("✓ Conectado a MongoDB\n")
except Exception as e:
    print(f"✗ Error: {e}"); exit(1)

# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────
def crear_coleccion(nombre, validator):
    try:
        db.create_collection(nombre, validator=validator)
        print(f"  ✓ Creada: {nombre}")
    except CollectionInvalid:
        db.command("collMod", nombre, validator=validator,
                   validationLevel="moderate", validationAction="warn")
        print(f"  ~ Ya existía, actualizada: {nombre}")

def geom_a_geojson(geom):
    return json.loads(gpd.GeoSeries([geom]).to_json())["features"][0]["geometry"]

def area_m2(geom):
    try:
        return round(float(
            gpd.GeoSeries([geom], crs="EPSG:4326").to_crs("EPSG:3857").area.iloc[0]
        ), 2)
    except:
        return 0.0

# ─────────────────────────────────────────────
# 1. COLECCIONES E ÍNDICES
# ─────────────────────────────────────────────
print("── Colecciones ──")
crear_coleccion("municipalities_pdet", {"$jsonSchema": {
    "bsonType": "object", "required": ["cod_mpio","nombre","geometry"],
    "properties": {
        "cod_mpio":       {"bsonType": "string"},
        "nombre":         {"bsonType": "string"},
        "departamento":   {"bsonType": "string"},
        "subregion_pdet": {"bsonType": "string"},
        "pdet":           {"bsonType": "bool"},
        "area_km2":       {"bsonType": ["double","null"]},
        "geometry":       {"bsonType": "object"}
    }
}})
crear_coleccion("buildings_google", {"$jsonSchema": {
    "bsonType": "object", "required": ["source","area_m2","geometry"],
    "properties": {
        "source":     {"bsonType": "string", "enum": ["google"]},
        "area_m2":    {"bsonType": ["double","int"], "minimum": 0},
        "confidence": {"bsonType": ["double","null"]},
        "cod_mpio":   {"bsonType": ["string","null"]},
        "geometry":   {"bsonType": "object"}
    }
}})
crear_coleccion("buildings_microsoft", {"$jsonSchema": {
    "bsonType": "object", "required": ["source","area_m2","geometry"],
    "properties": {
        "source":   {"bsonType": "string", "enum": ["microsoft"]},
        "area_m2":  {"bsonType": ["double","int"], "minimum": 0},
        "height":   {"bsonType": ["double","null"]},
        "cod_mpio": {"bsonType": ["string","null"]},
        "geometry": {"bsonType": "object"}
    }
}})

print("\n── Índices ──")
db.municipalities_pdet.create_index([("geometry", GEOSPHERE)], name="geometry_2dsphere")
db.municipalities_pdet.create_index([("cod_mpio", ASCENDING)], unique=True, name="cod_mpio_unique")
db.buildings_google.create_index([("geometry", GEOSPHERE)], name="geometry_2dsphere")
db.buildings_google.create_index([("cod_mpio", ASCENDING),("area_m2", ASCENDING)], name="mpio_area")
db.buildings_microsoft.create_index([("geometry", GEOSPHERE)], name="geometry_2dsphere")
db.buildings_microsoft.create_index([("cod_mpio", ASCENDING),("area_m2", ASCENDING)], name="mpio_area")
print("  ✓ Índices creados")

# ─────────────────────────────────────────────
# 2. MUNICIPIOS PDET
# ─────────────────────────────────────────────
print("\n── Cargando municipalities_pdet ──")

df_pdet = pd.read_excel(PDET_EXCEL)
df_pdet.columns = ["subregion","cod_dpto","departamento","cod_mpio","nombre"]
df_pdet["cod_mpio"] = df_pdet["cod_mpio"].astype(str).str.zfill(5)
codigos_pdet = set(df_pdet["cod_mpio"])
print(f"  ℹ PDET en Excel: {len(codigos_pdet)}")

gdf = gpd.read_file(MGN_PATH)
print(f"  ℹ Registros MGN: {len(gdf)}")
if gdf.crs and gdf.crs.to_epsg() != 4326:
    gdf = gdf.to_crs("EPSG:4326")

# Buscar columna código — acepta mayúsculas y minúsculas
cols_lower = {c.lower(): c for c in gdf.columns}
cod_col = None
for candidato in ["mpio_cdpmp","cod_mpio","codigo","dptompio"]:
    if candidato in cols_lower:
        cod_col = cols_lower[candidato]
        break

if cod_col is None:
    print(f"  ✗ Columna código no encontrada. Columnas: {list(gdf.columns)}")
else:
    print(f"  ✓ Columna código: '{cod_col}'")
    gdf[cod_col] = gdf[cod_col].astype(str).str.zfill(5)
    gdf_pdet = gdf[gdf[cod_col].isin(codigos_pdet)].copy()
    print(f"  ℹ Municipios PDET encontrados: {len(gdf_pdet)}")

    # Mapear otras columnas (minúsculas o mayúsculas)
    nom_col  = cols_lower.get("mpio_cnmbr", cols_lower.get("nombre", None))
    dpto_col = cols_lower.get("dpto_cnmbr", cols_lower.get("departamen", None))

    docs = []
    for _, row in gdf_pdet.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty: continue
        cod  = str(row[cod_col]).zfill(5)
        info = df_pdet[df_pdet["cod_mpio"] == cod]
        docs.append({
            "cod_mpio":       cod,
            "nombre":         str(row[nom_col])  if nom_col  else "",
            "departamento":   str(row[dpto_col]) if dpto_col else "",
            "subregion_pdet": str(info["subregion"].values[0]) if len(info) > 0 else "",
            "pdet":           True,
            "area_km2":       area_m2(geom) / 1e6 if geom else None,
            "geometry":       geom_a_geojson(geom)
        })

    if docs:
        ops = [UpdateOne({"cod_mpio": d["cod_mpio"]}, {"$set": d}, upsert=True) for d in docs]
        db.municipalities_pdet.bulk_write(ops)
        print(f"  ✓ Municipios en DB: {db.municipalities_pdet.count_documents({})}")

# ─────────────────────────────────────────────
# 3. EDIFICIOS GOOGLE (GDB)
# ─────────────────────────────────────────────
print("\n── Cargando buildings_google (GDB) ──")
print(f"  ℹ Ruta: {GOOGLE_GDB}")

try:
    # Intentar con driver OpenFileGDB (viene con pyogrio/GDAL)
    import pyogrio
    capas = pyogrio.list_layers(GOOGLE_GDB)
    print(f"  ℹ Capas encontradas: {capas}")
    capa = capas[0][0]
    gdf_g = gpd.read_file(GOOGLE_GDB, layer=capa, engine="pyogrio")
    if gdf_g.crs and gdf_g.crs.to_epsg() != 4326:
        gdf_g = gdf_g.to_crs("EPSG:4326")
    print(f"  ℹ Columnas: {list(gdf_g.columns)}")
    print(f"  ℹ Edificios: {len(gdf_g):,}")

    area_col = next((c for c in gdf_g.columns if "area" in c.lower()), None)
    conf_col = next((c for c in gdf_g.columns if "conf" in c.lower()), None)

    batch, total = [], 0
    for _, row in gdf_g.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty: continue
        a = float(row[area_col]) if area_col else area_m2(geom)
        batch.append({
            "source":     "google",
            "area_m2":    round(a, 2),
            "confidence": float(row[conf_col]) if conf_col else None,
            "cod_mpio":   None,
            "geometry":   geom_a_geojson(geom)
        })
        if len(batch) >= 5000:
            db.buildings_google.insert_many(batch, ordered=False)
            total += len(batch); batch = []
            print(f"  … {total:,} insertados", end="\r")
    if batch:
        db.buildings_google.insert_many(batch, ordered=False)
        total += len(batch)
    print(f"  ✓ Total Google: {total:,} edificios")

except Exception as e:
    print(f"  ✗ Error GDB: {e}")
    print("  → Intenta renombrar la carpeta:")
    print(f"    mv \"{GOOGLE_GDB.replace('.gdb','')}\" \"{GOOGLE_GDB}\"")


# ─────────────────────────────────────────────
# 4. VERIFICACIÓN
# ─────────────────────────────────────────────
print("\n── Verificación final ──")
for col in ["municipalities_pdet","buildings_google"]:
    n   = db[col].count_documents({})
    idx = [i["name"] for i in db[col].list_indexes()]
    print(f"\n  {col}")
    print(f"    Documentos : {n:,}")
    print(f"    Índices    : {idx}")

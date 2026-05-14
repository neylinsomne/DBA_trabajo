# DBA — UPME Solar Energy Feasibility Project

Análisis de viabilidad de energía solar en municipios PDET de Colombia usando MongoDB y datasets abiertos de edificaciones.

## Estructura

| Carpeta | Contenido |
|---|---|
| `entrega_1/` | Diseño de esquema NoSQL, modelo de datos, scripts ETL |
| `entrega_2/` | Integración de fronteras municipales PDET (MGN-DANE) |
| `entrega_3/` | Carga y análisis comparativo Google + Microsoft |

## Setup

### 1. Dependencias

```bash
pip install pymongo geopandas pandas openpyxl shapely pyogrio python-dotenv folium matplotlib
```

### 2. MongoDB

Requiere MongoDB Community 8.x corriendo localmente o accesible vía URI.

```bash
# macOS
brew services start mongodb-community

# verificar
mongosh --eval "db.adminCommand('ping')"
```

### 3. Variables de entorno

Copia `.env.example` a `.env` y ajusta los valores:

```bash
cp .env.example .env
```

| Variable | Descripción |
|---|---|
| `MONGO_URI` | URI de conexión (ej: `mongodb://localhost:27017/`) |
| `MONGO_DB` | Nombre de la base de datos (default: `upme_solar`) |
| `DATA_DIR` | Carpeta local donde están los datasets descargados |

> El `.env` está en `.gitignore` — nunca lo subas al repo.

## Descarga de Datasets

Descarga los siguientes archivos en la carpeta apuntada por `DATA_DIR`:

### 1. MGN 2025 — DANE (límites municipales)

- **URL:** https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/datos-geoestadisticos/?cod=111
- **Versión:** `MGN2025-Colombia` — todos los niveles geográficos
- **Archivo necesario:** `MGN_ADM_MPIO_GRAFICO.geojson`

### 2. Lista oficial de municipios PDET

- **Archivo:** `MunicipiosPDET.xlsx` (provisto por UPME)
- 170 municipios designados PDET

### 3. Google Open Buildings v3

- **URL:** https://sites.research.google/gr/open-buildings/
- **Formato:** File Geodatabase (`.gdb`)
- **Cobertura:** 16,496,745 edificios en Colombia
- **Licencia:** CC BY-4.0 + ODbL
- **Carpeta esperada:** `col_buildings.gdb/`

### 4. Microsoft Building Footprints — Colombia

- **URL:** https://planetarycomputer.microsoft.com/dataset/ms-buildings
- **Formato:** GeoJSONL (`Colombia.geojsonl`)
- **Cobertura:** 6,083,732 edificios insertados
- **Licencia:** ODbL

### Estructura final esperada de `DATA_DIR`

```
$DATA_DIR/
├── MGN_ADM_MPIO_GRAFICO.geojson
├── MunicipiosPDET.xlsx
├── Colombia.geojsonl
└── col_buildings.gdb/
```

## Ejecución

```bash
cd entrega_1/
python mongodb_schema_setup.py    # crea colecciones, índices, carga municipios + Google
python load_microsoft.py          # carga Microsoft Building Footprints
```

Luego abrir los notebooks en `entrega_2/` y `entrega_3/` para verificación y análisis.

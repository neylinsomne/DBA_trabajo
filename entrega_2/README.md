# Entrega 2 — README: PDET Municipality Boundaries Dataset Integration

## Fuentes de Datos

| Dataset | Versión | URL | Formato | Tamaño |
| MGN Colombia | MGN2025 | https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/datos-geoestadisticos/?cod=111 | GeoJSON | 273 MB |
| Lista PDET oficial | — | Documento oficial UPME | XLSX | 24 KB |

## Pasos para Reproducir

```bash
# 1. Instalar dependencias
pip install pymongo geopandas pandas openpyxl shapely folium matplotlib

# 2. Asegurarse que MongoDB esté corriendo
brew services start mongodb-community
mongosh --eval "db.adminCommand('ping')"

# 3. Correr el script de carga (Entrega 1)
cd entrega_1/
python mongodb_schema_setup.py

# 4. Abrir el notebook de verificación
cd ../entrega_2/
jupyter notebook pdet_integration.ipynb
# O en VS Code: abrir el archivo directamente
```

## Decisiones Tomadas

- **Formato GeoJSON vs Shapefile:** Se usó `MGN_ADM_MPIO_GRAFICO.geojson` en lugar del shapefile porque GeoPandas lo lee directamente sin necesidad de archivos auxiliares (.shx, .dbf).
- **Sistema de coordenadas:** El MGN viene en EPSG:4326 (WGS84) — compatible directo con MongoDB GeoJSON.
- **Filtrado PDET:** Se cruzó el shapefile MGN por `mpio_cdpmp` (código DANE de 5 dígitos) con la lista oficial de 170 municipios del Excel.
- **Cálculo de área:** Se reproyectó a EPSG:3857 para obtener área en metros cuadrados, luego convertido a km².

## Resultados

| Métrica | Valor |
| Municipios PDET cargados | 170 / 170 |
| Departamentos representados | 19 |
| Subregiones PDET | 16 |
| Geometrías inválidas | 0 |
| Índice 2dsphere | Activo |
| Query $geoIntersects | Funcional |

## Archivos Generados

| Archivo | Descripción |
|---|---|
| `pdet_integration.ipynb` | Notebook principal con verificación completa |
| `mapa_pdet.png` | Mapa estático coloreado por subregión PDET |
| `mapa_pdet_interactivo.html` | Mapa interactivo con tooltips por municipio |

## Municipios sin cobertura

| Dataset | Municipios sin datos | % del total |
| Google Open Buildings | 5 | 2.9% |
| Microsoft Building Footprints | 1 | 0.6% |

### Sin Google Open Buildings (5)

| Municipio | Departamento | Área (km²) |
| Murindó | Antioquia | 1,290 |
| Vigía del Fuerte | Antioquia | 1,691 |
| Bojayá | Chocó | 3,691 |
| Medio San Juan | Chocó | 671 |
| Nóvita | Chocó | 957 |

### Sin Microsoft Building Footprints (1)

| Municipio | Departamento | Área (km²) |
| Miraflores | Guaviare | 12,885 |

### Análisis

Los 5 municipios sin cobertura Google tienen un área promedio de 1,660 km²,
menor al promedio de 2,340 km² de los municipios con cobertura. Son
territorios predominantemente selváticos en Chocó y Antioquia, con baja
densidad poblacional y acceso limitado a imágenes satelitales de alta
resolución.

Miraflores (Guaviare, 12,885 km²) es el único sin cobertura Microsoft —
su extensión territorial extrema y ubicación en la Amazonía colombiana
explican la ausencia de datos en ambas fuentes para las zonas más remotas.

**Impacto en el análisis:** el 2.9% de municipios PDET sin Google se
analizará con Microsoft como fuente alternativa en la Entrega 4.
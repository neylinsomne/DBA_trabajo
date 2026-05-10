# Data Model — UPME Solar Energy Feasibility Analysis

## 1. Base de Datos

**Nombre:** `upme_solar`  
**Motor:** MongoDB 8.2.7  
**Conexión:** `mongodb://localhost:27017/`

---

## 2. Colecciones

### 2.1 `municipalities_pdet`

Almacena los límites administrativos de los 170 municipios designados como territorios PDET, extraídos del MGN 2025 de DANE y filtrados con la lista oficial PDET.

**Cardinalidad:** 170 documentos, uno por municipio

| Campo | Tipo BSON | Requerido | Descripción |
| `_id` | ObjectId | Auto | Identificador interno MongoDB |
| `cod_mpio` | String | Si | Código DANE del municipio (5 dígitos, ej: "05045") |
| `nombre` | String | Si | Nombre oficial del municipio |
| `departamento` | String | Si | Nombre del departamento |
| `subregion_pdet` | String | Si | Subregión PDET (ej: "URABÁ ANTIOQUEÑO") |
| `pdet` | Boolean | Si | Siempre `true` en esta colección |
| `area_km2` | Double | No | Área del municipio en km² (calculada en EPSG:3857) |
| `geometry` | Object | Si | GeoJSON Polygon/MultiPolygon del límite municipal |

**Ejemplo de documento:**
```json
{
  "cod_mpio": "05045",
  "nombre": "APARTADÓ",
  "departamento": "ANTIOQUIA",
  "subregion_pdet": "URABÁ ANTIOQUEÑO",
  "pdet": true,
  "area_km2": 547.96,
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-76.62, 7.88], [-76.59, 7.85], "..."]]
  }
}
```

---

### 2.2 `buildings_google`

Almacena las huellas de edificios detectadas por Google Open Buildings para Colombia, en su versión 3 (File Geodatabase).

**Cardinalidad:** 16,496,745 documentos

| Campo | Tipo BSON | Requerido | Descripción |
| `_id` | ObjectId | Auto | Identificador interno MongoDB |
| `source` | String | Si | Siempre `"google"` |
| `area_m2` | Double | Si | Área de la huella en metros cuadrados |
| `confidence` | Double | No | Score de confianza de detección (0.0 – 1.0) |
| `cod_mpio` | String | No | FK lógica hacia municipalities_pdet (asignada en Entrega 4) |
| `geometry` | Object | Si | GeoJSON Polygon de la huella del edificio |

**Ejemplo de documento:**
```json
{
  "source": "google",
  "area_m2": 95.31,
  "confidence": 0.793,
  "cod_mpio": null,
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-76.623, 7.882], [-76.621, 7.881], "..."]]
  }
}
```

---

### 2.3 `buildings_microsoft`

Almacena las huellas de edificios del dataset Microsoft Building Footprints para Colombia, distribuido en formato GeoJSONL.

**Cardinalidad:** 6,083,732 documentos, 89 omitidos por geometría inválida irreparable

| Campo | Tipo BSON | Requerido | Descripción |
| `_id` | ObjectId | Auto | Identificador interno MongoDB |
| `source` | String | Si | Siempre `"microsoft"` |
| `area_m2` | Double | Si | Área de la huella en metros cuadrados |
| `height` | Double | No | Altura del edificio (null — no disponible para Colombia) |
| `cod_mpio` | String | No | FK lógica hacia municipalities_pdet (asignada en Entrega 4) |
| `geometry` | Object | Si | GeoJSON Polygon de la huella del edificio |

**Ejemplo de documento:**
```json
{
  "source": "microsoft",
  "area_m2": 560.87,
  "height": null,
  "cod_mpio": null,
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-74.625, 4.203], [-74.624, 4.203], "..."]]
  }
}
```

---

## 3. Relaciones entre Colecciones

```
municipalities_pdet          buildings_google
───────────────────          ────────────────
cod_mpio (PK única)  ◄──── cod_mpio (FK lógica, null hasta E4)

municipalities_pdet          buildings_microsoft  
───────────────────          ───────────────────
cod_mpio (PK única)  ◄──── cod_mpio (FK lógica, null hasta E4)
```

**Nota:** En MongoDB no existen foreign keys con enforcement automático. La integridad referencial se garantiza mediante el proceso ETL del spatial join (`$geoIntersects`) ejecutado en la Entrega 4.

---

## 4. Decisiones de Diseño

**¿Por qué dos colecciones separadas para edificios?**  
Mantener `buildings_google` y `buildings_microsoft` separadas permite comparar directamente los resultados de cada fuente por municipio, identificar discrepancias y evaluar cuál dataset es más apropiado para regiones específicas de Colombia.

**¿Por qué `cod_mpio` como string y no como integer?**  
Los códigos DANE tienen ceros a la izquierda significativos (ej: "05045"). Almacenarlos como entero perdería ese formato y dificultaría el join con otras fuentes que los manejan como string.

**¿Por qué calcular `area_m2` en el ETL y no en MongoDB?**  
MongoDB no tiene funciones nativas para calcular áreas de polígonos. La conversión a EPSG:3857 (metros) se hace en Python con GeoPandas durante la inserción, garantizando que el campo esté siempre disponible para agregaciones con `$sum`.

# Schema Design & Appropriateness — UPME Solar Energy Feasibility Analysis

## 1. Estrategia de Validación — JSON Schema

MongoDB aplica validadores JSON Schema en cada inserción. Se configuró `validationLevel: moderate` y `validationAction: warn` para no bloquear inserciones durante desarrollo, pero registrar documentos que no cumplan el esquema.

### Validador — `municipalities_pdet`
```javascript
db.createCollection("municipalities_pdet", {
  validator: {
    "$jsonSchema": {
      "bsonType": "object",
      "required": ["cod_mpio", "nombre", "geometry"],
      "properties": {
        "cod_mpio":       { "bsonType": "string" },
        "nombre":         { "bsonType": "string" },
        "departamento":   { "bsonType": "string" },
        "subregion_pdet": { "bsonType": "string" },
        "pdet":           { "bsonType": "bool" },
        "area_km2":       { "bsonType": ["double", "null"] },
        "geometry":       { "bsonType": "object" }
      }
    }
  }
})
```

### Validador — `buildings_google`
```javascript
"$jsonSchema": {
  "required": ["source", "area_m2", "geometry"],
  "properties": {
    "source":     { "bsonType": "string", "enum": ["google"] },
    "area_m2":    { "bsonType": ["double", "int"], "minimum": 0 },
    "confidence": { "bsonType": ["double", "null"] },
    "cod_mpio":   { "bsonType": ["string", "null"] },
    "geometry":   { "bsonType": "object" }
  }
}
```

### Validador — `buildings_microsoft`
```javascript
"$jsonSchema": {
  "required": ["source", "area_m2", "geometry"],
  "properties": {
    "source":   { "bsonType": "string", "enum": ["microsoft"] },
    "area_m2":  { "bsonType": ["double", "int"], "minimum": 0 },
    "height":   { "bsonType": ["double", "null"] },
    "cod_mpio": { "bsonType": ["string", "null"] },
    "geometry": { "bsonType": "object" }
  }
}
```

---

## 2. Índices

### `municipalities_pdet`

| Índice | Tipo | Campo | Propósito |
| `geometry_2dsphere` | 2dsphere | `geometry` | Activa operadores espaciales ($geoIntersects, $geoWithin) |
| `cod_mpio_unique` | Ascending + Unique | `cod_mpio` | Evita duplicados; acelera búsqueda por código |

```python
db.municipalities_pdet.create_index([("geometry", GEOSPHERE)], name="geometry_2dsphere")
db.municipalities_pdet.create_index([("cod_mpio", ASCENDING)], unique=True, name="cod_mpio_unique")
```

### `buildings_google` y `buildings_microsoft`

| Índice | Tipo | Campos | Propósito |
| `geometry_2dsphere` | 2dsphere | `geometry` | Spatial join con municipios en Entrega 4 |
| `mpio_area` | Ascending compuesto | `cod_mpio`, `area_m2` | Acelera agregaciones de área por municipio |

```python
db.buildings_google.create_index([("geometry", GEOSPHERE)], name="geometry_2dsphere")
db.buildings_google.create_index([("cod_mpio", ASCENDING), ("area_m2", ASCENDING)], name="mpio_area")
```

---

## 3. Apropiabilidad del Esquema NoSQL

### ¿Por qué documento-orientado y no relacional?
### Ventajas del esquema implementado para este proyecto

**Flexibilidad de campos:** `buildings_google` tiene `confidence` y `buildings_microsoft` tiene `height` — en SQL requeriría columnas nullable o tablas separadas con JOIN. En MongoDB cada documento porta solo los campos relevantes.

**GeoJSON nativo:** Los datasets de Google y Microsoft ya vienen en GeoJSON. MongoDB los almacena sin conversión de formato, eliminando una capa de transformación y garantizando fidelidad de coordenadas.

**Escalabilidad horizontal:** Con 22 millones de documentos en la instancia local, el esquema está preparado para escalar a nivel nacional o multi-país simplemente añadiendo shards, sin cambiar la estructura de los documentos.

**Operaciones de agregación:** La query central del proyecto (sumar `area_m2` por `cod_mpio`) se expresa naturalmente en MongoDB:
```javascript
db.buildings_google.aggregate([
  { "$geoMatch": { "geometry": { "$geoIntersects": { "$geometry": mpio_geom } } } },
  { "$group": { "_id": "$cod_mpio", "total_area": { "$sum": "$area_m2" }, "count": { "$sum": 1 } } }
])
```

---

## 4. Integridad de Datos — Decisiones

| Situación | Decisión | Justificación |
| Geometrías inválidas (Shapely) | `make_valid()` antes de insertar | Preserva el edificio con geometría reparada |
| Geometrías rechazadas por MongoDB (89) | Omitir | Irrecuperables para geometría esférica; menos del 0.001% del total |
| `cod_mpio` null en edificios | Intencional — se asigna en Entrega 4 | El spatial join requiere que municipios estén cargados primero |
| `height` null en Microsoft | Aceptado | Dato no disponible para Colombia en este dataset |
| Upsert en municipios | `bulk_write` con `upsert=True` | Permite re-ejecutar el script sin duplicar datos |

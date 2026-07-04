# Fixtures de prueba (datos reales)

Fuente integración: local pos-core-etl silver CSVs (Kavia + QIN Dec 2025)

```json
{
  "start": "2025-12-01",
  "end": "2025-12-07",
  "branches": [
    "Kavia",
    "QIN"
  ],
  "source": "local pos-core-etl silver CSVs (Kavia + QIN Dec 2025)",
  "raw_file": "detail_kavia_qin_2025-12-01_2025-12-07.csv",
  "row_count": 16536,
  "scenarios": {
    "cafe_refill_regular.csv": {
      "order_id": 3,
      "source_file": "detail_Panem-Credi-Club_2025-12-01_2025-12-07.csv"
    },
    "cafe_refill_descafeinado.csv": {
      "order_id": 6,
      "source_file": "detail_Panem-Hospital-Zambrano-N_2025-12-01_2025-12-07.csv"
    },
    "chilaquiles_salsa_verde_with_egg.csv": {
      "order_id": 4,
      "source_file": "detail_Panem-Credi-Club_2025-12-01_2025-12-07.csv"
    },
    "concha_vainilla_passthrough.csv": {
      "order_id": 6,
      "source_file": "detail_Panem-Credi-Club_2025-12-01_2025-12-07.csv"
    },
    "concha_uber_chocolate.csv": {
      "order_id": 27,
      "source_file": "detail_Panem-Punto-Valle_2025-12-01_2025-12-07.csv"
    },
    "concha_rappi_vainilla.csv": {
      "order_id": 28,
      "source_file": "detail_Panem-Punto-Valle_2025-12-01_2025-12-07.csv"
    },
    "chilaquiles_uber_salsa_verde.csv": {
      "order_id": 7,
      "source_file": "detail_Panem-Credi-Club_2025-12-01_2025-12-07.csv"
    },
    "caja_10_conchas_uber.csv": {
      "order_id": 1,
      "source_file": "detail_Panem-Credi-Club_2025-12-01_2025-12-07.csv"
    },
    "non_adjacent_modifier.csv": {
      "order_id": 7,
      "source_file": "detail_Panem-Plaza-Nativa_2025-12-01_2025-12-07.csv"
    },
    "delivery_passthrough_latte.csv": {
      "order_id": 15,
      "source_file": "detail_Panem-Credi-Club_2025-12-01_2025-12-07.csv"
    }
  }
}
```

# Método de recomendaciones de venta cruzada

Este documento es la referencia canónica para el análisis **Ventas cruzadas**.
El objetivo es producir sugerencias operativas como “cuando compren café, ofrece
concha” sin confundir popularidad con afinidad ni presentar una asociación como
causalidad.

## Unidad de análisis

Cada ticket es una canasta binaria de productos comprados:

- Se usa `pdv_txn_id` cuando está disponible.
- En caso contrario, el ticket se identifica por
  `(sucursal, operating_date, order_id)`, porque `order_id` se reutiliza.
- Cada producto cuenta una vez por ticket, aunque tenga varias líneas o cantidad
  mayor a uno.
- Se excluyen modificadores, cantidades no positivas y líneas con
  `subtotal_item <= 0` (cortesías, anulaciones o líneas sin compra).
- Los nombres se analizan después del enriquecimiento y de la unificación
  opcional de canales.

## Reglas y métricas

Para una regla direccional `X → Y`:

- `N`: total de canastas.
- `n_X`: canastas con `X`.
- `n_Y`: canastas con `Y`.
- `n_XY`: canastas con ambos.

Las métricas son:

```text
support = n_XY / N
confidence = P(Y|X) = n_XY / n_X
base_rate = P(Y) = n_Y / N
lift = confidence / base_rate
leverage = support - (n_X / N) × base_rate
excess_baskets = N × leverage
```

La confianza responde “¿en qué porcentaje de tickets con `X` también aparece
`Y`?”. El lift compara ese porcentaje contra la frecuencia normal de `Y`.
La leverage mide el exceso absoluto frente a independencia. Una pareja puede
tener confianza alta solo porque `Y` es muy popular; por eso ninguna métrica se
usa de forma aislada.

## Protección contra asociaciones débiles

Una regla es elegible solo cuando cumple todo lo siguiente:

1. `X` aparece en al menos 30 tickets.
2. La pareja aparece en al menos `max(5, 0.1% de N)` tickets.
3. Lift mayor a 1 y leverage positiva.
4. El límite inferior unilateral de Wilson al 95% para `P(Y|X)` es mayor que la
   frecuencia base de `Y`.

El intervalo de Wilson reduce la puntuación de resultados con pocas
observaciones. No corrige todos los efectos de probar muchas parejas, pero es
una salvaguarda transparente y estable sin agregar una dependencia estadística.
Si ninguna regla supera los filtros, la interfaz comunica que no hay evidencia
suficiente; no rellena espacios con recomendaciones débiles.

## Lectura operativa en la app

La interfaz traduce estas métricas a lenguaje de piso de venta:

- La tabla por producto muestra **tickets del producto** (`antecedent_tickets`) y
  **tickets con ambos** (`co_tickets`) junto a la confianza, para que sea evidente
  que confianza = tickets con ambos ÷ tickets del producto.
- El límite inferior de Wilson (`confidence_lower_bound`) se presenta como
  **piso seguro**: la confianza mínima razonable dada la cantidad de tickets.
- En las recomendaciones elegibles se añade la etiqueta *asociación por encima de
  lo normal*, porque el piso seguro ya supera la frecuencia base de la sugerencia;
  es una forma llana de decir que la pareja no parece coincidencia casual.

## Orden de las recomendaciones

La puntuación operativa es:

```text
opportunity_score =
    n_X × max(0, Wilson_lower_bound(P(Y|X)) - P(Y))
```

Primero se ordena por esta oportunidad conservadora, después por leverage y
cantidad de tickets conjuntos. Las tres recomendaciones generales no repiten
la misma pareja al revés. En la búsqueda por producto sí se conserva la
dirección: `café → concha` y `concha → café` responden preguntas distintas.

El Excel exportado conserva métricas, periodo observado, puntuación y estado de
elegibilidad para auditoría.

## Interpretación y validación

Las reglas describen compras históricas, no el efecto de hacer una oferta.
Promociones, disponibilidad, combos, temporada, canal y preferencias del cliente
pueden explicar una asociación.

Antes de convertir una sugerencia en política permanente:

1. Revísala en un periodo posterior y por sucursal.
2. Confirma que la confianza y el lift se mantengan.
3. Ejecuta una prueba aleatoria en punto de venta: ofrecer a un grupo y mantener
   otro como control.
4. Evalúa incremento de tasa de compra y margen, no solo ventas observadas.

Con periodos extensos, una evolución futura recomendable es descubrimiento en
un bloque cronológico y validación en el siguiente. No se usa una partición
aleatoria porque mezclaría temporadas y surtidos futuros con el entrenamiento.

## Referencias

- Agrawal, R., Imieliński, T. y Swami, A. (1993), *Mining Association Rules
  between Sets of Items in Large Databases*,
  <https://doi.org/10.1145/170035.170072>.
- Wilson, E. B. (1927), *Probable Inference, the Law of Succession, and
  Statistical Inference*, <https://doi.org/10.1080/01621459.1927.10502953>.
- Tan, P.-N., Steinbach, M. y Kumar, V., *Introduction to Data Mining*,
  capítulo de análisis de asociaciones,
  <https://www-users.cse.umn.edu/~kumar001/dmbook/ch6.pdf>.

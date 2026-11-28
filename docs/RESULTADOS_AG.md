# Resultados del AG (tarea 13)

Todo se reproduce con los comandos de cada sección. Los CSV completos están en `docs/resultados_ag/`.
Escenarios A–D con los grupos de `data/grupos_*.csv` (12 grupos, 1 a 8 personas). El E se omite porque es de 4x4.

## 1. AG contra azar y búsqueda exhaustiva, con los parámetros finales

`python3 -m evacuador experimentos-ag --k K --csv docs/resultados_ag/comparacion_kK.csv` (10 semillas, 0 a 9).
El azar recibe el mismo número de configuraciones distintas que evaluó el AG. La búsqueda exhaustiva solo corre si hay
50 000 combinaciones o menos (k = 2 en A, B y C).

### k = 2

| Escenario | Tamaño | k | Semillas | Evaluaciones | AG media | AG mín | AG máx | Azar media | Azar mín | Azar máx | Exhaustivo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A. Sin humo | 12x20 | 2 | 10 | 230.5 | 0.2946 | 0.2805 | 0.2963 | 0.2712 | 0.2601 | 0.2826 | 0.2963 |
| B. Humo moderado | 12x20 | 2 | 10 | 171.9 | 0.2270 | 0.2226 | 0.2275 | 0.2257 | 0.2223 | 0.2272 | 0.2284 |
| C. Mucho humo | 15x25 | 2 | 10 | 170.2 | 0.2685 | 0.2618 | 0.2695 | 0.2614 | 0.2531 | 0.2695 | 0.2695 |
| D. Mapa grande | 40x40 | 2 | 10 | 313.5 | 0.3345 | 0.3209 | 0.3401 | 0.3183 | 0.3048 | 0.3285 | - |

### k = 3

| Escenario | Tamaño | k | Semillas | Evaluaciones | AG media | AG mín | AG máx | Azar media | Azar mín | Azar máx | Exhaustivo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A. Sin humo | 12x20 | 3 | 10 | 380.2 | 0.3354 | 0.3320 | 0.3365 | 0.3053 | 0.2788 | 0.3220 | - |
| B. Humo moderado | 12x20 | 3 | 10 | 301.7 | 0.2755 | 0.2680 | 0.2773 | 0.2609 | 0.2529 | 0.2692 | - |
| C. Mucho humo | 15x25 | 3 | 10 | 269.8 | 0.2669 | 0.2614 | 0.2693 | 0.2630 | 0.2517 | 0.2691 | - |
| D. Mapa grande | 40x40 | 3 | 10 | 473.5 | 0.3596 | 0.3494 | 0.3685 | 0.3197 | 0.3082 | 0.3266 | - |

### k = 4

| Escenario | Tamaño | k | Semillas | Evaluaciones | AG media | AG mín | AG máx | Azar media | Azar mín | Azar máx | Exhaustivo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A. Sin humo | 12x20 | 4 | 10 | 477.6 | 0.3968 | 0.3723 | 0.3999 | 0.3065 | 0.2831 | 0.3332 | - |
| B. Humo moderado | 12x20 | 4 | 10 | 394.9 | 0.3098 | 0.2713 | 0.3147 | 0.2981 | 0.2826 | 0.3124 | - |
| C. Mucho humo | 15x25 | 4 | 10 | 376.4 | 0.3001 | 0.2833 | 0.3065 | 0.2718 | 0.2653 | 0.2907 | - |
| D. Mapa grande | 40x40 | 4 | 10 | 578.2 | 0.4122 | 0.3811 | 0.4216 | 0.3495 | 0.3293 | 0.3782 | - |

Lectura:
- El AG supera al azar en media en los doce casos.
- En A con k = 2, el mejor resultado del AG iguala a la búsqueda exhaustiva (0.2963) con unas 230 evaluaciones frente a 20 148 pares. En B y C queda en el 99,6 % y el 100 % de la exhaustiva en su mejor semilla.
- La aptitud sube con k porque más salidas reducen tiempos, riesgo y aglomeración. Esos valores no se comparan entre mapas.

## 2. Ajuste de sigma y élites

La convergencia temprana se veía en que la mejor aptitud casi no mejoraba después de las primeras generaciones y algunas semillas se quedaban en un óptimo local (mínimos bajos). Se probó una malla con k = 3 y 10 semillas
(`python3 -m evacuador ajuste-ag --k 3 --csv docs/resultados_ag/ajuste_k3.csv`).

Promedio de los cuatro escenarios:

| Sigma | Élites | Aptitud media | Aptitud mínima | Evaluaciones |
|---|---|---|---|---|
| 0.05 | 1 | 0.3042 | 0.2809 | 208 |
| 0.05 | 2 | 0.3042 | 0.2751 | 202 |
| 0.05 | 4 | 0.3058 | 0.2919 | 189 |
| 0.10 | 1 | 0.3066 | 0.2814 | 288 |
| 0.10 | 2 | 0.3074 | 0.2808 | 283 |
| 0.10 | 4 | 0.3075 | 0.2918 | 258 |
| 0.20 | 1 | 0.3082 | 0.2927 | 352 |
| 0.20 | 2 | 0.3083 | 0.2952 | 326 |
| 0.20 | 4 | 0.3087 | 0.2955 | 307 |
| 0.30 | 1 | 0.3106 | 0.3040 | 383 |
| 0.30 | 2 | 0.3094 | 0.3027 | 356 |
| 0.30 | 4 | 0.3099 | 0.3005 | 329 |

- Subir sigma mejora la media y, sobre todo, la peor semilla: de 0.281 (sigma 0.10) a 0.303 (sigma 0.30).
- Las élites casi no cambian la media (diferencias de 0.002 o menos y sin patrón), así que se deja en 2.
- El costo de subir sigma es evaluar más configuraciones distintas (de 283 a 356, un 26 % más), lo que significa más tiempo.

### Validación con semillas distintas

Para no ajustar sobre las mismas semillas, se comparó sigma 0.10 contra 0.30 (élites 2) con 20 semillas nuevas, de la 100 a la 119 y con k = 2, 3 y 4
(`python3 -m evacuador ajuste-ag --k 2 3 4 --sigmas 0.1 0.3 --elitismos 2 --semillas 20 --desde 100 --csv docs/resultados_ag/validacion_sigma.csv`).

Promedio de los cuatro escenarios:

| k | Sigma | Aptitud media | Aptitud mínima | Evaluaciones |
|---|---|---|---|---|
| 2 | 0.10 | 0.2796 | 0.2691 | 166 |
| 2 | 0.30 | 0.2798 | 0.2714 | 223 |
| 3 | 0.10 | 0.3045 | 0.2750 | 272 |
| 3 | 0.30 | 0.3099 | 0.3004 | 359 |
| 4 | 0.10 | 0.3496 | 0.2997 | 366 |
| 4 | 0.30 | 0.3550 | 0.3335 | 447 |

- Con k = 2 el cambio es neutro. Con k = 3 y 4 mejora la media y la peor semilla.
- Por escenario, la media con sigma 0.30 es igual o mejor en 10 de 12 combinaciones. En las otras dos (A con k = 4 y D con k = 2) baja 0.0017 y 0.0005.
- El mejor resultado alcanzado (máximo) no cambia: sigma 0.30 no encuentra mejores soluciones, encuentra buenas soluciones con más consistencia.

Tabla completa: `docs/resultados_ag/validacion_sigma.csv`.

## 3. Parámetros finales

Población 20, 100 generaciones, torneo 3, élites 2, cruza aritmética (p = 0.80), mutación gaussiana con **sigma = 0.30** (antes 0.10), p_mut_ind = 0.30, p_mut_gen = 0.25, d_min = 3, p_evac = 0.90, ventana 5 s y separación mínima del top 3 de 3 casillas.

## 4. Limitaciones

- La aglomeración es una aproximación estática: cuenta las personas que llegan a una salida dentro de una ventana, sin simular el movimiento ni las colas.
- Con k = 2 en el escenario B, el AG con sigma 0.30 no llegó al óptimo exhaustivo en las 10 semillas (mejor 0.2275 contra 0.2284). La diferencia es de 0,4 %.
- La búsqueda exhaustiva solo es viable con k = 2 y mapas pequeños, así que con k = 3 y 4 la referencia es solo el azar.
- Los grupos son fijos (generados con semilla 1) y el riesgo viene de un único mapa de tóxico por escenario.

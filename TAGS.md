# Etiquetas de las recetas

Cada receta de `recipes.json` lleva en `tags` una o varias de estas etiquetas, escritas tal cual: en minúsculas y sin tildes.
Si una receta lleva una etiqueta que no está en la lista, `generate.py` avisa. En la web solo aparecen las de esta lista.

| Etiqueta | Cuándo ponerla |
|---|---|
| `rapida` | Preparación + cocción suman **30 minutos o menos**. Si suman más, no se pone. `generate.py` avisa si no cuadra. |
| `cena` | Plato salado principal. |
| `postre` | Dulce que se toma de postre. |
| `desayuno` | Típico del desayuno, como tortitas, bollitos o bizcochos. |
| `merienda` | Algo para media tarde, dulce o un snack (tortitas, bollitos, helado…). Los platos principales no la llevan. |
| `horno` | Se cocina en el horno o en la airfryer: la airfryer cuenta como horno. |
| `pescado` | El protagonista es pescado o marisco (gambas, langostinos, atún…). |
| `pollo` | Lleva pollo como protagonista. También si la receta dice «pollo o ternera». |
| `carne` | Ternera, cerdo o carne picada como protagonista. |
| `huevo` | El huevo es el protagonista: huevos marinados, nidos, tortilla… |
| `pasta` | Pasta, fideos, noodles, udon, ramen y ñoquis. |
| `arroz` | El arroz es la base o va en el plato, como el sushi o un plato servido con arroz. No cuentan las obleas ni el papel de arroz. |
| `verdura` | La verdura es la protagonista del plato. |
| `vegetariano` | Plato **salado** sin carne ni pescado. Los postres no la llevan. |
| `ensalada` | Ensaladas. |
| `sopa` | Sopas y caldos, incluido el ramen. |
| `asiatica` | Cocina asiática: japonesa, china, coreana o tailandesa (sushi, tataki, gyozas, noodles, salteados, ramen…). Los postres no la llevan. |

`rapida` y `cena` no salen como botón de filtro en la web. Sí se buscan, y se ven en la ficha de la receta.

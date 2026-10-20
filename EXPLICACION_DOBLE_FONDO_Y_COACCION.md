# Explicación: Bóveda de doble fondo (Negación Plausible)

## 1. ¿Puedo subir mis propios archivos al proyecto?

**No, en esta implementación no se suben archivos binarios a la bóveda de doble fondo.**

La bóveda de doble fondo trabaja únicamente con **texto (entradas)**, no con archivos `.pdf`, `.docx`, `.jpg`, `.zip`, etc.

- Lo que se guarda dentro de cada vista son **entradas de texto** (título + contenido).
- Esto se hace intencionalmente para preservar el principio de **negación plausible**: ambas vistas tienen exactamente el mismo formato y estructura. Si se almacenaran archivos con tamaños distintos o tipos diferentes, eso podría delatar la existencia de dos contenidos distintos.

**Conclusión:** En el estado actual, el contenido es siempre **texto** (demo o el que tú escribas). No existe la funcionalidad para subir archivos propios desde tu PC a la bóveda de doble fondo.

## 2. ¿Siempre son demo o puedo usarlo con información real?

**Puedes usarlo con información real, pero únicamente en formato de texto.**

El sistema cifra ese contenido con **AES-256-GCM** antes de guardarlo en la base de datos local (JSON). No hay ninguna limitación para que escribas información sensible real dentro de las entradas, siempre teniendo en cuenta la limitación anterior: **solo texto, no archivos adjuntos**.

## 3. ¿Existe una función de "coacción" que borre archivos al ingresar la contraseña falsa?

**No. No existe esa función, y por diseño NO debe existir.**

Aquí está la clave más importante para entender esta técnica:

- Al ingresar **cualquiera de las dos contraseñas válidas**, el sistema **desencripta únicamente UNA de las dos vistas**. **Nunca borra, elimina ni modifica** ningún dato.
- Si introduces la **contraseña falsa** (la que abre la vista inocente), se muestra **únicamente el contenido señuelo**. El contenido confidencial **permanece cifrado** dentro de esa misma bóveda.
- Si introduces la **contraseña real**, se muestra **únicamente el contenido secreto**. El contenido inocente **también sigue cifrado** con la otra clave.
- **Ambos contenidos coexisten cifrados en todo momento.** El desencriptado es selectivo, no destructivo.

### ¿Por qué NO se borra al usar la contraseña falsa?

Porque eso **rompería directamente la negación plausible**.

Si, al introducir la clave falsa, el sistema eliminara automáticamente el contenido real, estarías demostrando que **reaccionó ante esa contraseña** y, por tanto, que **sí existía un segundo contenido**. Eso destruiría toda credibilidad ante una situación de coacción.

El principio fundamental es:

> **Negación plausible significa poder negar con credibilidad que exista otro contenido.**

Para lograrlo, el comportamiento debe ser **pasivo e indistinguible**: el sistema simplemente hace lo mismo en ambos casos: toma una contraseña, intenta descifrar y muestra lo que corresponde a esa clave. No toma decisiones "defensivas".

### ¿Cómo funciona entonces ante una situación de coacción?

La idea es conceptual, no automatizada:

1. El usuario crea dos contraseñas distintas para la misma bóveda.
2. Asigna a una de ellas un **contenido inocente y verosímil** (notas de reunión, agenda, tareas, etc.)
3. Asigna a la otra el **contenido realmente sensible**.
4. **Si es obligado a revelar una contraseña**, el usuario entrega **únicamente la contraseña falsa**.
5. Quien la pruebe verá el contenido inocente, completamente creíble. **No hay forma de demostrar que existe una segunda vista.**

**Conclusión:** LegalVault implementa **negación plausible pasiva (desencriptado selectivo)**. No cuenta con un "autodestrucción" o función de coacción, ya que ese tipo de mecanismo suele debilitar la negación plausible en lugar de reforzarla.

En pocas palabras: Con lo que tienes actualmente NO es posible subir archivos binarios directamente a la bóveda de doble fondo. Sí puedes poner tus propias dos contraseñas, pero los archivos desde el PC no se admiten tal como está implementado ahora.
Te lo explico claro para que tomes la decisión correcta.
1. Estado actual: ¿Qué sí permite y qué no?
Lo que SÍ puedes hacer ahora
- Poner tus propias contraseñas. Al crear la bóveda tú escribes dos contraseñas distintas (Contraseña 1 y Contraseña 2). Ahí sí usas las tuyas, no son fijas.
- Poner tu propio contenido. Puedes escribir lo que quieras en los dos campos de texto (vista 1 y vista 2). Ahí metes el señuelo y el contenido real, ambos con tus palabras.
Lo que NO puedes hacer ahora
- Subir archivos .pdf, .docx, .jpg, .zip, etc. La bóveda guarda únicamente texto (entradas con título + contenido).
- Los formularios de creación (CrearBovedaModal) usan <textarea>, no tienen un input[type="file"].
- En el backend, el contenido desencriptado espera una estructura tipo { entradas: [...] } (JSON). No está preparado para guardar bytes de archivos.
2. ¿Por qué está limitado a texto (a propósito)?
El motivo principal es la negación plausible.
- Tamaños distintos delatan. Si la vista falsa tiene un archivo de 2 KB y la vista real tiene un PDF de 2 MB, aunque ambos estén cifrados, el tamaño cifrado aproximado o el espacio ocupado difiere. Eso puede levantar sospechas de que "algo más" existe.
- Formato homogéneo. Al guardar solo texto en formato JSON, ambas vistas son indistinguibles entre sí a nivel de estructura. Esto refuerza que no se pueda probar cuál es cuál (ni si hay dos).
- Es el equilibrio correcto para un prototipo. El README incluso menciona esto como mejora futura: "Relleno a tamaño fijo en las vistas de la bóveda (mejor negación plausible)".
3. ¿Se podría añadir para subir archivos? ¿Es rápido?
Sí se podría añadir, pero no es "añadir un botón" sin más si quieres mantener la negación plausible seria.
Opción A: Añadir archivos tal cual (rápido, debilita negación plausible)
- Guardar por vista: nombre_archivo, mime_type, tamaño, contenido_base64 (cifrado junto al resto).
- Frontend: añadir 2 inputs de archivo (uno por vista).
- Impacto: Bajo-Medio. Funciona rápido.
Desventaja: Los tamaños serían distintos casi seguro → debilitas el punto fuerte de la idea.
Opción B: Forzar tamaño fijo (más realista, un poco más trabajo)
- Definir un tamaño máximo fijo para ambas vistas (ej. 5 MB). Al subir un archivo más pequeño, se hace padding (relleno) antes de cifrar, para que ambas vistas ocupen exactamente el mismo tamaño cifrado.
- Así, mirando el dato cifrado no se distingue qué vista tiene más o menos información.
Esfuerzo: Medio (requiere ajustar cifrado/almacenamiento). No es trivial de 5 minutos, pero tampoco es gigantesco.
4. Mi recomendación para mañana
Para la presentación de mañana, NO lo modifiques.
Mi razonamiento:
- Arriesgas la estabilidad justo antes de exponer. Cambiar el modelo de datos de la bóveda (texto → archivos + posible padding) toca backend + frontend + esquema. Aunque pequeño, siempre hay riesgo de romper lo que ya funciona.
- La idea se demuestra perfectamente con texto. El efecto "misma bóveda, dos contraseñas, dos contenidos distintos" queda clarísimo escribiendo un par de líneas. Ahí ves la negación plausible al instante.
- Es más honesto. Mejor decir: "Actualmente la bóveda trabaja con contenido textual para garantizar la indistinguibilidad entre ambas vistas. El soporte para archivos propios es extensible, pero requiere añadir relleno a tamaño fijo para preservar la negación plausible."
Eso demuestra que entendiste el concepto críticamente, no solo que lo implementaste.
5. Respuesta directa a tu pregunta
- ¿Puedo poner mis propias contraseñas? Sí. Totalmente.
- ¿Puedo subir mis propios archivos? Con el código actual, no.
- ¿Conviene añadirlo hoy para la expo? No, bajo mi criterio. Suma complejidad y puede restar claridad o introducir riesgo innecesario. El texto cumple perfectamente con lo que quieres demostrar.
# LegalVault — Plan al siguiente nivel: evolución de módulos, nuevos módulos y capa educativa

> Documento de **planificación**. No se ha modificado ningún código.
> Fecha: 2026-10-19. Base: revisión completa de la documentación, backend (FastAPI),
> frontend (React/Vite), tests y scripts.
>
> **Principio rector:** *sin perder la idea ni afectar la funcionalidad*. Todo cambio
> debe ser **retrocompatible** con los datos existentes (los JSON actuales y las bóvedas
> ya creadas deben seguir abriéndose igual), incremental, testeable y demostrable.
>
> **Segundo principio:** el proyecto debe **educar sobre criptografía de forma
> disimulada** — el estudiante aprende mientras usa la app, no leyendo un manual aparte.

---

## 1. Estado actual (punto de partida)

| # | Módulo | Estado | Deuda / límite principal |
| --- | --- | --- | --- |
| 1 | Autenticación y usuarios | ✅ | JWT sin refresh persistente; revocación en memoria; sin 2FA; sin rate limiting por IP |
| 2 | Expedientes | ✅ | Sin paginación; sin historial de cambios |
| 3 | Documentos | ✅ | Archivos **sin cifrar en disco**; sin validación de tipo real (magic bytes); SHA-256 no se re-verifica al descargar |
| 4 | Bóveda de doble fondo | ✅ | **Solo texto** (sin archivos); sin relleno a tamaño fijo; contraseñas viajan al servidor |
| 5 | Permisos granulares | ✅ | Sin expiración temporal de permisos; sin plantillas |
| 6 | Auditoría formal | ✅ | Cadena sin **firma externa** (reescribir todo el archivo de forma coherente sería indetectable) |
| 7 | Alertas de seguridad | ✅ | Solo conteos; sin correlación ni detección de anomalías |

Fortalezas a preservar: arquitectura MVC limpia, permisos siempre en servidor, JSON con
escritura atómica, 82 tests en verde, `smoke_test` E2E, documentación coherente.

---

## 2. Parte A — Llevar los módulos existentes al siguiente nivel

Cada mejora indica **prioridad** (P0 = alto impacto/bajo esfuerzo, P1 = medio, P2 = grande),
**impacto educativo** (qué concepto enseña "por los bordes") y **riesgo**.

### Módulo 1 — Autenticación y usuarios

| Mejora | Detalle | Pri. | Enseña |
| --- | --- | --- | --- |
| **Refresh tokens persistentes** | El access token sigue siendo corto; añadir refresh token guardado en JSON con rotación y revocación persistente (sobrevive reinicios). Elimina la limitación documentada en `security.py`. | P0 | Cadena de confianza, rotación de tokens, vida útil de credenciales |
| **2FA con TOTP (RFC 6238)** | Segundo factor opcional por usuario: el servidor genera un secreto Base32, el usuario lo escanea (o copia) y valida 6 dígitos con ventana ±1. Implementable con `hmac`/`struct` de la stdlib (construcción estándar, **no** cripto propia). | P1 | HMAC, tiempo vs. códigos de un uso, sincronización reloj, qué es y qué no protege la 2FA |
| **Rate limiting por IP** | Token bucket en memoria por IP en `/auth/login` (complementa el bloqueo por cuenta). Población simple en `core/`. | P0 | Defensa en profundidad: bloqueo por cuenta ≠ límite por origen |
| **Medidor de entropía de contraseña** | En creación/edición de usuarios: estimación de entropía (largo, diccionario simulado, patrones) con barra y consejo. Guardar el historial de fuerza en JSON si se quiere gamificar. | P1 | Entropía, espacios de búsqueda, por qué "P@ssw0rd" es débil |
| **Historial de sesiones** | Registro de "sesiones activas" (jti, IP, fecha, navegador) con revocación individual desde el perfil. | P2 | Endurecimiento de sesión, superficie de ataque |

### Módulo 2 — Expedientes

| Mejora | Detalle | Pri. | Enseña |
| --- | --- | --- | --- |
| **Paginación real** | `pagina`/`por_pagina` en listados (backend + frontend). Preparado para el crecimiento de datos. | P0 | APIs escalables, coste de O(n) |
| **Historial de cambios (versionado)** | Cada edición guarda un diff en `historial` (quién, cuándo, qué campo cambió). Visible en la ficha del expediente. | P1 | Trazabilidad, inmutabilidad de eventos, complementa la auditoría |
| **Búsqueda full-text simple** | Índice de tokens en memoria (sin dependencias): normalizar, tokenizar, puntuar. | P2 | Indexación, por qué un `LIKE '%x%'` no escala |

### Módulo 3 — Documentos (subida de archivos de verdad)

| Mejora | Detalle | Pri. | Enseña |
| --- | --- | --- | --- |
| **Cifrado en reposo** | Los archivos de `uploads/` se guardan cifrados. Diseño de **envelope encryption**: cada documento recibe una DEK aleatoria (32 B) que se envuelve con una KEK derivada de `LEGALVAULT_MASTER_KEY` (scrypt). La DEK envuelta se guarda en el metadato; al descargar se desenvuelve y descifra en streaming. El servidor aplica permisos **antes** de descifrar. | **P0** | Jerarquía de claves (KEK/DEK), el patrón real de los KMS (AWS KMS, Vault Transit) |
| **Validación real de tipo (magic bytes)** | Sniffing del encabezado: `%PDF`, `PK\x03\x04` (zip/docx/xlsx), `\x89PNG`, `\xFF\xD8\xFF` (JPEG), `Rar!`, cabeceras de texto. Rechazar si la extensión miente. Lista blanca configurable por `TipoDocumento`. Sin dependencias nuevas. | P0 | Por qué "no validar el MIME" es un clásico de vulnerabilidades (evadir listas negras) |
| **Re-verificación de integridad en descarga** | Recalcular SHA-256 al descargar; si no coincide con el metadato → 409 + alerta `DOCUMENTO_CORRUPO` y registro en auditoría. | P0 | Integridad **verificable**, no solo "calculated once" |
| **Streaming de subida** | Leer por chunks en lugar de `await archivo.read()` completo en memoria; validación de tamaño incremental. | P1 | DoS por tamaño, procesamiento en streaming |
| **Vista previa y firma de contenido** | Miniaturas de imágenes/PDF en el frontend (blob URL) solo tras autorizar; opción "verificar integridad de este documento" en la UI que recalcula y compara hash. | P1 | Verificación en cliente, `crypto.subtle` |
| **DLP ligero (patrones sensibles)** | Al subir texto/CSV, detectar patrones ficticios (CURP/RFC/INE *de demostración*) y marcar sensibilidad sugerida. Solo sugiere, no decide. | P2 | Prevención de fugas de datos, falsos positivos |

### Módulo 4 — Bóveda de doble fondo (el diferenciador) ⭐

Es donde más se nota el "siguiente nivel". **La restricción histórica ("solo texto")
ya no tiene por qué ser una limitación: se puede subir cualquier archivo SIN perder la
negación plausible si se hace bien.**

| Mejora | Detalle | Pri. | Enseña |
| --- | --- | --- | --- |
| **4.1 Subida de archivos a la bóveda** | Cada vista admite además entradas con **archivo adjunto**. Diseño: el archivo se cifra con AES-256-GCM en **chunks** (nonce derivado del índice de chunk: `nonce = IV_base(8B) ‖ contador(4B)`, nunca repetido) y se guarda como blob en `data/bovedas/{id}/` (NO en base64 dentro del JSON — el JSON solo guarda metadatos: nombre, mime, tamaño, hash del plaintext). El contenido JSON de la vista se cifra igual que hoy y referencia los blobs. Compatibilidad: las bóvedas viezas (solo `{"entradas":[...]}`) se abren igual; se añade un campo `version` al descifrar. | **P0** | Cifrado autenticado en streaming, por qué GCM necesita nonces únicos, separación metadatos/datos |
| **4.2 Relleno a tamaño fijo (bucket padding)** | **Clave para no romper la negación plausible.** Tamaño máximo por vista configurable (`LEGALVAULT_BOVEDA_BUCKET_MB`, ej. 5 MB). Al guardar, el plaintext se rellena con bytes aleatorios hasta el **bucket** antes de cifrar → ambas vistas ocupan **exactamente lo mismo** en disco. Buckets discretos (1/5/25 MB) evitan revelar tamaños exactos. El relleno se elimina al descifrar (prefijo de longitud). | **P0** | Indistinguibilidad, por qué "el tamaño delata", relleno criptográfico |
| **4.3 Contraseñas que no salen del navegador** | Modo **end-to-end**: derivar la clave con scrypt **en WebCrypto** (`crypto.subtle.deriveBits` con parámetros idénticos) y enviar al servidor solo el ciphertext + salt. El servidor jamás ve la contraseña. Transición: mantener el modo servidor para texto corto y añadir `?e2e=1` o una versión de esquema `v2`; las bóvedas v1 siguen abriendo. | P1 | Cifrado extremo a extremo, "el servidor solo debe ver lo mínimo" (zero-knowledge aproximado) |
| **4.4 Intentos limitados por bóveda** | Contador de fallos por bóveda (no por usuario) con bloqueo temporal; alerta `BOVEDA_BLOQUEO`. Complementa el bloqueo de cuentas. | P1 | Fuerza bruta, por qué los límites de intentos existen en todo lo que usa contraseñas |
| **4.5 Exportar/importar bóveda como archivo `.lvault`** | Export de un único archivo autocontenido (manifest + vistas cifradas + blobs) verificable fuera de la app; import reconstruye la bóveda. Perfecto para la demo: "este archivo se ve igual para todos, y solo dos contraseñas lo abren". | P1 | Serialización, portabilidad, y que **la idea original era "un archivo con doble fondo"** — se recupera ese formato exacto |
| **4.6 Gestión de credenciales con Shamir (n de k)** | Recuperación de bóveda: dividir una clave maestra en *k* compartes de las que basta con *k-1* (Shamir's Secret Sharing). Entregar 2 de 3 a socios del despacho. Usar una librería existente (p. ej. `pyssecret`) — nunca implementar cripto propia. | P2 | Compartición de secretos, por qué "una contraseña no es suficiente" |
| **4.7 Refuerzo KDF** | Mantener scrypt por defecto (compatibilidad) pero subir parámetros a N=2¹⁶ documentando el coste, o activar Argon2id (`argon2-cffi`) para bóvedas nuevas, con los parámetros guardados **en claro junto al ciphertext** (así es portátil y se explica solo). | P1 | Parámetros de KDF almacenados, evolución sin romper datos viejos |

**Anti-mejora deliberada (documentar en la app):** *no* implementar borrado/autodestrucción
ante contraseña falsa. Eso **destruye** la negación plausible (ver
`EXPLICACION_DOBLE_FONDO_Y_COACCION.md`). Sí se puede **explicar en la UI** por qué no
existe — eso es oro educativo: enseña críticamente, no solo a usar.

### Módulo 5 — Permisos avanzados

| Mejora | Detalle | Pri. | Enseña |
| --- | --- | --- | --- |
| **Permisos con caducidad** | La matriz acepta `hasta` (fecha) por usuario/acción; al vencer se ignora y se audita. Ideal para colaboradores externos o peritajes temporales. | P1 | Mínimo privilegio **en el tiempo**, credenciales temporales |
| **Plantillas de permisos** | "Lectura", "Colaborador", "Perito externo" → aplicar de un clic y auditar. | P2 | Políticas vs. permisos ad-hoc (intuición de RBAC/ABAC) |
| **Justificación obligatoria al conceder** | Quien concede debe escribir un motivo (queda en auditoría). | P2 | Accountability |

### Módulo 6 — Auditoría formal

| Mejora | Detalle | Pri. | Enseña |
| --- | --- | --- | --- |
| **Firma de la cadena con clave externa** | El eslabón final se firma con HMAC-SHA256 (o Ed25519) usando una clave **que no está en el archivo de auditoría** (env `LEGALVAULT_AUDIT_KEY`). Un atacante que reescriba todo el JSON no puede re-firmar. Añadir `GET /api/auditoria/verificar` que además valide la firma. | **P0** | Firma de registros, por qué "encadenar sin firmar" no basta, no-repudio |
| **Verificador externo** | Script `python -m scripts.verificar_auditoria data/auditoria.json` que valida cadena+firma **sin servidor** (para el examen: "cualquiera puede verificar el log sin confiar en la app"). | P1 | Verificación independiente, confianza cero |
| **Visualización animada de la cadena** | En `AuditoriaPage`: grafo vertical de eslabones (hash truncado por registro) con botón "verificar" que resalta el primer eslabón roto. | P1 | Que la cadena de hashes sea **visible**, no abstracta → ✅ **implementado 2026-10-20** (`src/components/CadenaAuditoria.jsx`: génesis + eslabones en orden cronológico con `hash_anterior`/`hash_actual` truncados y conectores con ✓/✕, barrido animado al verificar, primer eslabón roto en rojo con latido y los posteriores en ámbar como «no confiable», plegado de cadenas largas, respeto a `prefers-reduced-motion`; helper `hashCorto(hash, cabeza, cola)` en `utils/format.js`; los índices 0-based de `GET /auditoria/verificar` se alinean con el orden del archivo; 19 pruebas nuevas — `npm run test` con 48 en verde) |
| **Export firmado** | Exportar CSV/JSON de la auditoría con un `.sig` adjunto. | P2 | Export verificable |

### Módulo 7 — Alertas de seguridad

| Mejora | Detalle | Pri. | Enseña |
| --- | --- | --- | --- |
| **IP y User-Agent en todas las alertas** | Hoy solo `auth_service` rellena `ip`; propagar `obtener_ip()` a todos los servicios. | P0 | Correlación de eventos |
| **Reglas de correlación** | Reglas simples en un servicio: "≥3 accesos denegados en 5 min del mismo usuario", "descarga de 10 documentos en 1 min", "login con IP nueva". Genera alerta `PATRON_SOSPECHOSO`. | P1 | Detección de anomalías básica, qué es un SIEM |
| **Resumen "estado de seguridad"** | Tarjeta en el panel: puntuación 0–100 derivada de reglas (bloqueos activos, alertas críticas, permisos vencidos, auditoría íntegra). | P2 | Postura de seguridad |

---

## 3. Parte B — Nuevos módulos que suman muchísimo valor

Ordenados por valor/effort. Todos son **compatibles con la decisión "sin base de datos"**.

### Módulo 8 — Firma digital de documentos ⭐⭐ (el más alineado al ámbito jurídico)

- **Qué hace:** el abogado firma un documento con su par de claves **Ed25519** (generado al
  primer uso y guardado cifrado); cualquiera con permiso puede pulsar "Verificar firma" y
  ver ✅ *válido* / ❌ *alterado*, con emisor, fecha y hash del documento.
- **Cómo:** `cryptography` (Ed25519) sobre el SHA-256 del contenido cifrado/descifrado.
  Clave privada protegida con passphrase (scrypt + AES-GCM), nunca en claro; clave pública
  en el perfil del usuario (exportable).
- **Endpoints:** `POST /documentos/{id}/firmar`, `POST /documentos/{id}/verificar`,
  `GET /usuarios/{id}/clave-publica`.
- **Enseña:** no-repudio, firma vs. cifrado (¡la distinción clásica!), por qué un hash
  solo no basta, integridad + autenticidad.
- **Por qué encaja:** un expediente jurídico **real** exige firma electrónica; es el
  módulo que más "cara de solución real" da sin romper nada.

### Módulo 9 — Sellado de tiempo (timestamping) ⭐

- **Qué hace:** a la firma se le añade un sello: `Sello = Firmar_TSA(Hash(doc) ‖ fecha)`.
  Un "servicio de sellado" local (simula una TSA, RFC 3161) con clave propia; el sello
  queda en auditoría y en el metadato del documento.
- **Enseña:** por qué la firma sola no prueba *cuándo* se firmó, qué es una TSA, ataques
  de retrodatación.
- **Combo con M8:** "Firmado y sellado" — el entregable completo de confianza digital.

### Módulo 10 — Laboratorio criptográfico interactivo ⭐⭐⭐ (el corazón educativo "disimulado")

Página `/laboratorio` con mini-apps que usan **la misma infraestructura real** del proyecto:

1. **"Ver el cifrado"**: pestaña en bóveda/documentos que muestra el JSON crudo
   (`salt/nonce/datos` en base64) junto al texto plano, con botón "cambiar 1 bit y ver
   cómo falla todo" (alterar ciphertext → `InvalidTag`).
2. **Derivador de claves visual:** el usuario escribe una contraseña, ve scrypt correr en
   tiempo real con N/r/p ajustables, ve el salt cambiar → clave distinta, y un contador de
   tiempo. Enseña por qué "rápido" no es "seguro" aquí.
3. **HMAC-TOTP a mano:** ver los 6 dígitos cambiar cada 30 s y cómo un código viejo deja
   de servir (conecta con el Módulo 1 si se implementa 2FA).
4. **Cadena de auditoría en vivo:** panel que muestra `hash_anterior ‖ registro → hash_actual`
   calculándose en el navegador con `crypto.subtle` y permitiendo **romperla a mano**
   (editar un registro → la verificación señala el eslabón).
5. **Fuerza bruta simulada (controlada):** un generador de contraseñas débiles + un
   "atacante" local que prueba un diccionario de 10 000 entradas contra un hash scrypt
   con parámetros bajos (N=2⁴) para verlo caer en segundos, y luego con N=2¹⁴ para ver
   el coste real. **Todo local, contra datos ficticios.**
6. **AES-GCM pedagógico:** cifrar "hola" con y sin nonce, demostrar reutilización de nonce.

### Módulo 11 — Retos y progreso (gamificación discreta)

- `/retos`: 6–8 retos automáticos con validación server-side, por ejemplo:
  1. *Detecta la manipulación:* altera `auditoria.json` (te lo dice la app dónde, en modo
     práctica) y consigue que `verificar` lo señale. → enseña integridad.
  2. *Abre la vista B sin romper nada:* encuentra la contraseña demo (pista: entropía). →
     fuerza bruta y KDF.
  3. *Escala de privilegios fallida:* intenta administrar la matriz de permisos sin ser
     responsable y observa el 403 auditado. → mínimo privilegio.
  4. *Firma alterada:* modifica un documento firmado y verifica. → no-repudio.
  5. *Cambia un bit del ciphertext de una bóveda.* → autenticación de mensajes.
  6. *Sandbox de capas:* identifica en qué capa (red, disco, aplicación) está protegido
     cada dato (.JWT, uploads, bóveda, auditoría).
- Progreso en `data/retos.json` (acumulado por usuario); insignias visibles en el panel.
- **Enseña jugando**, sin que parezca un curso: el estudiante "usa la app" y de paso
  demuestra que entendió los conceptos.

### Módulo 12 — Esteganografía (módulo "de espías" opcional ⭐)

- **Qué hace:** empaquetar una bóveda exportada (`.lvault`) dentro de una imagen PNG
  cualquiera usando **LSB** (bit menos significativo de cada canal), con la clave de
  extracción siendo una de las contraseñas de la bóveda. Imagen resultante: indetectable
  a simple vista y **aparentemente inocente**.
- **Por qué encaja:** es literalmente el espíritu de la idea original del profesor
  ("fotos de vacaciones") y complementa la negación plausible: *negar con credibilidad*
  + *ocultar sin que se note*.
- **Cuidado:** implementación LSB simple y documentada como **demostración**; añadir aviso
  honesto de que la esteganografía real exige más (entropía, resistencia a análisis
  estadístico). Enseñar también a **detectar** LSB trivial (histograma) es medio módulo
  educativo gratis.
- **Espera:** P2 (tras tener la export `.lvault`, Módulo 4.5).

### Módulo 13 — Mensajería cifrada end-to-end en el expediente ⭐

- **Qué hace:** hilo de comentarios/mensajes entre los usuarios de un expediente,
  cifrados **en el navegador** con ECDH (X25519) → clave compartida → AES-GCM. El
  servidor solo almacena ciphertext; solo los participantes pueden leerlo (incluso el
  admin **no** puede leer mensajes — es un punto discutible y excelente para debatir en
  clase: "¿y el admin? ¿y la orden judicial?").
- **Enseña:** intercambio de claves Diffie-Hellman, clave efímera vs. identidad,
  Perfect Forward Secrecy (opción: ratchet básico), y el dilema real de la privacidad
  vs. cumplimiento.
- **Espera:** P2. Requiere WebCrypto (ya viable en cualquier navegador moderno).

### Módulo 14 — Export/import cifrado de expedientes

- **Qué hace:** exportar un expediente completo (documentos + metadatos + manifiesto) en
  un solo `.lvx` cifrado (passphrase → scrypt → AES-GCM), con manifiesto JSON firmado
  dentro (hash de cada archivo). Import en otra instancia de LegalVault lo verifica todo.
- **Enseña:** paquetes cifrados, manifiestos de integridad, por qué "zip con contraseña"
  (ZIPCrypto) es inseguro — comparar con nuestro formato.

### Módulo 15 — Panel de "Cripto en acción" transversal (capa educativa)

Ver Parte C.

---

## 4. Parte C — La capa educativa *disimulada* (qué lo hace memorable)

Objetivo: que **usar** LegalVault sea aprender criptografía sin darse cuenta. Cinco
mecanismos de bajo coste y alto impacto:

### C1. Tarjetas de concepto contextuales (componente `<Concepto cripto="aes-gcm" />`)

- En cada página, junto a elementos relevantes, un `ℹ️` que abre una tarjeta de 3–5 líneas
  con el concepto real que está pasando **ahí** (ej. junto al campo de contraseña de la
  bóveda: *"scrypt convierte esto en una clave; por eso el servidor nunca guarda tu
  contraseña"*).
- Catálogo estático en `src/conceptos.js` (10–15 conceptos): AES-GCM, nonce, salt, KDF,
  SHA-256, cadena de hashes, JWT, mínimo privilegio, negación plausible, firma digital,
  esteganografía, entropy, TOTP.
- Coste: **medio día**. Retorno enorme en el valor educativo percibido.

### C2. Modo "ver lo que realmente se guarda"

- Toggle global (icono 🔍) que, donde aplique, muestra la representación cruda:
  - Bóveda: los bytes base64 de cada vista + metadatos (`salt`, `nonce`) resaltados.
  - Documento: cabecera cifrada + hash SHA-256 con sus 64 hex visibles.
  - Auditoría: `hash_anterior + registro → hash_actual` en una línea.
- Efecto: el estudiante **ve** que no hay texto en claro. Esa imagen vale más que mil
  diapositivas.

### C3. Página "¿Qué me protege y qué no?"

- Tabla viva generada desde el código: dato → capa de protección → límite conocido.
  Ej: *JWT en localStorage → firmado y con expiración → pero expuesto a XSS*. Incluye la
  sección de **límites honestos** de la negación plausible.
- Enseña **pensamiento crítico**, que es lo que realmente evalúa un profesor de seguridad.

### C4. Retos (Módulo 11) + insignias

### C5. Guion de demo con narrativa (documento nuevo `docs/GUION_DEMO.md`)

- Escenario continuado: *"Un despacho guarda la identidad de un testigo protegido…"*
  con el orden exacto de clics, las dos contraseñas, el momento de abrir la auditoría y
  verificar la cadena, y las frases clave para cada tramo. Incluye el "remate" final:
  *"si me obligan a dar una contraseña, doy la falsa"*.

---

## 5. Parte D — Roadmap por fases

Convenciones: mismas que el plan original (sin BD, JSON atómico, permisos en servidor,
español, tests por fase, actualizar README + este documento al cerrar).

### Fase 6 — "Archivos de verdad" (M4.1 + M4.2) — *prioridad máxima*

- Subida de archivos a la bóveda (blobs en `data/bovedas/`, metadatos cifrados en el JSON
  de la vista, AES-GCM chunked con nonce por índice).
- Relleno a bucket fijo para ambas vistas (independientemente de si hay archivo o no).
- Compatibilidad: bóvedas v1 se abren sin cambios; nuevo campo `version`.
- Frontend: `input type="file"` en `CrearBovedaModal` y `AbrirBovedaModal`, barra de
  progreso, lista de adjuntos con hash visible.
- Tests: round-trip archivo, tamaños idénticos entre vistas, blob alterado detectado,
  bóveda v1 legible, smoke extendido.
- **Criterios:** ✅ se sube un PDF real a cada vista; ✅ ambas vistas ocupan lo mismo en
  disco; ✅ `pytest` en verde; ✅ la demo actual sigue funcionando.

### Fase 7 — "Confianza" (M3 cifrado en reposo + M3 magic bytes + M3 verificación + M6 firma de cadena)

- Envelope encryption de `uploads/` (DEK/KEK), validación de magic bytes, re-verificación
  SHA-256 al descargar con alerta ante corrupción.
- Firma HMAC/Ed25519 de la cadena de auditoría con clave externa + verificación extendida.
- Script `scripts/verificar_auditoria.py`.
- **Migración:** al arrancar, cifrar en background los uploads existentes (flag de
  migración en `data/`), conservando hash.
- **Criterios:** ✅ ningún `.pdf` de `uploads/` legible en claro; ✅ subir un `.exe`
  renombrado a `.pdf` rechazado; ✅ reescribir auditoría completa ya **no** verifica;
  ✅ docs viejos descargan idénticos.

### Fase 8 — "Firma y sello" (M8 + M9)

- Pares Ed25519 por usuario, firmar/verificar en documentos, sello de tiempo local,
  combo "Firmado y sellado" en la tabla de documentos.
- Reto #4 conectado.

### Fase 9 — "Aprender jugando" (C1 + C2 + C3 + M10 + M11 + M15)

- Tarjetas de concepto, modo "ver el cifrado", laboratorio, 6 retos con validación,
  insignias, guion de demo.
- **Criterio clave:** recorrer la app sin leer nada y salir sabiendo explicar AES-GCM,
  hash y negación plausible en 2 minutos.

### Fase 10 — "Endurecer" (M1 refresh+rate limit, M4.4, M5 caducidad, M7 correlación, M1 entropía)

- Todo lo defensivo que falta, en un solo bloque porque toca servicios de seguridad.

### Fase 11 — "Extender" (M12 esteganografía, M14 export `.lvx`, M4.5 `.lvault`, M4.6 Shamir, M2 historial)

### Fase 12 — "Sellar" (E2E de bóvedas v2 con WebCrypto, M13 mensajes E2E, documentación final)

**Orden sugerido para una entrega con expo:** 6 → 7 → 9 → 8 → 10. Las fases 6 y 7 son las
que más "wow" dan sin riesgo conceptual; la 9 es la que vende lo educativo.

---

## 6. Parte E — Riesgos, compatibilidad y reglas innegociables

### Reglas innegociables (no romper la idea)

1. **Nunca cripto propia.** Solo `cryptography` y construcciones estándar de stdlib
   (`hmac`, `hashlib`) con parámetros documentados.
2. **La negación plausible no se toca:** sin borrado ante contraseña falsa, sin etiquetas
   en las vistas, sin metadatos que delaten cuál es cuál, y con bucket padding para que
   el tamaño tampoco delate.
3. **Los datos existentes siguen abriendo.** Toda evolución de esquema lleva `version`
   y migración al vuelo. Las bóvedas actuales se abren idénticas.
4. **Permisos siempre en el servidor**; la UI solo oculta, nunca autoriza.
5. **Nada de secretos** en logs, alertas ni auditoría (claves, contraseñas, plaintext).
6. **Cada fase en verde:** `pytest` + `smoke_test` + `npm run build` antes de dar por
   cerrada la fase; actualizar `README.md` y este documento.

### Riesgos técnicos y mitigación

| Riesgo | Mitigación |
| --- | --- |
| El bucket padding agranda el JSON/disco | Blobs fuera del JSON (`data/bovedas/`); bucket configurable y por defecto modesto (5 MB) |
| Cifrar uploads rompe descargas existentes | Migración con flag al arrancar + test de round-trip con archivo pre-existente |
| Scrypt en cliente (E2E) lento en máquinas débiles | Parámetros del cliente ligeramente menores documentados; no bloquea la fase 6 |
| Añadir dependencias (`argon2-cffi`, `pyssecret`) | Opcional/fallback a stdlib; el core nunca depende de ellas |
| Scope creep (la lista es larga) | Este documento está **priorizado**; P0 antes que P2; cada fase es entregable por sí sola |
| WebCrypto/LSB/ECDH poco portables | Progresión: fallback servidor con aviso; browsers modernos ok |

### Esfuerzo estimado por fase (orden de magnitud)

| Fase | Estimación |
| --- | --- |
| 6 (archivos en bóveda + padding) | 1–2 días |
| 7 (cifrado en reposo + verificación + firma de cadena) | 1–2 días |
| 9 (capa educativa + laboratorio + retos) | 2–3 días |
| 8 (firma digital + sellado) | 1–2 días |
| 10 (endurecimiento) | 1 día |
| 11–12 (extensiones) | 2–4 días |

---

## 7. Resumen ejecutivo — Top 10 de impacto

1. **Archivos en la bóveda con bucket padding** → cumple el "subir cualquier archivo"
   sin sacrificar la negación plausible (la mejora que más pide el usuario).
2. **Cifrado en reposo de documentos (DEK/KEK)** → el hueco de seguridad más visible hoy.
3. **Firma digital + sellado de tiempo** → credibilidad jurídica inmediata.
4. **Firma de la cadena de auditoría con clave externa** → cierra la debilidad nº 1 del
   módulo 6.
5. **Validación de tipo (magic bytes) + re-verificación de SHA-256 al descargar.**
6. **Capa educativa disimulada:** tarjetas de concepto + modo "ver el cifrado".
7. **Laboratorio criptográfico interactivo** (el módulo que convierte la app en curso).
8. **Retos con gamificación** (aprender jugando y demostrar comprensión).
9. **Refresh tokens + rate limiting por IP + TOTP.**
10. **Esteganografía LSB y `.lvault` exportable** → el toque "de película" que redonda
    la idea original del profesor.

Con esta hoja de ruta LegalVault pasa de "prototipo funcional" a **plataforma criptográfica
con alma educativa**, manteniendo intactos su idea, su arquitectura y lo que ya funciona.

---

## 8. Parte F — Mapa de viabilidad: ¿qué implemento antes de la presentación?

> **Contexto:** presentación **mañana**. El objetivo es agregar ideas *hasta donde se
> pueda*, sin romper lo que ya funciona. El criterio de orden es **facilidad + rapidez ×
> seguridad para la demo** (no solo esfuerzo): algo que se hace en 2 horas pero puede
> dejar la bóveda rota a las 2 a.m. **no** es viable, es temerario.
>
> **Regla de oro para esta noche:** trabajar en una rama (`git checkout -b
> feat/expo-rapida`), correr `pytest` + `smoke_test` + `npm run build` tras **cada**
> mejora, y tener un punto de retorno limpio. Si algo no queda en verde en 1–2 h, se
> posterga y sigue el siguiente del listado.

### Nivel 1 — Viables HOY, en horas (riesgo nulo/bajo: son aditivos o solo tocan frontend)

| # | Mejora | Dónde | Esfuerzo | Por qué es segura |
| --- | --- | --- | --- | --- |
| 1 | **Tarjetas de concepto cripto contextuales** (C1) | Solo frontend | 2–3 h | Catálogo en `src/conceptos.js` + componente nuevo; no toca lógica existente |
| 2 | **Página "¿Qué me protege y qué no?"** (C3) | Solo frontend | 1–2 h | Contenido estático; es la página que más pensamiento crítico demuestra |
| 3 | **Re-verificar SHA-256 al descargar** + botón "Verificar integridad" en la tabla de documentos | Backend (poco) + frontend | 1–2 h → ✅ **implementado 2026-10-19** | Añade una comprobación; si no coincide lanza alerta, no rompe nada |
| 4 | **Validación de tipo por magic bytes** al subir | Backend (poco) | 1–2 h | ⚠️ Incluir `txt/png/jpg/pdf/zip/csv` en la lista blanca (el `seed` sube `.txt`) para no romper la demo → ✅ **implementado 2026-10-19** (`app/core/magic_bytes.py`, lista blanca configurable por `LEGALVAULT_EXTENSIONES_PERMITIDAS`, alerta `documento_rechazado` + auditoría `denegado`; 113 tests en verde) |
| 5 | **IP en todas las alertas y auditoría** (hoy solo auth la rellena) | Backend | 1 h | Propagar `obtener_ip()` a los servicios; cambio cosmético-registrable |
| 6 | **Rate limiting por IP en login** (token bucket en memoria) | Backend (poco) | 1–2 h | Aislado en `core/`; solo afecta al endpoint de login |
| 7 | **Visualización animada de la cadena de auditoría** (eslabones con hash truncado + resaltar el roto) | Solo frontend | 2–3 h | Ya existe `GET /auditoria/verificar`; es **el remate visual** de la demo de auditoría → ✅ **implementado 2026-10-20** (`CadenaAuditoria.jsx` + estilos animados + 19 pruebas: barrido eslabón a eslabón, primer roto en rojo y resto «no confiable», plegado de cadenas largas y movimiento reducido; 48 pruebas de interfaz en verde y `npm run build` OK) |
| 8 | **Medidor de entropía de contraseña** | Frontend (+1 endpoint opcional) | 2–3 h | Cálculo local en JS; efecto educativo inmediato en el formulario |
| 9 | **Página 404 propia + toast de errores** (pulido) | Solo frontend | 1 h | Cosmético, sube la percepción de calidad → ✅ **implementado 2026-10-19** (`src/pages/NotFoundPage.jsx` para rutas desconocidas en lugar de la redirección silenciosa a `/`, con la ruta fallida y salida según sesión; capa global de toasts `ToastContext` + bus `utils/notificar.js` con avisos de **sesión expirada (401)**, **backend inaccesible** (mensaje amigable en español) y **error de servidor (5xx)**, deduplicación y red de seguridad de promesas rechazadas; los 4xx contextuales siguen solo inline; 29 pruebas nuevas con Vitest + React Testing Library — `npm run test`) |

**Combo realista de una tarde/noche:** Nivel 1 completo (~1–1.5 días de trabajo
efectivo; si solo hay unas horas, el **Top 4: #1, #3, #7, #2** — son los que más se notan
en pantalla).

### Nivel 2 — Viables si sobra tiempo hoy (1 día c/u, riesgo bajo: cambios aditivos)

| # | Mejora | Dónde | Nota |
| --- | --- | --- | --- |
| 10 | Paginación en listados | Backend + frontend | Mecánico, pero toca muchos endpoints: hacerlo de una vez, no a medias |
| 11 | Historial de cambios de expedientes | Backend (JSON nuevo) + frontend | Aditivo: archivo nuevo, no toca el modelo existente |
| 12 | Permisos con caducidad (`hasta`) | Backend + frontend | Campo aditivo con default `null` = comportamiento actual intacto |
| 13 | Reglas de correlación en alertas | Backend | Aditivo: nuevo servicio que **genera** alertas; no modifica las existentes |
| 14 | Resumen "estado de seguridad" en el panel | Frontend + endpoint | Derivado de datos ya existentes |

### Nivel 3 — Alto impacto para la expo, riesgo MEDIO (elegir **uno** y tener tiempo de testearlo)

| # | Mejora | Esfuerzo | Impacto en la expo | Riesgo |
| --- | --- | --- | --- | --- |
| 15 | **Bucket padding en la bóveda** (solo relleno, *sin* archivos aún) | ~4–6 h | ⭐⭐⭐ Responde el "¿y si subo archivos?" con "el tamaño ni siquiera te delata" | Medio: toca `boveda_crypto`/`boveda_service`; **las bóvedas viejas deben seguir abriendo** (migración al vuelo) |
| 16 | **Firma HMAC de la cadena de auditoría + `scripts/verificar_auditoria.py`** | ~3–5 h | ⭐⭐⭐ "Reescribir todo el log ya no basta, hay una clave fuera del archivo" | Medio-bajo: solo se firman registros nuevos; verificar valida ambos |
| 17 | **Modo "ver el cifrado"** (endpoint que devuelve el material cifrado de la bóveda a creador/admin, y lo muestra en base64 con salt/nonce resaltados) | ~3–4 h | ⭐⭐⭐ El efecto "no hay texto en claro, mira" es el más fotogénico | Medio: exponer blobs requiere permiso estricto (creador/admin) y jamás la contraseña |
| 18 | **Retos básicos (3–4) con validación** | ~4–6 h | ⭐⭐ Gamificación visible | Medio-bajo: usa endpoints existentes; progreso en JSON nuevo |

**Recomendación:** con tiempo de **una noche**, el **#16 o el #17** (no los dos). Con dos
noches, **#15 + #16**.

### Nivel 4 — Post-exposición (requieren diseño de detalle y tests extensos)

| # | Mejora | Por qué espera |
| --- | --- | --- |
| 19 | **Archivos completos en la bóveda** (chunking + blobs + padding integrado) — Fase 6 | Toca el núcleo del diferenciador: 1–2 días con tests; no se improvisa la noche anterior |
| 20 | **Cifrado en reposo de uploads (DEK/KEK) + migración** — Fase 7 | Implica migrar archivos existentes al arrancar |
| 21 | **Firma digital Ed25519 + sellado de tiempo** — M8/M9 | Diseño de gestión de claves por usuario |
| 22 | Refresh tokens, TOTP, Shamir, esteganografía, `.lvault`, mensajes E2E | Cada uno es una fase con su spec y tests |

### Mapa visual (de mayor a menor viabilidad inmediata)

```
VIABLE YA (horas, riesgo ↓)                ──►  #1 tarjetas  #2 límites  #3 SHA-256
                                                #4 magic bytes  #5 IP  #6 rate limit
                                                #7 cadena animada  #8 entropía  #9 pulido
                                                        │
SI SOBRA TIEMPO (1 día, riesgo bajo)        ──►  #10 paginación  #11 historial
                                                #12 caducidad  #13 correlación  #14 panel
                                                        │
UN SOLO GRAN HITE (noche, riesgo medio)     ──►  elijir UNO:  #15 padding bóveda
                                                #16 firma de auditoría  #17 ver el cifrado
                                                #18 retos
                                                        │
POST-EXPOSICIÓN (días, requieren spec)      ──►  #19 archivos en bóveda  #20 cifrado en reposo
                                                #21 firma digital  #22 resto del roadmap
```

---

## 9. Parte G — ¿El plan es suficiente para empezar a implementar?

**Respuesta corta: sí para los Niveles 1 y 2; casi, pero no del todo, para los Niveles 3–4.**
Depende de qué tan lejos quieras llegar.

### Lo que SÍ está resuelto en este documento (da para codificar ya)

- ✅ **Qué** mejorar en cada módulo y **por qué** (prioridades, impacto educativo).
- ✅ **Reglas de compatibilidad** (versionado de esquemas, datos viejos siguen abriendo,
  permisos en servidor, sin cripto propia) → evita errores de diseño caros.
- ✅ **Criterios de aceptación y pruebas por fase** (qué debe quedar en verde).
- ✅ **Riesgos y mitigaciones** conocidos.
- ✅ Para las mejoras **Nivel 1–2** el diseño es tan directo (propagar un parámetro,
  añadir una comprobación, crear una página estática) que **no hace falta más plan**:
  se abre el archivo correspondiente y se hace.

### Lo que FALTA antes de implementar los Niveles 3–4 (specs técnicos de detalle)

Este documento es de nivel **diseño de solución**, no de **contrato de implementación**.
Para las fases estructurales conviene un mini-spec por fase (1–2 h de redacción cada uno)
que responda preguntas que hoy el código no contesta:

| Falta especificar | Afecta a | Ejemplo de la pregunta concreta |
| --- | --- | --- |
| **Formato de datos byte a byte** | #15 padding, #19 archivos | ¿Dónde vive el prefijo de longitud que marca el relleno? ¿Bucket = redondeo al siguiente múltiplo de 1 MB? ¿El blob va en `data/bovedas/{id}/` con qué nombre? |
| **Esquema de nonce chunked** | #19 archivos | IV base de 8 B + contador 4 B en big-endian, o `HKDF(nonce‖índice)`: hay que **elegirlo y escribirlo** antes de tocar `boveda_crypto` |
| **Contratos de API nuevos** | Todos los nuevos endpoints | Rutas, schemas Pydantic, códigos de error, quién tiene permiso |
| **Estrategia de migración** | #16 (registros viejos sin firmar), #20 (uploads en claro) | ¿Se firman los registros viejos al verificar? ¿La migración de uploads corre en el lifespan con flag en `data/`? |
| **Formato de los datos educativos** | #1 tarjetas, retos, insignias | Catálogo de conceptos: ¿fijo en JS o servido por API? ¿Progreso de retos por usuario en qué archivo? |
| **Casos de prueba concretos** | Fases 6, 7, 12 | Lista exacta de tests nuevos (el patrón ya existe en `tests/`, solo hay que enumerarlos) |

### Además faltan 3 decisiones **tuyas**, no técnicas

1. **Alcance exacto de la expo:** ¿cuánto tiempo real hay entre ahora y la presentación?
   Eso define si el plan es "Nivel 1" o "Nivel 1 + un Nivel 3". Sin ese número, la
   lista no se puede recortar.
2. **Qué se muestra mañana:** si la demo va a incluir la bóveda, **no** se toca la
   bóveda la noche anterior (ya lo decía `EXPLICACION_DOBLE_FONDO_Y_COACCION.md`).
   Eso decide si el hite de la noche es #16/#17 en vez de #15.
3. **Estrategia de ramas y punto de corte:** rama aparte, y una hora de colchón para
   `pytest` + `smoke_test` + recorrido manual de la demo. Si algo no pasa, se descarta
   sin remordimiento (la demo actual ya es suficiente, según el propio análisis de
   presentación).

### Veredicto

> **Este documento es suficiente para empezar a implementar YA los Niveles 1 y 2** (no
> falta planificación, falta ejecución). **Para los Niveles 3–4 hace falta un paso más,
> pero no de más planificación estratégica**: hace falta un **spec técnico por fase**
> (formato de datos, contratos de API, migración, tests), que es trabajo de horas, no de
> días. Si quieres, el siguiente paso natural es que redacte el spec de la fase que
> elijas para la expo (recomendación: **#16 firma de la cadena de auditoría** o
> **#17 modo "ver el cifrado"**, porque tocan un módulo que ya vas a demostrar y tienen
> retorno visual inmediato) antes de escribir una sola línea de código.

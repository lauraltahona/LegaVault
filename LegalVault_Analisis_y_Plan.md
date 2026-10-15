# LegalVault — Análisis completo y plan de implementación

> Documento generado tras una revisión completa del código (backend FastAPI + frontend React/Vite).
> Fecha: 2026-10-14. Commit revisado: `474a91c` (rama `main`).
>
> **Decisión de arquitectura vigente:** NO se usará base de datos. Todos los datos son
> *mock/ficticios* y se persisten **localmente en archivos JSON** con escritura atómica.
> El sistema debe ser **plenamente funcional** y **registrar localmente toda acción**.

---

# PARTE I — Análisis del proyecto

## 1. Resumen ejecutivo

**LegalVault** es un prototipo académico de gestión segura de expedientes jurídicos
para despachos de abogados. Centraliza casos y documentos aplicando autenticación,
control de acceso por roles, auditoría y —como elemento diferenciador— una **bóveda
cifrada de "doble fondo"** basada en el concepto de *negación plausible* (dos
contraseñas, dos conjuntos de contenido: uno visible y otro confidencial).

**Estado global:** la aplicación está **funcional y bien construida** para los módulos
1 (autenticación/usuarios), 2 (expedientes), 3 (documentos), **4 (bóveda cifrada de
doble fondo)** y 7 (alertas de seguridad). Quedan parciales los módulos
**5 (permisos avanzados)** y **6 (auditoría formal inalterable)**.

El proyecto ya arranca, tiene una prueba de humo E2E (`backend/scripts/smoke_test.py`)
y una suite `pytest` (`backend/tests/`).

## 2. Explicación de funcionalidades (qué hace hoy el sistema)

### Módulo 1 — Autenticación y gestión de usuarios ✅
- Inicio de sesión usuario/contraseña; devuelve token **JWT** con expiración. Cierre de
  sesión con **revocación del token** en el servidor (lista en memoria).
- Contraseñas como **hash scrypt** (N=2¹⁴, r=8, p=1, salt de 16 bytes), comparación en
  tiempo constante. Nunca se devuelve ni se registra la contraseña.
- CRUD de usuarios (solo admin), activación/desactivación, cambio de rol y
  restablecimiento de contraseña.
- Reglas: no se puede desactivar/degradar al **último admin activo** ni desactivar la
  propia cuenta.
- `/usuarios/seleccion` con datos mínimos (id, usuario, nombre, rol) para que abogados
  asignen responsables sin ver correos.

### Módulo 2 — Gestión de expedientes ✅
- Crear, consultar, editar y **archivar** expedientes.
- Campos: identificador, asunto, cliente, tipo de proceso, estado, abogado responsable,
  descripción y usuarios autorizados.
- Búsqueda por texto y filtros por estado/tipo/abogado.
- **Acceso**: admin ve todo; abogado/asistente solo donde son responsables o autorizados.
- Respuesta enriquecida con nombre del responsable y total de documentos.

### Módulo 3 — Gestión de documentos ✅
- Carga (multipart), consulta, descarga y eliminación.
- Clasificación por **tipo** y por **nivel de sensibilidad** (público, interno, confidencial).
- Archivo guardado en `backend/data/uploads/` con **nombre aleatorio** por id; el nombre
  original solo como metadato. **SHA-256** por documento.
- Límite de tamaño configurable (25 MB). Búsqueda y filtros.
- Solo autor o admin pueden eliminar.

### Módulo 4 — Bóveda cifrada de doble fondo ✅
- Crea una bóveda con **dos contraseñas distintas**. El contenido se cifra con **AES-256-GCM**
  y la clave se deriva de la contraseña con **scrypt** (salt y nonce aleatorios por operación).
- Cada bóveda guarda **dos vistas** en **orden aleatorio** y sin etiquetas; al desbloquear se
  prueba cada vista con la contraseña dada y se muestra la que valida (tag GCM correcto). Si
  ninguna valida → error **genérico** (negación plausible, sin pistas).
- Operaciones: crear, listar metadatos, desbloquear, añadir entradas, cambiar la contraseña de
  una vista y eliminar. Nunca se almacenan contraseñas ni claves.
- Interfaz dedicada (`/boveda`) y eventos de seguridad registrados como alertas.

### Módulo 5 — Control de acceso y permisos ✅
- Permisos por rol, acceso por expediente (responsable + autorizados) y restricción del
  asistente sobre documentos confidenciales. Verificación en servidor.
- **Matriz granular** por usuario/acción (`leer`, `cargar`, `descargar`, `editar`,
  `eliminar`) que refina los permisos por defecto, administrable por el admin o el
  responsable desde la interfaz (`PUT /api/expedientes/{id}/permisos`).

### Módulo 6 — Auditoría y registro de actividad ✅
- Registro de eventos (tipo, severidad, usuario, IP, mensaje, fecha), sin secretos.
- Auditoría **separada** de las alertas, con **encadenado de hashes SHA-256**
  verificable y vista/consulta dedicada (Módulo 6, Fase 3).

### Módulo 7 — Alertas de seguridad ✅
- Registra login exitoso/fallido, bloqueo/desbloqueo, acceso denegado, alta/edición/
  desactivación de usuario, creación/edición/archivado de expediente y operaciones con
  documentos.
- **Bloqueo temporal** tras N intentos fallidos (5 por defecto, 15 min) y desbloqueo manual.
- Panel admin con filtros, resumen y marcado leído/no leído.

## 3. Arquitectura

```
backend/
  app/
    models/        # M — dataclasses puras (User, Expediente, Documento, Alerta, Boveda, BaseEntity)
    repositories/  # M — JSON con escritura atómica (JsonRepository genérico)
    services/      #   — lógica de negocio y reglas de seguridad (+ permissions.py)
    controllers/   # C — routers FastAPI + dependencies (JWT/roles)
    schemas/       # V — contratos Pydantic de entrada/salida
    core/          # config, security (scrypt/JWT), boveda_crypto (AES-GCM), constants, exceptions, container, bootstrap, validators
  data/            # usuarios.json, expedientes.json, documentos.json, bovedas.json, alertas.json, uploads/
  scripts/         # seed.py (datos demo) y smoke_test.py (prueba E2E)
  tests/           # suite pytest (bóveda: cripto + API)

frontend/src/
  api/          # cliente HTTP centralizado + módulos por recurso
  context/      # AuthContext (sesión, token en localStorage, rol)
  components/   # Layout, RutaProtegida, Modal, Insignia, Aviso, TablaDocumentos, SubirDocumentoModal, CrearBovedaModal, AbrirBovedaModal
  pages/        # Login, Dashboard, Expedientes, ExpedienteDetalle, Documentos, Boveda, Usuarios, Alertas
  constants.js  # etiquetas de enums
  utils/format.js
```

Reglas respetadas: controladores delgados; permisos **siempre en servidor**; JSON con
escritura atómica (`os.replace`) y `RLock`; DI centralizada en `core/container.py`;
proxy de Vite `/api → http://127.0.0.1:8000`.

## 4. Estado por módulo

| Módulo | Descripción | Estado | Observación |
| --- | --- | --- | --- |
| 1. Autenticación y usuarios | Login/logout, CRUD, roles, bloqueo, scrypt | ✅ Completo | Revocación de token en memoria. |
| 2. Expedientes | CRUD + archivar, filtros, acceso por permisos | ✅ Completo | — |
| 3. Documentos | Carga/descarga/eliminación, clasificación, SHA-256 | ✅ Completo | Archivos **sin cifrar** en disco. |
| 4. Bóveda doble fondo | AES-GCM + derivación de clave + negación plausible | ✅ Completo | Implementado en la Fase 2. |
| 5. Permisos avanzados | Matriz granular por usuario/acción | ✅ Completo | Refina rol + expediente + sensibilidad. |
| 6. Auditoría formal | Registro inalterable/encadenado | ✅ Completo | Cadena SHA-256 verificable (Fase 3). |
| 7. Alertas de seguridad | Bloqueo, panel, resumen, filtros | ✅ Completo | — |

## 5. Seguridad y criptografía ya implementada

- Hash de contraseñas con **scrypt** + salt por usuario y comparación en tiempo constante.
- Sesiones **JWT HS256** con `exp`, `nbf`, `iat` y `jti` para revocación.
- Autorización de rol y acceso a expediente/documento **en el servidor**.
- **SHA-256** para integridad de documentos.
- Alertas **sin secretos**; validaciones de entrada; saneamiento de nombres (anti path traversal).
- Excepciones de dominio → HTTP 401/403/404/409/415/422/423.

## 6. Fortalezas

1. Arquitectura limpia y por capas, fácil de extender.
2. MVC real: controladores delgados, servicios con reglas, schemas Pydantic.
3. Buenas prácticas base: scrypt, JWT, permisos en servidor, sin secretos en logs.
4. Repositorio JSON genérico con escritura atómica.
5. Prueba de humo E2E para módulos 1, 2, 3 y 7.
6. Documentación (README + documento de módulos).
7. UI coherente y con manejo de 401.

## 7. Hallazgos, riesgos y deuda técnica

### Coherencia funcional (corregido en Fase 1 ✅)
- **Asistente y carga de documentos:** resuelto — el asistente puede cargar documentos
  `público`/`interno` en expedientes autorizados, pero no `confidencial` (403). README,
  backend y UI alineados (`ROLES_CARGA_DOCUMENTOS`, flag `puedeCargar`).
- **HTTP al eliminar sin permiso:** resuelto — `documento_service.eliminar` lanza
  `PermissionDeniedError` (403) en lugar de `ConflictError` (409).
- **Edición por abogado autorizado (no responsable):** resuelto — solo el admin o el
  abogado **responsable** pueden editar/archivar; el resto solo consulta y carga.

### Seguridad / prototipo
- Cifrado en reposo **solo para el contenido de las bóvedas** (AES-256-GCM, Módulo 4 ✅);
  los archivos de documentos siguen guardándose sin cifrar en disco.
- Revocación de tokens en memoria (se pierde al reiniciar).
- Auditoría con cadena de integridad SHA-256 (Módulo 6 ✅): el archivo sigue siendo un JSON
  editable, pero cualquier alteración es **detectable** con la verificación.
- Sin rate limiting por IP (el bloqueo es por cuenta).
- Sin paginación en listados.
- `JsonRepository` relee el archivo en cada operación; sin bloqueo entre procesos
  (ok con un solo worker; con varios podría haber condiciones de carrera).
- Sin validación real de tipo/contenido de archivo (solo límite de bytes).

### Entorno
- Python instalado: **3.14.5** (README probado con 3.13). Node **24**, npm **11**.
- **Existen** `backend/.venv` y `frontend/node_modules` (entorno listo para ejecutar).
- **Worktree sobrante**: `.kilo/worktrees/false-speak` (copia del mismo commit en detached HEAD).

---

# PARTE II — Plan de implementación por fases

## Convenciones para todas las fases

- **Sin base de datos.** Persistencia local en JSON dentro de `backend/data/`
  (configurable con `LEGALVAULT_DATA_DIR`) usando `JsonRepository` (escritura atómica).
- **Datos mock.** Los clientes, expedientes y documentos son ficticios; `scripts/seed.py`
  prepara la demo.
- **Toda acción se registra localmente** (auditoría/alertas) sin secretos.
- **Cada fase termina con pruebas** (unitarias con `pytest` + integración vía `TestClient`
  + checklist manual de UI) y debe dejar el proyecto arrancable.
- **Estilo:** español en dominios/mensajes, capas del proyecto respetadas, controladores
  delgados, permisos en servidor, esquemas Pydantic para entrada/salida.
- **Al cerrar cada fase:** actualizar `README.md` y este documento (marcar checklist).

## Estructura de pruebas a crear

```
backend/
  tests/
    conftest.py                 # TestClient con LEGALVAULT_DATA_DIR temporal + usuarios demo
    test_security.py            # hash/verify, JWT (emitir, decodificar, revocar)
    test_validators.py
    test_permissions.py         # reglas de autorización por rol y expediente
    test_json_repository.py
    test_api_modulos.py         # API módulos 1, 2, 3 y 7 (auth, usuarios, expedientes,
                                #   documentos, alertas y permisos del asistente)
    test_boveda_crypto.py       # cripto de la bóveda (Fase 2)
    test_boveda_api.py          # API de la bóveda (Fase 2)
    test_auditoria_repository.py  # cadena de hashes y detección de manipulación (Fase 3)
    test_auditoria_api.py       # API + integridad de auditoría (Fase 3)
    test_permisos_api.py        # matriz de permisos por expediente (Fase 4)
```

- Añadir `pytest` y `httpx2` (necesario por `TestClient`; Starlette ≥1.8 usa `httpx2`)
  a `requirements-dev.txt` — **ya creado en la Fase 0**.
- `conftest.py` fija `LEGALVAULT_DATA_DIR` a un `tmp_path` antes de importar `app`,
  igual que hace hoy `smoke_test.py`.

---

## Fase 0 — Puesta en marcha y verificación

**Objetivo:** dejar el entorno listo y confirmar que la base actual funciona.

**Tareas**
1. Crear entorno virtual e instalar dependencias:
   - `cd backend; python -m venv .venv`
   - `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
   - `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`
     (usa **`httpx2`** —no `httpx`— porque Starlette ≥1.8 lo exige para el `TestClient`).
2. Verificar instalación con **Python 3.14**. Si alguna dependencia falla, usar Python
   3.12/3.13 para el venv.
3. `cd frontend; npm install`.
4. Ejecutar `python -m scripts.seed` y `python -m scripts.smoke_test`.
5. Arrancar con `.\start-all.ps1`, entrar con `admin / Admin123!` y recorrer la UI.
6. Eliminar el worktree sobrante: `git worktree remove .kilo/worktrees/false-speak`.

**Pruebas / criterios de aceptación**
- [x] `pip install` sin errores.
- [x] `smoke_test` imprime **"TODAS LAS PRUEBAS OK"**.
- [x] Backend responde en `http://127.0.0.1:8000/docs` y frontend en `http://localhost:5173`.
- [x] Login y navegación básica funcionan.

**Estimación:** 30–60 min. **Riesgo:** versiones de `requirements.txt` inexistentes o
incompatibles con Python 3.14 (mitigar fijando Python 3.13).

**✅ RESULTADO (Fase 0 completada el 2026-10-14)**
- Entorno creado con **Python 3.14.5**; todas las dependencias de `requirements.txt`
  instalaron sin conflictos (fastapi 0.143.0, uvicorn 0.54.0, PyJWT 2.15.1, pydantic 2.14.1).
- **Hallazgo:** `smoke_test.py` fallaba porque `requirements.txt` no incluye el cliente HTTP
  del `TestClient`. Starlette 1.8.0 exige **`httpx2`** (no `httpx`). Se creó
  `backend/requirements-dev.txt` con `pytest` y `httpx2`, y se documentó en el `README.md`.
- `scripts.seed` generó los datos demo (3 usuarios + 2 documentos) correctamente.
- `scripts.smoke_test` → **31 comprobaciones, "TODAS LAS PRUEBAS OK"**.
- `frontend/npm install` OK; `npm run build` OK (esbuild funcional pese al aviso de
  `allowScripts`); `npm run dev` sirvió la app en `:5173` y el **proxy `/api` → backend** funcionó.
- Backend real verificado: `GET /` 200, `GET /api/health` 200, `POST /api/auth/login` 200,
  `GET /docs` 200.
- Worktree sobrante `.kilo/worktrees/false-speak` **eliminado**; `git status` limpio.
- Nota de entorno: npm advierte 4 vulnerabilidades en dependencias de desarrollo del
  frontend (no bloqueante para el alcance académico).

---

## Fase 1 — Coherencia funcional y pruebas base

**Objetivo:** corregir incoherencias menores y dejar una base de pruebas automatizadas.

**Tareas**
1. **Permisos del asistente (decidir y alinear):** opción recomendada — el asistente
   puede **cargar** documentos no confidenciales en expedientes autorizados.
   - Cambiar `DocumentoService.subir` para aceptar `Rol.ASISTENTE`, y en `subir` impedir
     que el asistente cree documentos `confidenciales` (forzar/validar `interno` o inferior).
   - Crear constante `ROLES_CARGA_DOCUMENTOS = (ADMIN, ABOGADO, ASISTENTE)` en
     `app/core/constants.py`.
   - Mostrar el botón "+ Cargar documento" al asistente en
     `ExpedienteDetallePage.jsx` y `DocumentosPage.jsx` (usar un nuevo flag `puedeCargar`
     del `AuthContext`, distinto de `puedeGestionar`).
   - Actualizar la tabla de roles del `README.md`.
2. **Código HTTP correcto:** en `documento_service.eliminar`, lanzar
   `PermissionDeniedError` (403) en lugar de `ConflictError` (409).
3. **Edición de expedientes:** documentar o restringir. Recomendado: solo el
   **responsable** o un **admin** puede editar/archivar (los autorizados solo leen/cargan).
   Ajustar `_asegurar_gestion` en `ExpedienteService`.
4. **Pruebas base** (`pytest`) para `security`, `validators`, `permissions`,
   `JsonRepository` y flujos API de 1–3 y 7 (equivalente al `smoke_test`, pero como tests).
5. **Script de arranque de tests:** añadir `pytest.ini`/`pyproject.toml` con config y
   quizá un `run-tests.ps1`.

**Pruebas / criterios de aceptación**
- [x] `pytest` en verde.
- [x] Un asistente puede cargar un documento `interno` pero **no** `confidencial` (403/422).
- [x] Eliminar documento sin permiso devuelve **403**.
- [x] Un abogado autorizado (no responsable) **no** puede editar/archivar (403).
- [x] README coincide con el comportamiento real.

**Estimación:** 1–2 h. **Riesgo:** bajo.

**✅ RESULTADO (Fase 1 completada el 2026-10-14)**
- **Permisos del asistente:** nueva constante `ROLES_CARGA_DOCUMENTOS = (ADMIN, ABOGADO,
  ASISTENTE)`; `DocumentoService.subir` ahora acepta al asistente y rechaza que este cree
  documentos `confidenciales` (403). Flag `puedeCargar` en `AuthContext` y botón «+ Cargar
  documento» visible para los tres roles; en `SubirDocumentoModal` el asistente no ve la
  opción «Confidencial». `permissions.py` ampliado con `es_responsable`,
  `puede_gestionar_expediente` y `puede_cargar_documento`.
- **Código HTTP correcto:** `documento_service.eliminar` ahora lanza `PermissionDeniedError`
  (**403**) en lugar de `ConflictError` (409).
- **Edición de expedientes:** `_asegurar_gestion` restringe editar/archivar a **admin o
  responsable**; un usuario autorizado solo consulta y carga. La UI (`ExpedientesPage`)
  oculta los botones de editar/archivar salvo para el responsable o el admin.
- **Pruebas base:** nuevas `tests/test_security.py`, `test_validators.py`,
  `test_permissions.py`, `test_json_repository.py` y `test_api_modulos.py` (flujos 1–3 y 7,
  incluidos los permisos del asistente y la restricción de edición). `conftest.py` asegura
  los usuarios demo al iniciar el cliente de pruebas. **73 passed**; `smoke_test` en verde.
- **Configuración de tests:** `backend/pytest.ini` presente. `npm run build` OK.

---

## Fase 2 — Módulo 4: Bóveda cifrada de doble fondo (PRIORIDAD)

**Objetivo:** implementar el diferenciador. Dos contraseñas → dos vistas independientes,
cifrado autenticado y negación plausible, todo persistido localmente.

**Diseño criptográfico**
- **AES-256-GCM** (`cryptography`) para cifrado autenticado (confidencialidad + integridad).
- **Derivación de clave (KDF):** `hashlib.scrypt` (ya disponible, sin dependencias extra)
  o Argon2id si se acepta añadir `argon2-cffi`. Recomendado: **scrypt** para minimizar
  dependencias, con parámetros documentados.
- Cada **vista** almacena de forma independiente: `salt` (16 B), `nonce` (12 B para GCM),
  `contenido_cifrado` (ciphertext + tag, en base64). Nunca se guardan contraseñas ni claves.
- **Negación plausible:** la bóveda tiene exactamente 2 vistas; al desbloquear se intenta
  descifrar cada una con la contraseña dada. Si una valida (tag GCM correcto) se muestra su
  contenido; si ninguna valida → "contraseña incorrecta" genérico. El nombre/estructura no
  revela cuál coincidió ni cuántos fondos hay.
- El contenido de cada vista es un JSON (lista de entradas: título, tipo, texto/archivo de
  referencia, sensibilidad) que se cifra como bloque.

**Tareas backend**
1. `requirements.txt`: añadir `cryptography`.
2. `app/core/boveda_crypto.py`:
   - `derivar_clave(password, salt) -> bytes`
   - `cifrar(datos: bytes, password: str) -> dict` → `{salt, nonce, contenido}`
   - `descifrar(blob: dict, password: str) -> bytes | None` (None si falla el tag)
   - `cambiar_credenciales(blob, nueva_password) -> dict`
3. `app/models/boveda.py`: `Boveda(BaseEntity)` con `nombre`, `descripcion`,
   `expediente_id` (opcional), `vistas: list[dict]` (2 slots: `{salt, nonce, contenido}`),
   `activo: bool`. Serialización `to_dict/from_dict`.
4. `app/repositories/boveda_repository.py`: `BovedaRepository(JsonRepository[Boveda])`.
5. `app/services/boveda_service.py`:
   - `crear(actor, datos)`: recibe `nombre`, `descripcion`, `password_visible`,
     `password_confidencial`, y contenido inicial de cada vista. Cifra y guarda.
   - `listar(actor)`: metadatos (nunca contenido ni blobs).
   - `desbloquear(boveda_id, password, actor) -> vista`: intenta ambas vistas; registra evento.
   - `agregar_entrada(boveda_id, password, entrada, actor)`: descifra, añade, re-cifra.
   - `cambiar_credenciales(boveda_id, password_actual, password_nueva, actor, vista)`.
   - `eliminar(boveda_id, actor)`.
   - Registrar **toda acción** en la auditoría (ver Fase 3; por ahora en alertas).
6. `app/schemas/boveda_schema.py`: `BovedaCreate`, `BovedaResponse` (sin blobs),
   `DesbloqueoRequest`, `CambioCredencialesRequest`, `VistaResponse`.
7. `app/controllers/boveda_controller.py` + registrar el router en `controllers/__init__.py`
   y en `app/main.py`.
8. `app/core/container.py`: añadir `boveda_repository()` y `boveda_service()`.
9. `scripts/seed.py`: crear una bóveda demo con dos vistas (plantillas administrativas vs
   documento "confidencial" ficticio).

**Endpoints**
- `POST /api/bovedas` — crear.
- `GET /api/bovedas` — listar metadatos.
- `GET /api/bovedas/{id}` — metadatos de una.
- `POST /api/bovedas/{id}/desbloquear` — contraseña → contenido de la vista (o 401 genérico).
- `POST /api/bovedas/{id}/entradas` — agregar entrada (requiere contraseña de la vista).
- `PUT /api/bovedas/{id}/credenciales` — cambiar contraseña de una vista.
- `DELETE /api/bovedas/{id}` — eliminar (admin o autor).

**Tareas frontend**
1. `src/api/bovedas.js` con las llamadas.
2. `src/pages/BovedaPage.jsx`: listar bóvedas, crear (formulario con las dos contraseñas),
   desbloquear (input de contraseña) y mostrar el contenido de la vista resultante.
3. Añadir enlace "Bóveda" en `components/Layout.jsx` y ruta en `App.jsx`.
4. `src/constants.js`: etiquetas para tipos de entrada de bóveda si aplica.

**Pruebas**
- Unitarias (`tests/test_boveda_crypto.py`): cifrar/descifrar ida y vuelta; contraseña
  incorrecta devuelve `None`; alterar un byte del ciphertext falla la verificación.
- Integración (`tests/test_boveda.py`): crear; desbloquear con A muestra vista A;
  con B muestra vista B; con incorrecta da 401; cambiar credenciales y revalidar;
  las respuestas de listar **no** exponen blobs.
- Manual: demo de negación plausible con las dos contraseñas.

**Criterios de aceptación**
- [x] Contraseña A y B abren contenidos distintos.
- [x] Contraseña incorrecta → error genérico, sin pistas.
- [x] Manipular el ciphertext es detectado (fallo de integridad).
- [x] No se almacena ninguna contraseña ni clave en claro.
- [x] Las acciones de bóveda quedan registradas localmente.
- [x] `pytest` en verde.

**Estimación:** 1–2 días. **Riesgo:** medio (diseño cripto y UX de dos contraseñas).

**✅ RESULTADO (Fase 2 completada el 2026-10-14)**
- Backend: `app/core/boveda_crypto.py` (AES-256-GCM + scrypt, salt/nonce aleatorios),
  `models/boveda.py`, `repositories/boveda_repository.py`, `services/boveda_service.py`,
  `schemas/boveda_schema.py` y `controllers/boveda_controller.py` (7 endpoints registrados).
- Las dos vistas se guardan en **orden aleatorio** y sin etiquetas; el archivo
  `data/bovedas.json` contiene solo `{salt, nonce, datos}` por vista (verificado: sin texto en claro).
- Autorización: crear requiere rol admin/abogado; ver/abrir según creador o acceso al
  expediente; eliminar solo creador o admin. Cada operación sensible registra una alerta
  (`boveda_creada`, `boveda_abierta`, `boveda_acceso_fallido`, `boveda_editada`,
  `boveda_credenciales`, `boveda_eliminada`).
- Frontend: `api/bovedas.js`, `pages/BovedaPage.jsx`, `components/CrearBovedaModal.jsx`,
  `components/AbrirBovedaModal.jsx`; enlace «Bóveda» y ruta `/boveda`; estilos propios.
- Pruebas: **28 pruebas pytest en verde** (`tests/test_boveda_crypto.py` y
  `tests/test_boveda_api.py`), más el bloque de bóveda añadido a `scripts/smoke_test.py`.
- Verificación manual en vivo (datos demo): «BovedaPublica123!» y «BovedaReservada123!»
  abren contenidos distintos; clave incorrecta → 401.

---

## Fase 3 — Módulo 6: Auditoría formal (toda acción, local, inalterable)

**Objetivo:** registrar **toda acción** del sistema en un log local append-only con
verificación de integridad, separado de las alertas.

**Diseño**
- Nuevo modelo `RegistroAuditoria`: id, fecha, usuario, usuario_id, rol, accion, entidad,
  entidad_id, resultado (ok/denegado/error), detalle (sin secretos), `hash_anterior`,
  `hash_actual`.
- **Cadena de integridad:** `hash_actual = SHA256(hash_anterior + serialización(registro))`.
  El primer registro encadena desde un hash génesis fijo. Cualquier edición manual rompe la
  cadena y es detectable con un endpoint de verificación.

**Tareas backend**
1. `app/models/registro_auditoria.py`.
2. `app/repositories/auditoria_repository.py` con métodos `append(registro)` (calcula el
   encadenado) y `verificar_cadena() -> (bool, indice_roto)`.
3. `app/services/auditoria_service.py`:
   - `registrar(accion, actor, entidad, entidad_id, resultado, detalle)`.
   - `listar(filtros)` (fecha, usuario, acción, resultado), `verificar_integridad()`.
4. Instrumentar **todas** las acciones en los servicios existentes (login, logout, CRUD de
   usuarios/expedientes/documentos, desbloqueos, intentos denegados, acciones de bóveda).
5. `app/schemas/auditoria_schema.py` y `app/controllers/auditoria_controller.py` (solo admin).
6. Registrar router y DI en `container.py`.
7. Mantener `AlertaService` para el panel de alertas; la auditoría es el registro completo.

**Endpoints**
- `GET /api/auditoria` — listar con filtros (solo admin).
- `GET /api/auditoria/verificar` — resultado de la verificación de cadena.

**Tareas frontend**
1. `src/pages/AuditoriaPage.jsx` (solo admin): tabla con filtros y botón "Verificar integridad".
2. Enlace en `Layout.jsx` y ruta en `App.jsx` (solo admin).
3. `src/api/auditoria.js`.

**Pruebas**
- Unitarias: el encadenado es correcto; modificar un registro en el archivo rompe la
  verificación; `verificar_cadena` detecta el índice.
- Integración: cada operación de la API genera su registro; un usuario no admin recibe 403.
- Manual: editar `backend/data/auditoria.json` a mano y comprobar que la verificación falla.

**Criterios de aceptación**
- [x] Toda acción relevante queda registrada localmente.
- [x] La cadena de hashes se verifica correctamente.
- [x] La manipulación manual es detectable.
- [x] Solo el admin consulta la auditoría.
- [x] `pytest` en verde.

**Estimación:** medio día. **Riesgo:** medio (instrumentar todos los servicios sin duplicar).

**✅ RESULTADO (Fase 3 completada el 2026-10-14)**
- Backend: `app/models/registro_auditoria.py` (con `HASH_GENESIS` y `calcular_hash()` con
  serialización canónica y determinista), `app/repositories/auditoria_repository.py`
  (`append` atómico que encadena + `verificar_cadena() -> (bool, indice_roto)`),
  `app/services/auditoria_service.py` (`registrar`, `listar`, `verificar_integridad`, `resumen`).
- Constantes `AccionAuditoria` y `ResultadoAuditoria` añadidas a `core/constants.py`.
- **Todos** los servicios existentes instrumentados con una llamada a la auditoría junto a
  cada alerta: `auth_service` (login/fallo/bloqueo/logout), `user_service` (CRUD, estado,
  contraseña, desbloqueo), `expediente_service` (crear/editar/archivar + acceso denegado),
  `documento_service` (cargar/descargar/eliminar + acceso denegado) y `boveda_service`
  (crear/abrir/fallo/editar/credenciales/eliminar + acceso denegado). `AlertaService` se
  conserva como vista de seguridad para el panel.
- Endpoints: `GET /api/auditoria` (filtros acción/resultado/usuario/entidad/rango/limite),
  `GET /api/auditoria/verificar` y `GET /api/auditoria/resumen`; los tres solo para admin.
  Wiring en `container.py`, `controllers/__init__.py`, `schemas/__init__.py` y `main.py`.
- Frontend: `api/auditoria.js`, `pages/AuditoriaPage.jsx` (tabla + filtros + botón
  «Verificar integridad» con aviso verde/rojo), ruta `/auditoria` (solo admin), enlace
  «📜 Auditoría» en el menú, etiquetas `ACCIONES_AUDITORIA`/`RESULTADOS_AUDITORIA`, estilo
  `.celda-hash` y tarjeta «Registros de auditoría» en el panel.
- Pruebas: `tests/test_auditoria_repository.py` (cadena, edición, reordenación y borrado
  intermedio) y `tests/test_auditoria_api.py` (403 no admin, login/logout/denegaciones
  auditadas, verificación y detección de manipulación vía API). Total acumulado: **43 passed**.
  Bloque de auditoría añadido a `scripts/smoke_test.py` → **TODAS LAS PRUEBAS OK**.
- Verificación en vivo (uvicorn + urllib): `verificar` → `integro: true`; el logout quedó
  auditado; `abogado.demo` recibió 403; cadena final íntegra. `npm run build` OK.

---

## Fase 4 — Módulo 5: Permisos avanzados por expediente

**Objetivo:** matriz de permisos granular por usuario/expediente y por acción.

**Diseño**
- Añadir a `Expediente` (o a un nuevo `Permiso`) una estructura de permisos por usuario:
  `{usuario_id: {leer, cargar, descargar, editar, eliminar}}`.
- Compatibilidad: mantener `abogado_responsable_id` y `usuarios_autorizados` como base;
  los permisos granulares refinan las acciones.

**Tareas backend**
1. Ampliar `app/services/permissions.py` con funciones por acción
   (`puede_leer`, `puede_cargar`, `puede_descargar`, `puede_editar`, `puede_eliminar`).
2. Añadir campo `permisos` a `Expediente` y sus esquemas; defaults según rol.
3. Aplicar en `ExpedienteService` y `DocumentoService`.
4. Endpoints para administrar permisos (`PUT /api/expedientes/{id}/permisos`).
5. Registrar cambios de permisos en la auditoría.

**Tareas frontend**
1. Sección "Permisos" en `ExpedienteDetallePage.jsx` (solo admin/responsable) con
   checkboxes por usuario y acción.
2. `src/api/expedientes.js`: llamada de actualización de permisos.

**Pruebas**
- Unitarias de cada función de permiso (combinaciones rol/acción).
- Integración: un usuario sin `descargar` recibe 403 al descargar; con `editar` puede editar.
- Manual: asignar permisos desde la UI y verificar el efecto.

**Criterios de aceptación**
- [x] Cada acción respeta la matriz en el servidor.
- [x] La UI refleja los permisos efectivos.
- [x] `pytest` en verde.

**Estimación:** medio día. **Riesgo:** medio (no romper la lógica actual de acceso).

**✅ RESULTADO (Fase 4 completada el 2026-10-14)**
- **Modelo:** nuevo campo `permisos: dict[str, dict[str, bool]]` en `Expediente`
  (`{usuario_id: {leer, cargar, descargar, editar, eliminar}}`) con normalización que
  descarta claves/acciones desconocidas. Constante `ACCIONES_PERMISO` y acción de auditoría
  `EXPEDIENTE_PERMISOS`.
- **Permisos efectivos:** `permissions.permisos_efectivos(user, exp)` combina el acceso base
  (responsable/admin → todo; autorizado → leer/cargar/descargar) con la matriz almacenada, que
  puede conceder o revocar. El admin y el responsable **no** pueden ser restringidos. Nuevas
  funciones por acción (`puede_accion`, `puede_leer_documento`, `puede_descargar_documento`,
  `puede_eliminar_documento`) y `puede_administrar_permisos` (solo admin/responsable, evita la
  escalada: tener `editar` no basta para administrar la matriz).
- **Servicios:** `DocumentoService` usa las nuevas funciones (cargar/descargar/eliminar) y
  `ExpedienteService.actualizar_permisos` reemplaza la matriz validando que solo afecte a
  usuarios autorizados activos; al cambiar `usuarios_autorizados` se podan los permisos de los
  usuarios retirados. Editar/archivar respeta la acción `editar`.
- **API:** `PUT /api/expedientes/{id}/permisos` (body `{permisos: {...}}`), solo admin o
  responsable; cambios registrados en la auditoría (`expediente_permisos`).
- **Frontend:** componente `PermisosExpediente.jsx` embebido en `ExpedienteDetallePage.jsx`
  (visible solo a admin/responsable) con checkboxes por usuario y acción y botón de guardado;
  `api/expedientes.js#actualizarPermisos`; etiquetas `ACCIONES_PERMISO` en `constants.js`.
- **Pruebas:** nuevas `tests/test_permisos_api.py` (conceder/revocar, solo admin/responsable,
  rechazo de usuarios no autorizados y auditoría) y casos unitarios de la matriz en
  `test_permissions.py`. Bloque nuevo en `scripts/smoke_test.py`. **82 passed**; smoke en verde;
  `npm run build` OK.

---

## Fase 5 — Documentación, modelo de amenazas y demo

**Objetivo:** cerrar el entregable académico.

**Tareas**
1. Actualizar `README.md` con el estado real (módulos 4, 5 y 6 completos).
2. Crear `docs/MODELO_DE_AMENAZAS.md`: qué cubre y qué no la negación plausible
   (memoria, caché, archivos temporales, capturas, copias de seguridad, metadatos).
3. Crear `docs/GUION_DEMO.md`: pasos de demostración con datos ficticios.
4. (Opcional) Diagrama de arquitectura y del flujo de la bóveda (Mermaid).
5. Repaso final de la matriz de pruebas global.

**Criterios de aceptación**
- [ ] Documentación coherente con el código.
- [ ] Guion de demo reproducible de principio a fin.
- [ ] Todas las fases marcadas como completadas.

**Estimación:** 2–3 h.

---

# PARTE III — Matriz de pruebas global

## Automatizadas
- [x] `pytest` cubre `security`, `validators`, `permissions`, `JsonRepository`.
- [x] `pytest` cubre la API de módulos 1, 2, 3, 7 (equivalente al `smoke_test`).
- [x] `pytest` cubre bóveda (A/B, incorrecta, integridad, cambio de credenciales).
- [x] `pytest` cubre auditoría (encadenado y detección de manipulación).
- [x] `pytest` cubre la matriz de permisos.
- [x] `scripts/smoke_test.py` sigue en verde.

## Manuales (UI)
- [ ] Login/logout con los tres roles; bloqueo tras 5 intentos y desbloqueo por admin.
- [ ] CRUD de expedientes, filtros y búsqueda.
- [ ] Carga/descarga/eliminación de documentos; confidenciales invisibles para el asistente.
- [ ] **Bóveda:** crear con dos contraseñas, desbloquear con cada una, contraseña incorrecta,
      cambio de credenciales.
- [x] **Auditoría:** listado con filtros y verificación de integridad.
- [x] **Permisos:** asignar y comprobar efecto.
- [ ] Persistencia: reiniciar el backend y comprobar que todo sigue guardado localmente.
- [ ] Casos límite: archivo > 25 MB, archivo vacío, duplicados, último admin.

## Seguridad
- [ ] La bóveda no revela cuántos fondos hay ni cuál coincidió.
- [ ] Errores de contraseña genéricos (sin filtrar información).
- [ ] No se guardan contraseñas ni claves en JSON, logs ni respuestas.
- [x] Manipular ciphertext o el log de auditoría es detectable.

---

# PARTE IV — Decisiones y riesgos

| Tema | Decisión |
| --- | --- |
| Base de datos | **No** se usa. Persistencia local en JSON. |
| Datos | **Mock/ficticios**; `scripts/seed.py` prepara la demo. |
| Cifrado de bóveda | AES-256-GCM + KDF scrypt (o Argon2id si se acepta la dependencia). |
| Auditoría | Local, append-only, con cadena de hashes. |
| Carga de documentos por asistente | Permitida (público/interno) en expedientes autorizados; nunca `confidencial` (Fase 1 ✅). |
| Orden de fases | 0 → 2 (bóveda) → 3 (auditoría) → 1 → 4 → 5, por impacto evaluable. |
| Permisos granulares | Matriz `{usuario: {accion}}` que refina rol + acceso; admin/responsable no restringibles; solo admin/responsable la administran (Fase 4 ✅). |

**Riesgos principales**
- Versión de Python 3.14 vs. dependencias (mitigar con 3.13 en el venv).
- Complejidad criptográfica del módulo 4 (usar librerías reconocidas, nunca cripto propia).
- Instrumentar toda la auditoría sin duplicar ni filtrar secretos.

---

## Ruta rápida recomendada (para el mínimo entregable diferenciador)

1. **Fase 0** (arrancar y validar). ✅ *Completada 2026-10-14.*
2. **Fase 2** (bóveda de doble fondo) — es lo que más peso tiene. ✅ *Completada 2026-10-14.*
3. **Fase 3** (auditoría de toda acción). ✅ *Completada 2026-10-14.*
4. **Fase 1** (coherencia + pruebas base). ✅ *Completada 2026-10-14.*
5. **Fase 4** (Módulo 5: permisos avanzados por expediente). ✅ *Completada 2026-10-14.*
6. **Fase 5** (documentación, modelo de amenazas y demo).

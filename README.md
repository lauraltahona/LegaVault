# LegalVault

Aplicación para la gestión segura de expedientes jurídicos. Combina la
administración de casos y documentos con autenticación, control de acceso por
rol, una bóveda cifrada de doble fondo, auditoría encadenada y alertas de
seguridad.

> **Prototipo académico.** Usa datos ficticios. No debe emplearse con
> expedientes reales sin una evaluación de seguridad profesional.

## Módulos implementados

| Módulo | Descripción | Estado |
| --- | --- | --- |
| **1. Autenticación y usuarios** | Inicio/cierre de sesión, CRUD y desactivación de usuarios, roles, protección contra intentos repetidos y hash `scrypt` de contraseñas. | ✅ |
| **2. Expedientes** | Crear, consultar, editar y archivar; cliente, tipo de proceso, estado y abogado responsable; búsqueda/filtros y acceso según permisos. | ✅ |
| **3. Documentos** | Carga, consulta y descarga autorizada; clasificación por tipo y sensibilidad; búsqueda por nombre/categoría/expediente; **tipo real validado al cargar por magic bytes** (lista blanca `txt/csv/png/jpg/pdf/zip`, configurable con `LEGALVAULT_EXTENSIONES_PERMITIDAS`): una extensión que no coincide con el contenido se rechaza con **422** y genera la alerta `documento_rechazado` más su registro denegado en auditoría; integridad por SHA-256 **re-verificada en cada descarga y bajo demanda** (`GET /documentos/{id}/verificar-integridad`, botón "Verificar" en la tabla): si el archivo en disco no coincide, la descarga se bloquea con **409** y se genera la alerta crítica `documento_corrupto` más su registro en auditoría. | ✅ |
| **4. Bóveda cifrada de doble fondo** | Contenido cifrado con **AES-256-GCM** y clave derivada con **scrypt**. Cada bóveda guarda **dos vistas independientes**: cada contraseña abre un contenido distinto, sin que la estructura almacenada revele cuál es cuál (negación plausible). | ✅ |
| **5. Permisos avanzados por expediente** | Matriz granular por usuario y acción (`leer`, `cargar`, `descargar`, `editar`, `eliminar`) que refina los permisos por defecto según rol y acceso; administrada por el administrador o el abogado responsable. | ✅ |
| **6. Auditoría formal** | Registro local **append-only** de todas las acciones relevantes (autenticación, CRUD, accesos denegados y acciones de bóveda), encadenado con **SHA-256** y verificable desde la interfaz; cualquier edición manual del archivo es detectable, y la página de auditoría **visualiza la cadena animada** (eslabones con hash truncado, barrido de verificación y resaltado del primer eslabón roto). | ✅ |
| **7. Alertas de seguridad** | Conteo de intentos fallidos, bloqueo temporal configurable, panel de alertas para el administrador (fecha, usuario y tipo, sin secretos). | ✅ |

Cada expediente admite una **matriz de permisos** (módulo 5) que refina, por
usuario y acción, los permisos derivados del rol y del acceso base. El
administrador y el abogado responsable conservan siempre el control total.

## Arquitectura (MVC + capa de servicios)

```
backend/
  app/
    models/        # M — entidades del dominio (dataclasses puras)
    repositories/  # M — acceso a datos (JSON, escritura atómica)
    services/      #   — lógica de negocio y reglas de seguridad
    controllers/   # C — routers HTTP (frontera de la API)
    schemas/       # V — contratos de entrada/salida (Pydantic)
    core/          # configuración, seguridad, contenedor de dependencias
  data/            # almacenamiento local en JSON + uploads/
  scripts/         # seed.py (datos demo) y smoke_test.py (pruebas E2E)

frontend/          # V — interfaz React (Vite)
  src/api/         # cliente HTTP centralizado (emite avisos globales de error)
  src/context/     # sesión (AuthContext) y notificaciones (ToastContext)
  src/components/  # layout, modal, tablas, insignias, toasts
  src/pages/       # login, panel, expedientes, documentos, bóveda, usuarios, alertas, auditoría, 404
  src/utils/       # bus de notificaciones y formato de fechas
  tests/           # pruebas de interfaz (Vitest + React Testing Library)
```

Reglas de diseño:

- El controlador **no** contiene lógica de negocio: solo valida la frontera HTTP
  y delega en los servicios.
- Los permisos se comprueban **siempre en el servidor** (`services/permissions.py`).
- Las contraseñas se guardan con **scrypt** (salt aleatorio por usuario) y nunca
  se incluyen en respuestas ni en las alertas.
- Las escrituras en JSON son **atómicas** (archivo temporal + `os.replace`).

## Requisitos

- Python 3.11+ (probado con 3.13 y 3.14)
- Node.js 18+ (probado con 22 y 24)
- Dependencias: `fastapi`, `uvicorn`, `python-multipart`, `PyJWT`, `pydantic`,
  `cryptography` (backend) y `react`, `react-dom`, `react-router-dom`, `vite`
  (frontend).

## Puesta en marcha

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# (Opcional) datos de demostración: usuarios, un expediente y documentos.
.\.venv\Scripts\python.exe -m scripts.seed

# Servidor de desarrollo
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- API: <http://127.0.0.1:8000>
- Documentación interactiva (Swagger): <http://127.0.0.1:8000/docs>

Al arrancar por primera vez se crea automáticamente el administrador inicial:

| Usuario | Contraseña | Rol |
| --- | --- | --- |
| `admin` | `Admin123!` | Administrador |
| `abogado.demo` | `Abogado123!` | Abogado (creado por `seed`) |
| `asistente.demo` | `Asistente123!` | Asistente jurídico (creado por `seed`) |

> Cambie estas credenciales y la clave `LEGALVAULT_SECRET_KEY` antes de
> cualquier uso real. Copie `backend/.env.example` como referencia.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Interfaz: <http://localhost:5173>. El proxy de Vite redirige `/api` al backend,
por lo que no hay problemas de CORS en desarrollo.

## Pruebas

Las pruebas requieren las dependencias de desarrollo (incluyen el cliente HTTP
`httpx2` que necesita el `TestClient` de Starlette). Instálelas una vez:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Prueba de humo integral de la API (usa un directorio temporal y no altera los
datos reales):

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.smoke_test
```

Cubre autenticación, gestión de usuarios, expedientes, documentos (incluido el
límite de sensibilidad por rol y la **re-verificación de integridad SHA-256**:
descarga bloqueada con 409 y alerta crítica ante corrupción), permisos
granulares por expediente, bóveda de doble fondo, bloqueo por intentos
fallidos, alertas, auditoría (con verificación de la cadena de integridad) y
cierre de sesión.

Suite de pruebas automatizadas con **pytest**: primitivas de seguridad, validadores,
permisos, repositorio JSON, criptografía de la bóveda, API de los módulos 1, 2, 3 y
7, la matriz de permisos del módulo 5, la cadena de auditoría del módulo 6 y la
**re-verificación de integridad de documentos** (`tests/test_integridad_documentos.py`).

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Pruebas de interfaz con **Vitest + React Testing Library** (`frontend/tests/`):
la página 404 y el enrutamiento (con y sin sesión, más regresión de las rutas
conocidas), el sistema de toasts (apertura, cierre manual, auto-cierre,
deduplicación y límite visible), los avisos globales del cliente HTTP (sesión
expirada, backend inaccesible con mensaje amigable y error 5xx), el bus de
notificaciones y la **cadena de auditoría animada**
(`frontend/tests/cadenaAuditoria.test.jsx`: lógica de estados por eslabón, orden
cronológico, barrido de verificación, resaltado del primer eslabón roto y de los
posteriores como no confiables, modo de movimiento reducido, plegado de cadenas
largas, fallo de la verificación y regresión de la tabla).

```powershell
cd frontend
npm install
npm run test
```

> **Mejora #7 del plan (*Visualización animada de la cadena de auditoría*) ya
> implementada:** solo frontend, sin cambios en el backend ni en los datos.

## Configuración

Variables de entorno (ver `backend/.env.example`):

| Variable | Por defecto | Descripción |
| --- | --- | --- |
| `LEGALVAULT_SECRET_KEY` | `dev-secret-...` | Clave de firma de los tokens JWT. |
| `LEGALVAULT_MAX_INTENTOS` | `5` | Intentos fallidos antes de bloquear. |
| `LEGALVAULT_MINUTOS_BLOQUEO` | `15` | Duración del bloqueo temporal. |
| `LEGALVAULT_MINUTOS_TOKEN` | `60` | Caducidad de la sesión. |
| `LEGALVAULT_MAX_ARCHIVO_MB` | `25` | Tamaño máximo de documento. |
| `LEGALVAULT_EXTENSIONES_PERMITIDAS` | `.txt,.csv,.png,.jpg,.jpeg,.pdf,.zip` | Lista blanca de extensiones al subir (validación por magic bytes). |
| `LEGALVAULT_DATA_DIR` | `backend/data` | Carpeta de datos JSON. |

## Roles y permisos

| Acción | Administrador | Abogado | Asistente |
| --- | :-: | :-: | :-: |
| Gestionar usuarios y ver alertas | ✅ | ❌ | ❌ |
| Consultar la auditoría y verificar su integridad | ✅ | ❌ | ❌ |
| Consultar catálogo mínimo de usuarios | ✅ | ✅ | ❌ |
| Ver expedientes propios/asignados | ✅ (todos) | ✅ | ✅ |
| Crear expedientes | ✅ | ✅ | ❌ |
| Editar/archivar expedientes | ✅ (todos) | ✅ (solo los suyos) | ❌ |
| Administrar la matriz de permisos del expediente | ✅ (todos) | ✅ (solo los suyos) | ❌ |
| Recibir permisos granulares (leer/cargar/descargar/editar/eliminar) | ✅ | ✅ | ✅ (según matriz) |
| Cargar documentos en expedientes accesibles | ✅ | ✅ | ✅ |
| Cargar documentos **confidenciales** | ✅ | ✅ | ❌ |
| Descargar documentos permitidos | ✅ | ✅ | ✅ |
| Ver documentos **confidenciales** | ✅ | ✅ | ❌ |
| Crear bóvedas cifradas | ✅ | ✅ | ❌ |
| Ver/abrir bóvedas propias o de su expediente | ✅ (todas) | ✅ | ✅ |
| Eliminar una bóveda | ✅ (cualquiera) | ✅ (solo las propias) | ❌ |

> Aunque un administrador pueda **ver la existencia** de cualquier bóveda, no
> puede leer su contenido sin conocer alguna de sus contraseñas.

## Seguridad y límites

- Contraseñas de usuario con **scrypt** (N=2¹⁴, r=8, p=1), salt de 16 bytes e
  igualdad en tiempo constante.
- Tokens **JWT** con expiración y lista de revocación en memoria para el cierre
  de sesión. Al reiniciar el proceso, la lista se pierde (mejora futura:
  almacén persistente o refresh tokens).
- Bloqueo temporal de cuentas y registro de eventos sin contraseñas ni claves.
- **Auditoría formal (Módulo 6):** cada acción relevante se guarda en
  `data/auditoria.json` como un registro encadenado
  (`hash_actual = SHA256(hash_anterior + registro)`). El endpoint
  `GET /api/auditoria/verificar` recalcula la cadena completa y señala el primer
  registro alterado, por lo que editar, insertar, reordenar o borrar líneas del
  archivo a mano es detectable. Solo el administrador puede consultarla.
  La página de auditoría **visualiza la cadena eslabón a eslabón** (hash anterior
  y hash propio truncados por ambos extremos): al pulsar "Verificar cadena" un
  barrido recorre los eslabones y pinta el resultado —verde los válidos, **rojo
  el primer eslabón roto** y ámbar todo lo posterior (ya no confiable)—, con la
  animación desactivada si el sistema pide reducir el movimiento.
- **Permisos avanzados (Módulo 5):** cada expediente guarda una matriz
  `{usuario_id: {leer, cargar, descargar, editar, eliminar}}` que **refina** los
  permisos por defecto (el usuario autorizado puede leer/cargar/descargar; el
  responsable y el administrador conservan el control total). Solo el
  administrador o el responsable pueden modificarla (`PUT
  /api/expedientes/{id}/permisos`); tener la acción `editar` **no** permite
  administrar la matriz, para evitar la escalada de privilegios.
- **Bóveda de doble fondo (Módulo 4):** contenido cifrado con AES-256-GCM y clave
  derivada de la contraseña con scrypt (salt y nonce aleatorios por operación).
  Cada bóveda tiene dos vistas en **orden aleatorio** y sin etiquetas, de modo
  que el archivo no revela cuántos contenidos hay ni cuál corresponde a cada
  contraseña. Nunca se almacenan contraseñas ni claves.
- Almacenamiento local en JSON con escrituras atómicas: adecuado para un
  prototipo, **no** para producción (no hay cifrado del índice en reposo ni
  control de concurrencia multiusuario real).
- La protección de los documentos cargados se basa en permisos de la aplicación;
  los archivos no se cifran en disco. El contenido de la **bóveda del módulo 4**
  sí se cifra, y es independiente de los documentos.

## Límites conocidos de la negación plausible (Módulo 4)

Para un prototipo académico, la bóveda implementa la separación de dos vistas
con credenciales independientes, pero **no** pretende resistir a un adversario
con capacidad forense avanzada:

- Toda bóveda tiene exactamente dos vistas, por lo que el número de vistas es
  uniforme y no delata un "doble fondo" concreto.
- No se oculta el **tamaño** aproximado del contenido cifrado (los rellenos
  criptográficos a un tamaño fijo serían la mejora natural).
- El nombre y la descripción de la bóveda son metadatos en claro; no deben
  contener información comprometedora.

## Mejoras futuras

- Módulo 5: permisos avanzados configurables.
- Relleno a tamaño fijo en las vistas de la bóveda (mejor negación plausible).
- Base de datos real y almacén persistente para la revocación de tokens.
- Cifrado en reposo de los documentos y análisis avanzado de alertas.

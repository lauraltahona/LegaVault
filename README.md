# LegalVault

Aplicación para la gestión segura de expedientes jurídicos. Combina la
administración de casos y documentos con autenticación, control de acceso por
rol y alertas de seguridad.

> **Prototipo académico.** Usa datos ficticios. No debe emplearse con
> expedientes reales sin una evaluación de seguridad profesional.

## Módulos implementados

| Módulo | Descripción | Estado |
| --- | --- | --- |
| **1. Autenticación y usuarios** | Inicio/cierre de sesión, CRUD y desactivación de usuarios, roles, protección contra intentos repetidos y hash `scrypt` de contraseñas. | ✅ |
| **2. Expedientes** | Crear, consultar, editar y archivar; cliente, tipo de proceso, estado y abogado responsable; búsqueda/filtros y acceso según permisos. | ✅ |
| **3. Documentos** | Carga, consulta y descarga autorizada; clasificación por tipo y sensibilidad; búsqueda por nombre/categoría/expediente; integridad por SHA-256. | ✅ |
| **7. Alertas de seguridad** | Conteo de intentos fallidos, bloqueo temporal configurable, panel de alertas para el administrador (fecha, usuario y tipo, sin secretos). | ✅ |

Los módulos 4 (bóveda cifrada de doble fondo), 5 (permisos avanzados) y 6
(auditoría formal) quedan fuera de esta entrega. Aun así, se aplican controles
básicos de acceso (rol + expediente) en los módulos 2 y 3.

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
  src/api/         # cliente HTTP centralizado
  src/context/     # sesión (AuthContext)
  src/components/  # layout, modal, tablas, insignias
  src/pages/       # login, panel, expedientes, documentos, usuarios, alertas
```

Reglas de diseño:

- El controlador **no** contiene lógica de negocio: solo valida la frontera HTTP
  y delega en los servicios.
- Los permisos se comprueban **siempre en el servidor** (`services/permissions.py`).
- Las contraseñas se guardan con **scrypt** (salt aleatorio por usuario) y nunca
  se incluyen en respuestas ni en las alertas.
- Las escrituras en JSON son **atómicas** (archivo temporal + `os.replace`).

## Requisitos

- Python 3.11+ (probado con 3.13)
- Node.js 18+ (probado con 22)
- Dependencias: `fastapi`, `uvicorn`, `python-multipart`, `PyJWT`, `pydantic`
  (backend) y `react`, `react-dom`, `react-router-dom`, `vite` (frontend).

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

Prueba de humo integral de la API (usa un directorio temporal y no altera los
datos reales):

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.smoke_test
```

Cubre autenticación, gestión de usuarios, expedientes, documentos (incluido el
límite de sensibilidad por rol), bloqueo por intentos fallidos, alertas y
cierre de sesión.

## Configuración

Variables de entorno (ver `backend/.env.example`):

| Variable | Por defecto | Descripción |
| --- | --- | --- |
| `LEGALVAULT_SECRET_KEY` | `dev-secret-...` | Clave de firma de los tokens JWT. |
| `LEGALVAULT_MAX_INTENTOS` | `5` | Intentos fallidos antes de bloquear. |
| `LEGALVAULT_MINUTOS_BLOQUEO` | `15` | Duración del bloqueo temporal. |
| `LEGALVAULT_MINUTOS_TOKEN` | `60` | Caducidad de la sesión. |
| `LEGALVAULT_MAX_ARCHIVO_MB` | `25` | Tamaño máximo de documento. |
| `LEGALVAULT_DATA_DIR` | `backend/data` | Carpeta de datos JSON. |

## Roles y permisos

| Acción | Administrador | Abogado | Asistente |
| --- | :-: | :-: | :-: |
| Gestionar usuarios y ver alertas | ✅ | ❌ | ❌ |
| Consultar catálogo mínimo de usuarios | ✅ | ✅ | ❌ |
| Ver expedientes propios/asignados | ✅ (todos) | ✅ | ✅ |
| Crear/editar/archivar expedientes | ✅ | ✅ | ❌ |
| Cargar/descargar documentos | ✅ | ✅ | ✅ |
| Ver documentos **confidenciales** | ✅ | ✅ | ❌ |

## Seguridad y límites

- Contraseñas de usuario con **scrypt** (N=2¹⁴, r=8, p=1), salt de 16 bytes e
  igualdad en tiempo constante.
- Tokens **JWT** con expiración y lista de revocación en memoria para el cierre
  de sesión. Al reiniciar el proceso, la lista se pierde (mejora futura:
  almacén persistente o refresh tokens).
- Bloqueo temporal de cuentas y registro de eventos sin contraseñas ni claves.
- Almacenamiento local en JSON con escrituras atómicas: adecuado para un
  prototipo, **no** para producción (no hay cifrado en reposo ni control de
  concurrencia multiusuario real).
- La protección de los documentos cargados se basa en permisos de la aplicación;
  los archivos no se cifran en disco (eso correspondería al módulo 4).

## Mejoras futuras

- Módulo 4: bóveda cifrada de doble fondo (AES-GCM + derivación de clave).
- Módulo 6: auditoría formal encadenada e inalterable.
- Base de datos real y almacén persistente para la revocación de tokens.
- Cifrado en reposo de los documentos y análisis avanzado de alertas.

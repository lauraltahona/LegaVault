# LegalVault — Sistema seguro de gestión de expedientes jurídicos

## 1. Descripción del proyecto

**LegalVault** es una aplicación orientada a abogados y despachos jurídicos que necesitan organizar y proteger documentos relacionados con sus casos. La plataforma combina funciones básicas de gestión de expedientes con mecanismos de seguridad informática y criptografía.

Su característica principal es una **bóveda cifrada con dos niveles de contenido**, inspirada en el concepto de *negación plausible*. Al desbloquear una bóveda, una contraseña permite acceder al conjunto de contenido visible y otra al conjunto confidencial. El objetivo es evitar que la estructura del archivo revele de forma evidente la existencia de información adicional.

La negación plausible no garantiza que sea imposible descubrir la existencia de datos ocultos. La protección real dependerá del diseño criptográfico, la implementación y las posibles evidencias que deje el sistema operativo o la aplicación.

## 2. Problema que aborda

Los profesionales del derecho manejan contratos, demandas, declaraciones, pruebas, datos personales y otros documentos que pueden contener información sensible. Una protección basada únicamente en organizar archivos en carpetas o utilizar una contraseña convencional puede ser insuficiente ante accesos no autorizados.

LegalVault propone centralizar la organización de expedientes y aplicar controles de acceso y cifrado para reducir el riesgo de exposición de la información.

## 3. Objetivo general

Desarrollar una aplicación para gestionar expedientes jurídicos y proteger sus documentos mediante autenticación, permisos de acceso, auditoría y una bóveda cifrada que implemente el concepto de negación plausible.

## 4. Usuarios del sistema

- **Administrador:** gestiona las cuentas, asigna roles y revisa los registros de actividad.
- **Abogado:** crea y administra los expedientes a los que tiene permiso, y protege sus documentos.
- **Asistente jurídico (opcional):** realiza tareas limitadas, como organizar o cargar documentos autorizados, sin acceso automático a todo el contenido confidencial.

## 5. Módulos de la aplicación

### Módulo 1. Autenticación y gestión de usuarios

Permite iniciar y cerrar sesión y administrar las cuentas del sistema.

Funciones:
- Inicio y cierre de sesión.
- Creación, edición y desactivación de usuarios.
- Asignación de roles.
- Protección contra intentos repetidos de inicio de sesión.
- Almacenamiento seguro de contraseñas mediante funciones de hash adecuadas; nunca guardarlas en texto plano.

### Módulo 2. Gestión de expedientes jurídicos

Permite organizar la información de los casos atendidos por el despacho.

Funciones:
- Crear, consultar, editar y archivar expedientes.
- Registrar un identificador, asunto, tipo de proceso, estado y abogado responsable.
- Asociar un cliente al expediente.
- Buscar y filtrar expedientes.
- Limitar el acceso según el usuario y sus permisos.

Para una demostración académica, se pueden utilizar clientes y expedientes ficticios.

### Módulo 3. Gestión de documentos

Permite añadir y organizar archivos asociados a cada expediente.

Funciones:
- Cargar y consultar documentos autorizados.
- Asociar documentos a un expediente.
- Clasificar documentos por tipo y nivel de sensibilidad.
- Buscar documentos por nombre, categoría o expediente.
- Descargar documentos después de comprobar los permisos correspondientes.

### Módulo 4. Bóveda cifrada de doble fondo

Es el módulo central y diferenciador del proyecto. Permite crear una bóveda que contenga dos conjuntos de datos protegidos.

Funciones:
- Crear una bóveda y asignar una contraseña para el contenido visible y otra para el contenido confidencial.
- Cifrar los contenidos antes de almacenarlos.
- Desbloquear la bóveda usando la contraseña correspondiente.
- Mostrar el conjunto de documentos asociado a la contraseña válida.
- Verificar la integridad de los datos y detectar contraseñas incorrectas o contenido alterado.
- Cambiar las credenciales y actualizar el cifrado de forma segura.

**Ejemplo de demostración:**
- Contraseña A: muestra plantillas y documentos administrativos de ejemplo.
- Contraseña B: muestra documentos confidenciales ficticios, como una declaración o una evidencia.

La aplicación no debe guardar las contraseñas directamente dentro de la bóveda ni incluirlas en registros de auditoría. El diseño criptográfico debe evitar que el contenido confidencial quede expuesto por metadatos, nombres de archivos o mensajes de error. Para un prototipo académico se debe documentar qué amenazas cubre y cuáles no.

### Módulo 5. Control de acceso y permisos

Define qué usuarios pueden consultar o modificar cada expediente y sus documentos.

Funciones:
- Aplicar permisos según el rol.
- Asignar abogados responsables a expedientes.
- Restringir lectura, carga, descarga, edición y eliminación.
- Aplicar el principio de mínimo privilegio: cada usuario recibe solo los permisos necesarios.
- Comprobar los permisos en el servidor, no solamente ocultar opciones en la interfaz.

### Módulo 6. Auditoría y registro de actividad

Registra eventos relevantes para facilitar la revisión de acciones dentro del sistema.

Funciones:
- Registrar inicios de sesión exitosos y fallidos.
- Registrar creación, edición y archivo de expedientes.
- Registrar cargas y descargas de documentos.
- Registrar intentos de acceso denegados y eventos de seguridad.
- Permitir al administrador consultar los registros.

Los registros no deben incluir contraseñas, claves criptográficas ni contenido de documentos. La auditoría debe protegerse contra modificaciones no autorizadas.

### Módulo 7. Alertas de seguridad

Ayuda a identificar patrones de acceso potencialmente sospechosos.

Funciones:
- Contabilizar intentos fallidos de inicio de sesión.
- Bloquear temporalmente una cuenta después de un límite configurable de intentos.
- Mostrar alertas al administrador.
- Consultar fecha, usuario y tipo de evento, evitando exponer secretos en los registros.

## 6. Flujo básico de uso

1. El usuario inicia sesión.
2. El sistema verifica su identidad y sus permisos.
3. El abogado crea un expediente o abre uno autorizado.
4. Carga y clasifica los documentos del caso.
5. Si necesita proteger información especialmente sensible, crea una bóveda de doble fondo.
6. La aplicación cifra ambos conjuntos de contenido.
7. Al desbloquear la bóveda, el sistema presenta el contenido correspondiente a la contraseña introducida.
8. Las acciones relevantes quedan registradas en la auditoría.

## 7. Conceptos de seguridad y criptografía

El proyecto puede demostrar y explicar:
- Cifrado simétrico, por ejemplo AES-GCM.
- Derivación de claves desde contraseñas mediante una función adecuada, como Argon2id o PBKDF2.
- Uso de salt y nonce/IV según los requisitos del algoritmo.
- Verificación de integridad y autenticidad de los datos cifrados.
- Hash seguro de contraseñas de las cuentas.
- Autenticación, autorización y principio de mínimo privilegio.
- Registro y análisis de eventos de seguridad.
- Limitaciones de la negación plausible.

La implementación debe usar bibliotecas criptográficas reconocidas y parámetros recomendados, en lugar de inventar algoritmos propios.

## 8. Alcance recomendado para la versión académica

Para mantener el proyecto realizable, la primera versión debería incluir:

1. Inicio de sesión y roles básicos.
2. CRUD de expedientes.
3. Carga y organización de documentos.
4. Bóveda cifrada de doble fondo.
5. Permisos de acceso por expediente.
6. Auditoría básica de acciones.

Las alertas avanzadas, el rol de asistente, la eliminación segura y otras funciones pueden quedar como mejoras futuras.

## 9. Consideraciones y límites

- La aplicación es un prototipo académico y no debe utilizarse con expedientes reales sin una evaluación de seguridad profesional.
- La negación plausible no equivale a una garantía absoluta de que no se pueda detectar información oculta.
- El cifrado de la bóveda no protege automáticamente archivos temporales, copias de seguridad, capturas de pantalla, memoria del dispositivo o documentos exportados fuera de la aplicación.
- Deben usarse datos ficticios en las pruebas y evitar almacenar secretos en logs.
- La solución no sustituye las obligaciones profesionales, legales y de protección de datos que correspondan al despacho.

## 10. Resumen

**LegalVault** es una aplicación de gestión segura de expedientes jurídicos cuyo elemento diferenciador es una bóveda cifrada de doble fondo. Combina administración de casos y documentos con autenticación, permisos, auditoría y alertas básicas. Así, el proyecto aplica conceptos de criptografía y seguridad informática a un escenario de uso específico: la protección de información jurídica sensible.

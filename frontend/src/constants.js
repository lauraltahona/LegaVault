// Etiquetas legibles para los valores de los enumerados del backend.

export const ROLES = {
  admin: 'Administrador',
  abogado: 'Abogado',
  asistente: 'Asistente jurídico',
}

export const ESTADOS_EXPEDIENTE = {
  abierto: 'Abierto',
  en_tramite: 'En trámite',
  suspendido: 'Suspendido',
  cerrado: 'Cerrado',
  archivado: 'Archivado',
}

export const TIPOS_PROCESO = {
  civil: 'Civil',
  penal: 'Penal',
  laboral: 'Laboral',
  mercantil: 'Mercantil',
  familia: 'Familia',
  administrativo: 'Administrativo',
  otro: 'Otro',
}

export const TIPOS_DOCUMENTO = {
  contrato: 'Contrato',
  demanda: 'Demanda',
  declaracion: 'Declaración',
  prueba: 'Prueba',
  poder: 'Poder',
  resolucion: 'Resolución',
  otro: 'Otro',
}

export const NIVELES_SENSIBILIDAD = {
  publico: 'Público',
  interno: 'Interno',
  confidencial: 'Confidencial',
}

export const TIPOS_ALERTA = {
  login_exitoso: 'Inicio de sesión',
  login_fallido: 'Inicio de sesión fallido',
  cuenta_bloqueada: 'Cuenta bloqueada',
  cuenta_desbloqueada: 'Cuenta desbloqueada',
  acceso_denegado: 'Acceso denegado',
  usuario_creado: 'Usuario creado',
  usuario_editado: 'Usuario editado',
  usuario_desactivado: 'Usuario desactivado',
  expediente_creado: 'Expediente creado',
  expediente_editado: 'Expediente editado',
  expediente_archivado: 'Expediente archivado',
  documento_cargado: 'Documento cargado',
  documento_descargado: 'Documento descargado',
  documento_eliminado: 'Documento eliminado',
  documento_corrupto: 'Integridad de documento rota',
  documento_rechazado: 'Carga rechazada (tipo de archivo)',
  boveda_creada: 'Bóveda creada',
  boveda_abierta: 'Bóveda abierta',
  boveda_acceso_fallido: 'Acceso a bóveda fallido',
  boveda_editada: 'Bóveda editada',
  boveda_credenciales: 'Credenciales de bóveda',
  boveda_eliminada: 'Bóveda eliminada',
}

export const SEVERIDADES = {
  info: 'Informativa',
  advertencia: 'Advertencia',
  critica: 'Crítica',
}

export const RESULTADOS_AUDITORIA = {
  ok: 'Correcto',
  denegado: 'Denegado',
  error: 'Error',
}

export const ACCIONES_AUDITORIA = {
  login: 'Inicio de sesión',
  login_fallido: 'Inicio de sesión fallido',
  logout: 'Cierre de sesión',
  cuenta_bloqueada: 'Cuenta bloqueada',
  acceso_denegado: 'Acceso denegado',
  usuario_creado: 'Usuario creado',
  usuario_editado: 'Usuario editado',
  usuario_estado: 'Estado de usuario',
  usuario_password: 'Contraseña restablecida',
  usuario_desbloqueado: 'Usuario desbloqueado',
  expediente_creado: 'Expediente creado',
  expediente_editado: 'Expediente editado',
  expediente_archivado: 'Expediente archivado',
  documento_cargado: 'Documento cargado',
  documento_descargado: 'Documento descargado',
  documento_eliminado: 'Documento eliminado',
  documento_verificado: 'Integridad verificada',
  documento_corrupto: 'Integridad rota (SHA-256)',
  documento_rechazado: 'Carga rechazada (magic bytes)',
  boveda_creada: 'Bóveda creada',
  boveda_abierta: 'Bóveda abierta',
  boveda_acceso_fallido: 'Acceso a bóveda fallido',
  boveda_editada: 'Bóveda editada',
  boveda_credenciales: 'Credenciales de bóveda',
  boveda_eliminada: 'Bóveda eliminada',
  expediente_permisos: 'Permisos de expediente',
  auditoria_verificada: 'Auditoría verificada',
}

// Acciones de la matriz de permisos granular por expediente (Módulo 5).
export const ACCIONES_PERMISO = {
  leer: 'Leer',
  cargar: 'Cargar',
  descargar: 'Descargar',
  editar: 'Editar',
  eliminar: 'Eliminar',
}

// Lista blanca de extensiones admitidas al subir documentos (Módulo 3).
// El servidor valida el tipo REAL por magic bytes; esta lista guía al usuario
// y debe mantenerse en sincronía con LEGALVAULT_EXTENSIONES_PERMITIDAS.
export const EXTENSIONES_ARCHIVO_PERMITIDAS = [
  '.txt',
  '.csv',
  '.png',
  '.jpg',
  '.jpeg',
  '.pdf',
  '.zip',
]

// Valor para el atributo `accept` del input de tipo archivo.
export const ARCHIVO_ACCEPT = EXTENSIONES_ARCHIVO_PERMITIDAS.join(',')

// Convierte un objeto de etiquetas en una lista de opciones para <select>.
export function opciones(mapa) {
  return Object.entries(mapa).map(([valor, etiqueta]) => ({ valor, etiqueta }))
}

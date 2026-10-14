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
}

export const SEVERIDADES = {
  info: 'Informativa',
  advertencia: 'Advertencia',
  critica: 'Crítica',
}

// Convierte un objeto de etiquetas en una lista de opciones para <select>.
export function opciones(mapa) {
  return Object.entries(mapa).map(([valor, etiqueta]) => ({ valor, etiqueta }))
}

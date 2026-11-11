"""Excepciones del dominio.

Todas heredan de ``DominioError`` para que la capa de presentación pueda
capturarlas de forma uniforme y mostrar mensajes comprensibles al usuario.
"""


class DominioError(Exception):
    """Error base de las reglas de negocio."""


class ValidacionError(DominioError):
    """Los datos recibidos incumplen una regla de validación."""


class TransicionInvalidaError(DominioError):
    """Se intentó un cambio de estado fuera del flujo definido."""


class PermisoDenegadoError(DominioError):
    """El actor no tiene permiso para ejecutar la acción (RBAC)."""


class NoEncontradoError(DominioError):
    """El recurso solicitado no existe."""


class AutenticacionError(DominioError):
    """Credenciales inválidas o usuario inactivo."""


class EvidenciaInvalidaError(ValidacionError):
    """El archivo adjunto no es una imagen válida o excede el tamaño."""


class DuplicadoError(DominioError):
    """Ya existe un registro con el mismo identificador único."""

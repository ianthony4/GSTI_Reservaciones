"""Errores de negocio. La capa API los traduce a códigos HTTP."""


class BusinessError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(BusinessError):
    status_code = 404


class ForbiddenError(BusinessError):
    status_code = 403


class RuleViolationError(BusinessError):
    """Datos válidos en forma pero que incumplen una regla (horario, anticipación, capacidad)."""
    status_code = 422


class NoAvailabilityError(BusinessError):
    status_code = 409


class InvalidStateError(BusinessError):
    status_code = 409

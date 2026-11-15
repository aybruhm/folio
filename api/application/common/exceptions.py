class ApplicationError(Exception):
    pass


class ConflictError(ApplicationError):
    pass


class AuthenticationError(ApplicationError):
    pass

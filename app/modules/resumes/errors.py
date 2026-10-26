"""Erros do domínio, sem dependência de HTTP."""
class ResumeError(Exception):
    pass

class FileTooLargeError(ResumeError):
    pass

class UnsupportedFormatError(ResumeError):
    pass

class InvalidDocumentError(ResumeError):
    pass

class ProtectedDocumentError(ResumeError):
    pass

class NoTextFoundError(ResumeError):
    pass

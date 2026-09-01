class MemoryGuardError(Exception):
    """Base error for the MemoryGuard Module."""


class MemoryBackendUnavailable(MemoryGuardError):
    """The configured Sibyl Memory Adapter cannot serve the request."""


class MemoryIntegrityError(MemoryGuardError):
    """Persisted memory or a decision proof failed integrity checks."""


class MemoryConflictError(MemoryGuardError):
    """A concurrent or contradictory write requires a new review."""


class DecisionNotFoundError(MemoryGuardError):
    """The requested server-side decision does not exist."""


class FinalizationError(MemoryGuardError):
    """A decision could not be finalized safely."""

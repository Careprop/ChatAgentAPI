class AgentError(Exception):
    """Base for all agent-layer errors."""


class AgentConfigError(AgentError):
    """Provider is not configured (missing or empty API key)."""


class AgentAuthError(AgentError):
    """API key is invalid or lacks permissions."""


class AgentRateLimitError(AgentError):
    """Rate limit or quota exceeded on the provider side."""


class AgentTimeoutError(AgentError):
    """Request to the provider timed out."""


class AgentProviderError(AgentError):
    """Provider returned an error (connection failure, 5xx, bad model, etc.)."""

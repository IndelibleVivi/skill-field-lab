class FieldLabError(RuntimeError):
    """Base error for expected Field Lab failures."""


class ConfigError(FieldLabError):
    """A pack, case, plan, or CLI request violates the public contract."""


class ExecutionError(FieldLabError):
    """A bounded execution could not establish a trustworthy terminal state."""

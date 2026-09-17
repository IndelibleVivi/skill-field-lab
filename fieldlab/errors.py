class FieldLabError(RuntimeError):
    """Base error for expected Field Lab failures."""


class ConfigError(FieldLabError):
    """A pack, case, plan, or CLI request violates the public contract."""


class ExecutionError(FieldLabError):
    """A bounded execution could not establish a trustworthy terminal state."""


class EvidenceError(FieldLabError):
    """A bounded execution finished, but its evidence could not be constructed.

    The worker process already reached a trustworthy terminal state, so this is
    not a process-termination failure: no normal receipt may be sealed, and the
    attempt is recorded as an evidence-construction failure instead.
    """

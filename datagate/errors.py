class DataGateError(Exception):
    """Base error that is safe to present to a CLI user."""


class InputFormatError(DataGateError):
    """The input file is malformed or not a supported format."""


class ContractError(DataGateError):
    """A contract is malformed or uses unsupported rules."""

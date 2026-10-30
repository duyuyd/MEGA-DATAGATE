from __future__ import annotations

import hashlib
import math


class HybridCardinality:
    """Exact set for small columns; fixed-memory HyperLogLog after a threshold."""

    def __init__(self, exact_limit: int = 512, precision: int = 12) -> None:
        if exact_limit < 1 or not 4 <= precision <= 16:
            raise ValueError("exact_limit must be positive and precision must be between 4 and 16")
        self.exact_limit = exact_limit
        self.precision = precision
        self._exact: set[str] | None = set()
        self._registers: bytearray | None = None

    @staticmethod
    def _hash(value: str) -> int:
        digest = hashlib.blake2b(value.encode("utf-8", "surrogatepass"), digest_size=8).digest()
        return int.from_bytes(digest, "big")

    def _add_hll(self, value: str) -> None:
        assert self._registers is not None
        hashed = self._hash(value)
        width = 64 - self.precision
        index = hashed >> width
        remainder = hashed & ((1 << width) - 1)
        rank = width + 1 if remainder == 0 else (width - remainder.bit_length()) + 1
        if rank > self._registers[index]:
            self._registers[index] = rank

    def add(self, value: str) -> None:
        if self._exact is not None:
            self._exact.add(value)
            if len(self._exact) <= self.exact_limit:
                return
            previous = self._exact
            self._exact = None
            self._registers = bytearray(1 << self.precision)
            for item in previous:
                self._add_hll(item)
            return
        self._add_hll(value)

    @property
    def exact(self) -> bool:
        return self._exact is not None

    def estimate(self) -> int:
        if self._exact is not None:
            return len(self._exact)
        assert self._registers is not None
        m = len(self._registers)
        alpha = 0.7213 / (1.0 + 1.079 / m)
        raw = alpha * m * m / sum(2.0 ** (-register) for register in self._registers)
        zeros = self._registers.count(0)
        if raw <= 2.5 * m and zeros:
            raw = m * math.log(m / zeros)
        return max(0, int(round(raw)))

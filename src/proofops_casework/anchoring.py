from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable

import httpx

from .core import CaseworkError

ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")
ROOT = re.compile(r"^[0-9a-f]{64}$")


class BaseAuditAnchor:
    """Zero-value audit plans and independent RPC checks; never signs/broadcasts.

    A verified anchor attests a digest, NOT that the risk facts are true or the
    underlying payment is authorized. Confirmation count is not absolute finality.
    """
    def __init__(self, *, chain_id: int, contract: str, expected_attester: str,
                 rpc_url: str, confirmations: int = 2, rpc: Callable | None = None,
                 test_hasher: Callable | None = None, test_mode: bool = False):
        if chain_id not in {8453, 84532}:
            raise ValueError("Only Base or Base Sepolia is supported")
        if (not ADDRESS.fullmatch(contract) or not ADDRESS.fullmatch(expected_attester)
                or int(contract, 16) == 0 or int(expected_attester, 16) == 0):
            raise ValueError("non-zero contract and attester addresses required")
        if not 1 <= confirmations <= 128 or not rpc_url.startswith("https://"):
            raise ValueError("HTTPS RPC and bounded positive confirmations required")
        if (rpc is not None or test_hasher is not None) and not test_mode:
            raise ValueError("test RPC/hash injection is not allowed in production")
        if test_hasher is not None:
            hasher = test_hasher
        else:
            from eth_utils import keccak
            hasher = lambda value: keccak(text=value)
        self.chain_id = chain_id
        self.contract = contract.lower()
        self.expected_attester = expected_attester.lower()
        self.rpc_url = rpc_url
        self.confirmations = confirmations
        self._transport = rpc
        self.selector = hasher("anchor(bytes32,uint64)")[:4].hex()
        self.event_topic = "0x" + hasher("MemoryProofAnchored(bytes32,address,uint64,uint64)").hex()

    def _rpc(self, method: str, params: list):
        if self._transport is not None:
            return self._transport(method, params)
        response = httpx.post(self.rpc_url, json={"jsonrpc": "2.0", "id": 1,
                              "method": method, "params": params}, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or data.get("error") or "result" not in data:
            raise CaseworkError("ANCHOR_RPC_ERROR", 503)
        return data["result"]

    def plan(self, proof_root: str, memory_version: int, chain_id: int) -> dict:
        if (not ROOT.fullmatch(proof_root) or type(memory_version) is not int
                or not 1 <= memory_version < 2**64 or chain_id != self.chain_id):
            raise CaseworkError("ANCHOR_PROOF_OR_CHAIN_INVALID", 422)
        return {"chain_id": self.chain_id, "to": self.contract, "value": "0x0",
                "data": "0x" + self.selector + proof_root + f"{memory_version:064x}",
                "proof_root": proof_root, "memory_version": memory_version,
                "expected_attester": self.expected_attester, "audit_only": True,
                "human_wallet_confirmation_required": True}

    def verify(self, plan: dict, tx_hash: str) -> dict:
        if not HASH.fullmatch(tx_hash):
            raise CaseworkError("INVALID_TRANSACTION_HASH", 422)
        expected_plan = self.plan(plan["proof_root"], plan["memory_version"], plan["chain_id"])
        if expected_plan != plan:
            raise CaseworkError("ANCHOR_PLAN_TAMPERED", 503)
        try:
            if int(self._rpc("eth_chainId", []), 16) != self.chain_id:
                raise CaseworkError("ANCHOR_RPC_CHAIN_MISMATCH", 422)
            receipt = self._rpc("eth_getTransactionReceipt", [tx_hash])
            if receipt is None:
                return {"state": "PENDING", "tx_hash": tx_hash, "audit_only": True}
            if (str(receipt.get("transactionHash", "")).lower() != tx_hash.lower()
                    or receipt.get("status") != "0x1"
                    or str(receipt.get("to", "")).lower() != self.contract
                    or str(receipt.get("from", "")).lower() != self.expected_attester):
                raise CaseworkError("ANCHOR_RECEIPT_BINDING_FAILED", 422)
            transaction = self._rpc("eth_getTransactionByHash", [tx_hash])
            if (not isinstance(transaction, dict)
                    or str(transaction.get("to", "")).lower() != self.contract
                    or str(transaction.get("from", "")).lower() != self.expected_attester
                    or str(transaction.get("input", "")).lower() != plan["data"].lower()
                    or int(transaction.get("value", "0x1"), 16) != 0):
                raise CaseworkError("ANCHOR_CALLDATA_OR_VALUE_MISMATCH", 422)
            attester_topic = "0x" + self.expected_attester[2:].rjust(64, "0")
            matched = False
            for log in receipt.get("logs", []):
                topics = log.get("topics", [])
                data = log.get("data", "")
                if (str(log.get("address", "")).lower() == self.contract
                        and not log.get("removed", False)
                        and [str(value).lower() for value in topics] == [self.event_topic.lower(),
                            "0x" + plan["proof_root"], attester_topic]
                        and isinstance(data, str) and re.fullmatch(r"0x[0-9a-fA-F]{128}", data)
                        and int(data[2:66], 16) == plan["memory_version"]):
                    matched = True
            if not matched:
                raise CaseworkError("ANCHOR_EVENT_MISMATCH", 422)
            block_number = int(receipt["blockNumber"], 16)
            block_hash = receipt["blockHash"]
            if block_number <= 0 or not HASH.fullmatch(block_hash):
                raise CaseworkError("ANCHOR_BLOCK_INVALID", 422)
            canonical = self._rpc("eth_getBlockByNumber", [hex(block_number), False])
            if not canonical or str(canonical.get("hash", "")).lower() != block_hash.lower():
                raise CaseworkError("ANCHOR_BLOCK_NOT_CANONICAL", 409)
            seen = int(self._rpc("eth_blockNumber", []), 16) - block_number + 1
            if seen < self.confirmations:
                return {"state": "PENDING", "tx_hash": tx_hash, "confirmations": max(0, seen), "audit_only": True}
            return {"state": "VERIFIED", "tx_hash": tx_hash, "chain_id": self.chain_id,
                    "contract": self.contract, "attester": self.expected_attester,
                    "block_number": block_number, "block_hash": block_hash,
                    "confirmations_at_verification": seen, "minimum_confirmations": self.confirmations,
                    "proof_root": plan["proof_root"], "memory_version": plan["memory_version"],
                    "verified_at": datetime.now(timezone.utc).isoformat(), "audit_only": True,
                    "partner_bonus_awarded": False, "economic_action_authorized": False}
        except CaseworkError:
            raise
        except Exception as exc:
            raise CaseworkError("ANCHOR_VERIFICATION_UNAVAILABLE", 503) from exc

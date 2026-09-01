from __future__ import annotations

import re
from typing import Any

import httpx
from eth_utils import keccak

from ..errors import FinalizationError
from ..models import AnchorPlan, AnchorState, AnchorVerification, DecisionDraft

_ADDRESS = re.compile(r"^0x[a-fA-F0-9]{40}$")
_TX_HASH = re.compile(r"^0x[a-fA-F0-9]{64}$")


class DisabledAnchorAdapter:
    def plan(self, decision: DecisionDraft) -> AnchorPlan | None:
        del decision
        return None

    def verify(self, decision: DecisionDraft, tx_hash: str) -> AnchorVerification:
        del decision, tx_hash
        return AnchorVerification(
            state=AnchorState.FAILED,
            tx_hash=None,
            chain_id=None,
            contract=None,
            block_number=None,
            reason_codes=("base_anchor_not_configured",),
        )


class BaseAnchorAdapter:
    """Creates wallet plans and independently verifies MemoryProofAnchor receipts."""

    _FUNCTION_SIGNATURE = "anchor(bytes32,uint64)"
    _EVENT_SIGNATURE = "MemoryProofAnchored(bytes32,address,uint64,uint64)"

    def __init__(
        self,
        *,
        chain_id: int,
        network: str,
        rpc_url: str,
        contract: str,
        timeout_seconds: float = 10,
    ) -> None:
        if chain_id not in {8453, 84532}:
            raise ValueError("MemoryGuard Base anchor only supports chain 8453 or 84532")
        if not _ADDRESS.fullmatch(contract):
            raise ValueError("BASE_ANCHOR_ADDRESS must be a 20-byte EVM address")
        self._chain_id = chain_id
        self._network = network
        self._rpc_url = rpc_url
        self._contract = contract.lower()
        self._timeout = timeout_seconds

    @staticmethod
    def _selector(signature: str) -> str:
        return keccak(text=signature)[:4].hex()

    def plan(self, decision: DecisionDraft) -> AnchorPlan:
        if decision.intent.chain_id != self._chain_id:
            raise FinalizationError("decision chain does not match configured Base anchor chain")
        root = bytes.fromhex(decision.proof_root)
        version = decision.memory_version.to_bytes(32, byteorder="big", signed=False)
        data = "0x" + self._selector(self._FUNCTION_SIGNATURE) + root.hex() + version.hex()
        return AnchorPlan(
            chain_id=self._chain_id,
            network=self._network,
            contract=self._contract,
            to=self._contract,
            data=data,
            value="0x0",
            proof_root=decision.proof_root,
        )

    def _rpc(self, method: str, params: list[Any]) -> Any:
        response = httpx.post(
            self._rpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=self._timeout,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("error"):
            raise RuntimeError(str(body["error"].get("message", "Base RPC error")))
        return body.get("result")

    def _matches_anchor_event(
        self,
        log: dict[str, Any],
        decision: DecisionDraft,
        event_topic: str,
        receipt_from: str,
    ) -> bool:
        topics = log.get("topics", [])
        data = str(log.get("data", ""))
        if not data.startswith("0x") or len(data) < 66 or len(topics) < 3:
            return False
        try:
            memory_version = int(data[2:66], 16)
            event_attester = f"0x{str(topics[2]).removeprefix('0x')[-40:]}".lower()
        except ValueError:
            return False
        return (
            str(log.get("address", "")).lower() == self._contract
            and str(topics[0]).lower() == event_topic.lower()
            and str(topics[1]).lower() == f"0x{decision.proof_root}".lower()
            and event_attester == receipt_from
            and memory_version == decision.memory_version
        )

    def verify(self, decision: DecisionDraft, tx_hash: str) -> AnchorVerification:
        if decision.intent.chain_id != self._chain_id:
            return AnchorVerification(
                AnchorState.FAILED,
                tx_hash,
                self._chain_id,
                self._contract,
                None,
                ("decision_chain_does_not_match_anchor_chain",),
            )
        if not _TX_HASH.fullmatch(tx_hash):
            return AnchorVerification(
                AnchorState.FAILED,
                tx_hash,
                self._chain_id,
                self._contract,
                None,
                ("invalid_transaction_hash",),
            )
        try:
            actual_chain = int(str(self._rpc("eth_chainId", [])), 16)
            if actual_chain != self._chain_id:
                raise ValueError("rpc_chain_mismatch")
            receipt = self._rpc("eth_getTransactionReceipt", [tx_hash])
            if receipt is None:
                return AnchorVerification(
                    AnchorState.PENDING,
                    tx_hash,
                    self._chain_id,
                    self._contract,
                    None,
                    ("receipt_not_yet_available",),
                )
            if str(receipt.get("status", "0x0")).lower() != "0x1":
                raise ValueError("transaction_reverted")
            if str(receipt.get("to", "")).lower() != self._contract:
                raise ValueError("receipt_contract_mismatch")
            receipt_from = str(receipt.get("from", "")).lower()
            if not _ADDRESS.fullmatch(receipt_from):
                raise ValueError("receipt_sender_missing_or_invalid")
            event_topic = "0x" + keccak(text=self._EVENT_SIGNATURE).hex()
            matched = any(
                self._matches_anchor_event(log, decision, event_topic, receipt_from)
                for log in receipt.get("logs", [])
            )
            if not matched:
                raise ValueError("matching_root_version_and_attester_event_not_found")
            return AnchorVerification(
                AnchorState.VERIFIED,
                tx_hash,
                self._chain_id,
                self._contract,
                int(str(receipt["blockNumber"]), 16),
                ("base_receipt_root_memory_version_and_attester_verified",),
            )
        except Exception as exc:  # noqa: BLE001
            return AnchorVerification(
                AnchorState.FAILED,
                tx_hash,
                self._chain_id,
                self._contract,
                None,
                (str(exc) or type(exc).__name__,),
            )

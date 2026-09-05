from __future__ import annotations

import hashlib
import json
import re

from ..core import CaseworkError
from .http_client import BoundedHTTP

HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")


class BaseTransactionSource:
    def __init__(self, http=None):
        self.http = http or BoundedHTTP()

    @staticmethod
    def resource(spec, resource: str, scope):
        if not HASH.fullmatch(resource) or scope.chain_id != spec.chain_id:
            raise CaseworkError("BASE_RESOURCE_SCOPE_INVALID", 403)
        return resource.lower()

    def fetch(self, spec, resource: str, scope, at):
        txid = self.resource(spec, resource, scope)
        samples = []
        def rpc(method, args):
            body, _ = self.http.json("POST", spec.rpc_url,
                payload={"jsonrpc": "2.0", "id": 1, "method": method, "params": args})
            if body.get("error") or body.get("id") != 1 or body.get("jsonrpc") != "2.0":
                raise CaseworkError("SOURCE_RPC_FAILURE", 502)
            samples.append(body.get("result"))
            return body.get("result")
        try:
            if int(rpc("eth_chainId", []), 16) != spec.chain_id:
                raise CaseworkError("SOURCE_CHAIN_MISMATCH", 502)
            receipt = rpc("eth_getTransactionReceipt", [txid])
            if receipt is None:
                raise CaseworkError("SOURCE_TRANSACTION_PENDING", 409)
            tx = rpc("eth_getTransactionByHash", [txid])
            if (not isinstance(tx, dict) or not isinstance(receipt, dict)
                    or tx.get("hash", "").lower() != txid
                    or receipt.get("transactionHash", "").lower() != txid
                    or tx.get("to", "").lower() != scope.target
                    or receipt.get("to", "").lower() != scope.target
                    or tx.get("from", "").lower() != receipt.get("from", "").lower()
                    or tx.get("blockHash") != receipt.get("blockHash")
                    or tx.get("blockNumber") != receipt.get("blockNumber")):
                raise CaseworkError("SOURCE_TRANSACTION_BINDING_FAILED", 502)
            if (not re.fullmatch(r"0x[0-9a-fA-F]{40}", receipt.get("from", ""))
                    or not HASH.fullmatch(receipt.get("blockHash", ""))):
                raise CaseworkError("SOURCE_TRANSACTION_BINDING_FAILED", 502)
            block_no = int(receipt["blockNumber"], 16)
            block = rpc("eth_getBlockByNumber", [receipt["blockNumber"], False])
            head = int(rpc("eth_blockNumber", []), 16)
            if not block or block.get("hash") != receipt["blockHash"] or int(block["number"],16) != block_no:
                raise CaseworkError("SOURCE_REORG_DETECTED", 409)
            confirmations = head - block_no + 1
            if confirmations < spec.min_confirmations:
                raise CaseworkError("SOURCE_CONFIRMATIONS_INSUFFICIENT", 409)
            status = int(receipt["status"], 16)
            if status not in {0, 1} or int(tx["value"], 16) < 0:
                raise ValueError("unknown tx status")
            facts = {"chain_id": spec.chain_id, "tx_hash": txid, "to": scope.target,
                     "from": receipt["from"].lower(), "block_number": block_no,
                     "block_hash": receipt["blockHash"], "confirmations": confirmations,
                     "transaction_succeeded": status == 1, "value_wei": str(int(tx["value"], 16))}
            return {"facts": facts,
                    "payload_sha256": hashlib.sha256(json.dumps(samples, sort_keys=True).encode()).hexdigest(),
                    "provenance": "BASE_RPC_OBSERVED", "external_calls": 5,
                    "claim_boundary": "RPC observation at fetch time; not perpetual finality or business authorization"}
        except CaseworkError:
            raise
        except Exception as exc:
            raise CaseworkError("SOURCE_RPC_SCHEMA_INVALID", 502) from exc

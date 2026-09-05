"""RPC logic tests use a TEST hash function, not an EVM/chain integration."""
import copy
import hashlib

import pytest

from proofops_casework.anchoring import BaseAuditAnchor
from proofops_casework.core import CaseworkError
from .support import Harness


def configured():
    answers={}
    anchor=BaseAuditAnchor(chain_id=84532,contract="0x"+"1"*40,
        expected_attester="0x"+"2"*40,rpc_url="https://rpc.invalid",
        rpc=lambda method,params: copy.deepcopy(answers[method]),
        test_hasher=lambda s:hashlib.sha256(s.encode()).digest(),test_mode=True)
    plan=anchor.plan("a"*64,3,84532);tx="0x"+"3"*64;block="0x"+"4"*64
    answers.update({"eth_chainId":hex(84532),"eth_blockNumber":hex(101),
        "eth_getBlockByNumber":{"hash":block},
        "eth_getTransactionByHash":{"from":anchor.expected_attester,"to":anchor.contract,
            "input":plan["data"],"value":"0x0","hash":tx,"blockNumber":hex(100),"blockHash":block},
        "eth_getTransactionReceipt":{"transactionHash":tx,"status":"0x1","to":anchor.contract,
            "from":anchor.expected_attester,"blockNumber":hex(100),"blockHash":block,
            "logs":[{"address":anchor.contract,"topics":[anchor.event_topic,"0x"+plan["proof_root"],
                "0x"+anchor.expected_attester[2:].rjust(64,"0")],"data":"0x"+f"{3:064x}{1000:064x}"}]}})
    return anchor,answers,plan,tx


def test_receipt_exact_binding_and_confirmations():
    a,r,p,tx=configured();out=a.verify(p,tx)
    assert out["state"]=="VERIFIED"
    assert out["partner_bonus_awarded"] is False
    assert out["economic_action_authorized"] is False
    r["eth_blockNumber"]=hex(100)
    assert a.verify(p,tx)["state"]=="PENDING"
    r["eth_getTransactionReceipt"]=None
    assert a.verify(p,tx)["state"]=="PENDING"


@pytest.mark.parametrize("problem",["chain","sender","contract","tx_hash","reverted","value",
                                   "calldata","root","version","attester","removed","reorg"])
def test_bad_receipts_cannot_be_marked_verified(problem):
    a,r,p,tx=configured();receipt=r["eth_getTransactionReceipt"]
    if problem=="chain": r["eth_chainId"]=hex(8453)
    if problem=="sender": receipt["from"]="0x"+"9"*40
    if problem=="contract": receipt["to"]="0x"+"9"*40
    if problem=="tx_hash": receipt["transactionHash"]="0x"+"9"*64
    if problem=="reverted": receipt["status"]="0x0"
    if problem=="value": r["eth_getTransactionByHash"]["value"]="0x1"
    if problem=="calldata": r["eth_getTransactionByHash"]["input"]="0x00"
    if problem=="root": receipt["logs"][0]["topics"][1]="0x"+"9"*64
    if problem=="version": receipt["logs"][0]["data"]="0x"+f"{4:064x}{1000:064x}"
    if problem=="attester": receipt["logs"][0]["topics"][2]="0x"+"9"*64
    if problem=="removed": receipt["logs"][0]["removed"]=True
    if problem=="reorg": r["eth_getBlockByNumber"]["hash"]="0x"+"9"*64
    with pytest.raises(CaseworkError): a.verify(p,tx)


def test_plan_cannot_move_value_and_rejects_wrong_chain():
    a,r,p,tx=configured();assert p["value"]=="0x0"
    with pytest.raises(CaseworkError): a.plan("a"*64,3,8453)
    changed=p|{"value":"0x1"}
    with pytest.raises(CaseworkError,match="PLAN_TAMPERED"): a.verify(changed,tx)


def test_v2_anchor_reads_stored_decision_and_preserves_denial():
    a,r,p,tx=configured();h=Harness();h.svc.anchor=a;h.baseline()
    tid=h.task()["task"]["task_id"];h.risk();d=h.evaluate(tid)
    result=h.svc.prepare_anchor(h.actors["reviewer"],h.command(),tid,d["decision_id"])
    plan=result["anchor"]["plan"]
    assert plan["proof_root"]==d["proof_root"]
    assert result["payment_authorized"] is False
    assert h.store.load("tenant_demo").tasks[tid].status=="DENY"

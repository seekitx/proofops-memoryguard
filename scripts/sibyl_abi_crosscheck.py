#!/usr/bin/env python3
"""Offline Python/compiled-Solidity/ethers ABI consistency. No RPC or signer."""
from pathlib import Path
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from proofops_casework.anchoring import BaseAuditAnchor


def main():
    anchor=BaseAuditAnchor(chain_id=84532,contract='0x'+'1'*40,
        expected_attester='0x'+'2'*40,rpc_url='https://rpc.invalid')
    plan=anchor.plan('a'*64,7,84532)
    javascript=r'''
const fs=require('fs');
const {Interface}=require('ethers');
const artifact=JSON.parse(fs.readFileSync('artifacts/src/MemoryCaseworkAnchor.sol/MemoryCaseworkAnchor.json','utf8'));
const abi=new Interface(artifact.abi);
const data=abi.encodeFunctionData('anchor',['0x'+'a'.repeat(64),7]);
const topic=abi.getEvent('MemoryProofAnchored').topicHash;
process.stdout.write(JSON.stringify({data,topic}));
'''
    response=subprocess.run(['node','-e',javascript],cwd=ROOT/'contracts',
        check=True,capture_output=True,text=True,timeout=20)
    value=json.loads(response.stdout)
    if value['data'].lower()!=plan['data'].lower() or value['topic'].lower()!=anchor.event_topic.lower():
        raise SystemExit('Python/compiled-contract ABI mismatch')
    print(json.dumps({'abi_consistent':True,'keccak':'eth_utils','compiled_contract':'MemoryCaseworkAnchor',
                      'scope':'Offline calldata/event consistency, not a deployed transaction'}))
    return 0
if __name__=='__main__': raise SystemExit(main())

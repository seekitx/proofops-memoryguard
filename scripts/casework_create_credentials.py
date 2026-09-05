#!/usr/bin/env python3
"""Create LOCAL operator credentials. Raw secrets are never printed or published."""
import argparse
import hashlib
import json
import os
import secrets
from pathlib import Path


def private_write(path, data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w") as output: json.dump(data,output,indent=2)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--directory",type=Path,default=Path(".casework-private"))
    parser.add_argument("--tenant",default="tenant_demo");parser.add_argument("--subject",default="subject_demo")
    args=parser.parse_args()
    args.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    records=[];tokens={}
    for role in ["owner","investigator","reviewer","viewer"]:
        token=secrets.token_urlsafe(40);tokens[role]=token
        records.append({"token_sha256":hashlib.sha256(token.encode()).hexdigest(),"principal":{
            "actor_id":f"actor_{role}","tenant_id":args.tenant,"role":role,"subjects":[args.subject]}})
    registry=args.directory/"registry.json";secret_file=args.directory/"operator-tokens.json"
    if registry.exists() or secret_file.exists(): raise SystemExit("Refusing to replace existing credentials")
    private_write(registry,{"credentials":records});private_write(secret_file,tokens)
    print(f"Private registry: {registry.resolve()}\nLocal operator tokens: {secret_file.resolve()}")
    print("Do not commit, upload, screenshot or record either file. Set CASEWORK_AUTH_FILE to the registry path.")

if __name__=="__main__":main()

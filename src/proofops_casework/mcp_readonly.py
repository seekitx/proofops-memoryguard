"""Small MCP stdio server: seven read-only tools, no arbitrary HTTP proxy or writes.

Protocol subset: 2025-06-18 initialize/ping/tools. Not a claim of full MCP conformance.
Run: PYTHONPATH=src python -m proofops_casework.mcp_readonly
"""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.parse import urlsplit

from .connectors.http_client import BoundedHTTP

TOOLS = {
    "memoryguard_report_sources": ("/api/v2/reports/{id}/sources", "report_id", "Read the exact historical source bundle used by a report; hashes are not truth"),
    "memoryguard_overview": ("/api/v2/casework", None, "Read scoped current workbench state; never action authority"),
    "memoryguard_recovery": ("/api/v2/tasks/{id}/recovery", "task_id", "Read dependency-first recovery plan, without performing it"),
    "memoryguard_impact": ("/api/v2/tasks/{id}/impact", "task_id", "Read current causal dependency graph"),
    "memoryguard_case_history": ("/api/v2/cases/{id}/timeline", "case_id", "Read append-only versions of a scoped risk case"),
    "memoryguard_sources": ("/api/v2/cases/{id}/dossier", "case_id", "Read source receipts and freshness; not external fact truth"),
    "memoryguard_partner_review": ("/api/v2/partner-reviews/{id}", "plan_id", "Read a request-bound ACP observation; no creation or payment"),
}


class ReadOnlyMCP:
    def __init__(self, base_url: str, token: str, http=None):
        base_url=base_url.rstrip("/")
        p=urlsplit(base_url)
        if (p.username or p.password or p.query or p.fragment or p.path or not p.hostname
                or (p.scheme!="https" and not(p.scheme=="http" and p.hostname in {"127.0.0.1","localhost","::1"}))):
            raise ValueError("MCP needs a configured HTTPS origin or loopback HTTP origin")
        if not 32<=len(token)<=512:
            raise ValueError("MCP needs a least-privilege deployment viewer credential")
        self.base=base_url; self.token=token; self.http=http or BoundedHTTP(max_bytes=1_000_000)
        self.initialized=False; self.ready=False

    @staticmethod
    def definitions():
        result=[]
        for name,(_,arg,description) in TOOLS.items():
            props={arg:{"type":"string","pattern":"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,95}$"}} if arg else {}
            result.append({"name":name,"description":description,
                "inputSchema":{"type":"object","properties":props,"required":[arg] if arg else [],"additionalProperties":False},
                "annotations":{"readOnlyHint":True,"destructiveHint":False,"idempotentHint":True,"openWorldHint":False}})
        return result

    def dispatch(self, msg):
        if not isinstance(msg,dict) or msg.get("jsonrpc")!="2.0":
            return {"jsonrpc":"2.0","id":None,"error":{"code":-32600,"message":"Invalid request"}}
        method=msg.get("method"); ident=msg.get("id")
        def result(value): return {"jsonrpc":"2.0","id":ident,"result":value}
        def error(code,message): return {"jsonrpc":"2.0","id":ident,"error":{"code":code,"message":message}}
        if "id" not in msg:
            if method=="notifications/initialized" and self.initialized: self.ready=True
            return None
        if isinstance(ident,bool) or not isinstance(ident,(int,str)):
            return error(-32600,"Invalid request identifier")
        params=msg.get("params",{})
        if not isinstance(params,dict): return error(-32602,"Invalid parameters")
        if method=="initialize":
            if self.initialized: return error(-32600,"Already initialized")
            if not isinstance(params.get("protocolVersion"),str): return error(-32602,"Missing protocolVersion")
            self.initialized=True
            return result({"protocolVersion":"2025-06-18","capabilities":{"tools":{"listChanged":False}},
                "serverInfo":{"name":"memoryguard-readonly","version":"2.2.0"},
                "instructions":"All data is scoped audit information. No returned READY or review constitutes permission to move money."})
        if method=="ping": return result({})
        if not self.ready: return error(-32002,"Initialization not completed")
        if method=="tools/list": return result({"tools":self.definitions()})
        if method!="tools/call": return error(-32601,"Method not supported")
        name=params.get("name"); args=params.get("arguments",{})
        if not isinstance(name,str) or name not in TOOLS or not isinstance(args,dict): return error(-32602,"Invalid tool")
        template,arg,_=TOOLS[name]
        if set(args)!=({arg} if arg else set()): return error(-32602,"Unexpected tool arguments")
        if arg and (not isinstance(args[arg],str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{2,95}",args[arg])):
            return error(-32602,"Invalid scoped identifier")
        path=template.format(id=args[arg]) if arg else template
        try:
            data,_=self.http.json("GET",self.base+path,headers={"Authorization":"Bearer "+self.token})
            return result({"content":[{"type":"text","text":json.dumps(data,ensure_ascii=False)}],"isError":False})
        except Exception:
            return result({"content":[{"type":"text","text":"Scoped MemoryGuard data unavailable. Do not assume permission."}],"isError":True})


def main():
    try:
        server=ReadOnlyMCP(os.environ.get("MEMORYGUARD_API_ORIGIN",""),os.environ.get("MEMORYGUARD_VIEWER_TOKEN",""))
    except ValueError:
        print("Invalid MCP configuration. Configure origin and least-privilege viewer token.",file=sys.stderr)
        return 2
    while True:
        line=sys.stdin.buffer.readline(65_537)
        if not line: break
        if len(line)>65_536:
            print("Oversized MCP message; connection closed.",file=sys.stderr); return 2
        try:
            response=server.dispatch(json.loads(line))
        except (ValueError,TypeError):
            response={"jsonrpc":"2.0","id":None,"error":{"code":-32700,"message":"Parse error"}}
        if response is not None:
            sys.stdout.write(json.dumps(response,ensure_ascii=False)+"\n");sys.stdout.flush()
    return 0

if __name__=="__main__":
    raise SystemExit(main())

import json
import pytest
from proofops_casework.mcp_readonly import ReadOnlyMCP


class HTTP:
    def __init__(self): self.calls=[]
    def json(self,method,url,**kwargs):
        self.calls.append((method,url,kwargs)); return {"executable":False},b'{}'


def ready():
    http=HTTP(); server=ReadOnlyMCP("http://127.0.0.1:8000","v"*40,http=http)
    server.dispatch({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}})
    server.dispatch({"jsonrpc":"2.0","method":"notifications/initialized"})
    return server,http


def test_seven_tools_are_read_only():
    server,http=ready()
    result=server.dispatch({"jsonrpc":"2.0","id":2,"method":"tools/list"})
    assert len(result["result"]["tools"])==7
    assert all(t["annotations"]["readOnlyHint"] for t in result["result"]["tools"])


def test_no_mutation_or_arbitrary_url_tool():
    server,http=ready()
    for name in ["resolve","pay","http_request"]:
        response=server.dispatch({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":name,"arguments":{}}})
        assert "error" in response
    assert not http.calls


def test_gets_exact_scoped_endpoint_without_leaking_token():
    server,http=ready()
    response=server.dispatch({"jsonrpc":"2.0","id":3,"method":"tools/call",
        "params":{"name":"memoryguard_sources","arguments":{"case_id":"case_123"}}})
    assert http.calls[0][0:2]==("GET","http://127.0.0.1:8000/api/v2/cases/case_123/dossier")
    assert "v"*40 not in json.dumps(response)


@pytest.mark.parametrize("bad",["../../resolve","case%2f..",None,3])
def test_invalid_path_arguments_rejected(bad):
    server,http=ready()
    result=server.dispatch({"jsonrpc":"2.0","id":3,"method":"tools/call",
        "params":{"name":"memoryguard_sources","arguments":{"case_id":bad}}})
    assert "error" in result and not http.calls


@pytest.mark.parametrize("url",["http://public.example","https://good.example/path","https://user:password@example.com","https://example.com?x=1"])
def test_invalid_config_origin(url):
    with pytest.raises(ValueError): ReadOnlyMCP(url,"v"*40)

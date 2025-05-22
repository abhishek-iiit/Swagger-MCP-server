# petstore_mcp.py

import json
import httpx
import inspect
from typing import Any, Dict, Optional
from mcp.server.fastmcp import FastMCP
from jsonschema import validate, ValidationError

# ------------------------------------------------------------------------------
#  CONFIGURATION
# ------------------------------------------------------------------------------
mcp = FastMCP("petstore")

with open("openapi.json") as f:
    openapi_spec = json.load(f)

BASE_URL   = "https://petstore3.swagger.io/api/v3"
USER_AGENT = "petstore-mcp-agent/1.0"

# ------------------------------------------------------------------------------
#  HELPERS
# ------------------------------------------------------------------------------
def build_path(path_template: str, path_params: Dict[str, Any]) -> str:
    for name, value in path_params.items():
        path_template = path_template.replace(f"{{{name}}}", str(value))
    return path_template

async def call_endpoint(
    method:       str,
    path:         str,
    query_params: Optional[Dict[str, Any]] = None,
    json_body:    Optional[Any]          = None,
    raw_body:     Optional[bytes]        = None,
    headers:      Optional[Dict[str, str]] = None,
) -> Any:
    """
    Dispatch the HTTP call, sending either JSON or raw bytes.
    """
    url = f"{BASE_URL}{path}"
    hdrs = {"User-Agent": USER_AGENT}
    if json_body is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)

    async with httpx.AsyncClient() as client:
        req = {"params": query_params, "headers": hdrs, "timeout": 30.0}
        if json_body is not None:
            req["json"] = json_body
        elif raw_body is not None:
            req["content"] = raw_body

        resp = await client.request(method, url, **req)
        resp.raise_for_status()
        return None if resp.status_code == 204 else resp.json()
# ------------------------------------------------------------------------------
#  JSON SCHEMA VALIDATION
# ------------------------------------------------------------------------------
def resolve_ref(ref: str, spec: dict):
    """Resolve a $ref in the OpenAPI spec."""
    parts = ref.lstrip("#/").split("/")
    obj = spec
    for part in parts:
        obj = obj[part]
    return obj

def get_request_schema(operation: dict, spec: dict):
    """Extract the JSON schema for the request body, resolving $ref if needed."""
    content = operation.get("requestBody", {}).get("content", {})
    if "application/json" in content:
        schema = content["application/json"]["schema"]
        if "$ref" in schema:
            schema = resolve_ref(schema["$ref"], spec)
        return schema
    return None

# ------------------------------------------------------------------------------
#  TOOL FACTORY
# ------------------------------------------------------------------------------
def create_tool_func(
    path:      str,
    method:    str,
    operation: Dict[str, Any],
    spec:      Dict[str, Any]
):
    params       = operation.get("parameters", [])
    request_body = operation.get("requestBody", {})
    op_id        = operation["operationId"]

    # detect media type
    content = request_body.get("content", {})
    media = (
        "application/json"
        if "application/json" in content
        else "application/octet-stream"
        if "application/octet-stream" in content
        else None
    )

    # if JSON‐ref, we won’t explode it
    is_ref_body = False
    body_props: Dict[str, Any] = {}
    if media == "application/json":
        schema = content[media]["schema"]
        if "$ref" in schema:
            is_ref_body = True
        else:
            # inline schema: explode its properties
            body_props = schema.get("properties", {})

    async def tool_func(**kwargs):
        # 1) path/query/header
        path_params, query_params, headers = {}, {}, {}
        for p in params:
            name, loc = p["name"], p["in"]
            if loc == "path":
                path_params[name] = kwargs.pop(name)
            elif loc == "query":
                query_params[name] = kwargs.pop(name)
            elif loc == "header":
                headers[name]      = kwargs.pop(name)

        # 2) decide JSON vs raw
        json_body = None
        raw_body  = None
    
        if media == "application/json":
            if is_ref_body:
                json_body = kwargs.pop("body")
            else:
                json_body = {k: kwargs.pop(k) for k in body_props if k in kwargs}
    
            # -- Validate JSON body here --
            schema = get_request_schema(operation, spec)
            if schema:
                try:
                    validate(instance=json_body, schema=schema)
                except ValidationError as ve:
                    raise ValueError(f"Request body validation failed: {ve.message}")
    
        elif media == "application/octet-stream":
            raw_body = kwargs.pop("file")

        # 3) call
        actual_path = build_path(path, path_params)
        return await call_endpoint(
            method.upper(),
            actual_path,
            query_params=query_params or None,
            json_body=json_body,
            raw_body=raw_body,
            headers=headers or None,
        )

    # 4) build signature
    sig = []
    used = {p["name"] for p in params}
    for p in params:
        sig.append(inspect.Parameter(
            p["name"], inspect.Parameter.POSITIONAL_OR_KEYWORD
        ))

    if media == "application/json":
        if is_ref_body:
            sig.append(inspect.Parameter(
                "body",
                inspect.Parameter.POSITIONAL_OR_KEYWORD
            ))
        else:
            for prop in body_props:
                if prop not in used:
                    sig.append(inspect.Parameter(
                        prop,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        default=None
                    ))

    elif media == "application/octet-stream":
        sig.append(inspect.Parameter(
            "file",
            inspect.Parameter.POSITIONAL_OR_KEYWORD
        ))

    tool_func.__signature__ = inspect.Signature(parameters=sig)
    tool_func.__name__      = op_id
    tool_func.__doc__       = operation.get("summary", "")
    return tool_func

# ------------------------------------------------------------------------------
#  REGISTER TOOLS
# ------------------------------------------------------------------------------
for path, methods in openapi_spec["paths"].items():
    for method, operation in methods.items():
        op_id = operation.get("operationId")
        if not op_id:
            continue
        fn = create_tool_func(path, method, operation, openapi_spec)
        mcp.tool(name=op_id)(fn)

# ------------------------------------------------------------------------------
#  ENTRYPOINT
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")

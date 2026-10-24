"""最小的麦当劳 MCP Streamable HTTP 客户端，只读，无第三方依赖。

Token 只从环境变量 MCD_MCP_TOKEN 读取，绝不打印 Token，
也绝不把 Token 写进任何文件。输出文件里只有 MCP 返回的业务数据。
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

URL = "https://mcp.mcd.cn"


def parse_response(body):
    text = body.decode("utf-8", errors="ignore").strip()
    if not text:
        return None
    if "data:" in text:
        payloads = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data = line[5:].strip()
                if data and data != "[DONE]":
                    try:
                        payloads.append(json.loads(data))
                    except json.JSONDecodeError:
                        pass
        for payload in reversed(payloads):
            if isinstance(payload, dict) and ("result" in payload or "error" in payload):
                return payload
        return payloads[-1] if payloads else None
    return json.loads(text)


def post(payload, session_id, token):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    req.add_header("Authorization", "Bearer " + token)
    if session_id:
        req.add_header("Mcp-Session-Id", session_id)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return parse_response(resp.read()), headers.get("mcp-session-id")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:500]
        raise SystemExit(f"MCP 请求失败，HTTP {e.code}：{body}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", default="list-nutrition-foods")
    parser.add_argument("--out", default="")
    parser.add_argument("--list-tools", action="store_true")
    parser.add_argument("--args-json", default="{}")
    args = parser.parse_args()

    token = os.environ.get("MCD_MCP_TOKEN", "").strip()
    if not token:
        print("缺少环境变量 MCD_MCP_TOKEN，请先在你自己的终端里设置，"
              "不要把 Token 写进文件或发到公开场合。", file=sys.stderr)
        return 2

    session_id = None
    result, session_id = post({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "mcd-kcal-picker", "version": "0.1.0"},
        },
    }, session_id, token)
    if not result or "error" in result:
        print(f"initialize 失败：{result}", file=sys.stderr)
        return 1

    # JSON-RPC 通知，无需返回值，失败也不中断主流程
    try:
        post({"jsonrpc": "2.0", "method": "notifications/initialized"},
             session_id, token)
    except SystemExit:
        pass

    result, session_id = post({
        "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
    }, session_id, token)
    if not result or "error" in result:
        print(f"tools/list 失败：{result}", file=sys.stderr)
        return 1
    tools = result["result"].get("tools", [])
    names = [t.get("name", "") for t in tools]
    print(f"工具总数：{len(names)}")
    if args.list_tools:
        for name in names:
            print(name)
        return 0
    if args.tool not in names:
        print(f"工具 {args.tool} 不在工具列表里，可用工具见上。", file=sys.stderr)
        return 1

    try:
        call_args = json.loads(args.args_json)
    except json.JSONDecodeError:
        call_args = {}
    result, session_id = post({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": args.tool, "arguments": call_args},
    }, session_id, token)
    if not result or "error" in result:
        print(f"tools/call 失败：{result}", file=sys.stderr)
        return 1
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result["result"], f, ensure_ascii=False, indent=2)
        print(f"已保存到 {args.out}")
    else:
        print(json.dumps(result["result"], ensure_ascii=False)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

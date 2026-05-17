import json
import os
import subprocess

def test_search(query):
    # The MCP server expects an initialization request first
    init_request = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-01-01",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }

    server_path = os.path.join(os.path.dirname(__file__), "server.py")
    process = subprocess.Popen(
        ["python3", server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        # Send initialize
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        process.stdout.readline()  # Consume init response

        # Send tool call
        call_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "query": query
                }
            }
        }
        process.stdin.write(json.dumps(call_request) + "\n")
        process.stdin.flush()

        response_data = process.stdout.readline()
        if response_data:
            return json.loads(response_data)
        else:
            return "No response from server"
    except Exception as e:
        return f"Error: {e}"
    finally:
        process.terminate()

if __name__ == "__main__":
    print(test_search("current weather in London"))

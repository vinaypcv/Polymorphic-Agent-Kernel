import asyncio
import json
import sys
from typing import Dict, Any, Optional

class MCPTransportMultiplexer:
    """Provides a native Model Context Protocol connection layer for external editor tools."""
    def __init__(self, kernel_runtime: Any):
        self.kernel = kernel_runtime
        self.running = False
        self.read_queue: asyncio.Queue = asyncio.Queue()
        self.write_lock = asyncio.Lock()

    async def start_event_loop(self):
        self.running = True
        asyncio.create_task(self._async_stdin_reader())
        await self._processing_execution_worker()

    async def _async_stdin_reader(self):
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        while self.running:
            line = await reader.readline()
            if not line:
                break
            await self.read_queue.put(line)

    async def _processing_execution_worker(self):
        while self.running:
            raw_line = await self.read_queue.get()
            try:
                payload = json.loads(raw_line.decode('utf-8'))
                response = await self._route_protocol_message(payload)
                if response:
                    async with self.write_lock:
                        sys.stdout.write(json.dumps(response) + "\n")
                        sys.stdout.flush()
            except Exception as e:
                pass
            finally:
                self.read_queue.task_done()

    async def _route_protocol_message(self, message: dict) -> Optional[dict]:
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "pak-router", "version": "0.1.0"}},
                "id": msg_id
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            if tool_name == "kernel/execute_vtable_node":
                target = arguments.get("action_target")
                args = arguments.get("payload_arguments", {})
                res = self.kernel.vtable[target](args)
                return {"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": json.dumps(res)}]}, "id": msg_id}
        return {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": msg_id}
import json
from typing import Dict, Any
from langchain_mcp_adapters.client import MultiServerMCPClient

class MCPClient:
    def __init__(self):
        self.tools = []
        self.client = None

    async def initialize(self):
        server_list = self._load_server_list()
        try:
            self.client = MultiServerMCPClient(server_list)
            await self.client.__aenter__()
            self.tools = self.client.get_tools()
        except Exception as e:
            raise RuntimeError(f"MCP client initialization failed: {str(e)}")

    def _load_server_list(self) -> Dict[str, Any]:
        try:
            with open("mcp_server.json", "r", encoding="utf-8") as f:
                return json.load(f)["mcpServers"]
        except FileNotFoundError:
            return {}

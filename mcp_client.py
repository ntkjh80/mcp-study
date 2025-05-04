import json
import asyncio
from typing import Dict, Any
from langchain_mcp_adapters.client import MultiServerMCPClient

class MCPClient:
    def __init__(self):
        self.tools = []
        self.client = None

    async def initialize(self):
        server_list = self._load_server_list() # MCP 서버 리스트 가져오기
        try:
            self.client = MultiServerMCPClient(server_list)
            await self.client.__aenter__()
            self.tools = self.client.get_tools() # MCP 서버로부터 Tool 가져오기
        except Exception as e:
            raise RuntimeError(f"MCP client initialization failed: {str(e)}")

    def _load_server_list(self) -> Dict[str, Any]:
        try:
            with open("mcp_server.json", "r", encoding="utf-8") as f:
                return json.load(f)["mcpServers"]
        except FileNotFoundError:
            return {}
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
            # 수정 1: async with로 컨텍스트 관리
            async with MultiServerMCPClient(server_list) as client:
                self.client = client
                self.tools = client.get_tools()
        except Exception as e:
            # 수정 2: 에러 메시지 상세화
            raise RuntimeError(f"MCP 초기화 실패: {str(e)}. 서버 설정 확인 필요")

    def _load_server_list(self) -> Dict[str, Any]:
        try:
            with open("mcp_server.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                # 수정 3: JSON 구조 검증
                if "mcpServers" not in data:
                    raise ValueError("mcp_server.json에 'mcpServers' 키 누락")
                return data["mcpServers"]
        except FileNotFoundError:
            return {}
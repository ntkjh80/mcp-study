# mcp_tools/k8s_mcp_instance.py
from mcp.server.fastmcp import FastMCP

# 공유 MCP 인스턴스를 여기서 생성합니다.
mcp_instance = FastMCP("k8s-pilot")
print(f"[k8s_mcp_instance DEBUG] Shared MCP instance created with ID: {id(mcp_instance)}")
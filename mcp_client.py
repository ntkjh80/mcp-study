# 필요한 라이브러리 임포트
import json  # JSON 파일 처리를 위함
import asyncio  # 비동기 프로그래밍을 위함
from typing import Dict, Any  # 타입 힌트를 위함
from langchain_mcp_adapters.client import MultiServerMCPClient  # MCP 클라이언트 라이브러리

# MCP 클라이언트 클래스 정의
class MCPClient:
    """
    MCP 서버들과 통신하고 사용 가능한 도구(Tool) 목록을 관리하는 클라이언트 클래스.
    """
    def __init__(self):
        """
        클래스 초기화 메서드.
        tools: 사용 가능한 도구 목록을 저장할 리스트.
        client: MultiServerMCPClient 인스턴스를 저장할 변수.
        """
        self.tools = []  # MCP 서버에서 제공하는 도구들을 저장할 리스트
        self.client = None  # MultiServerMCPClient 인스턴스

    async def initialize(self):
        """
        MCP 클라이언트를 비동기적으로 초기화하는 메서드.
        mcp_server.json 파일에서 서버 목록을 로드하고,
        MultiServerMCPClient를 생성하여 서버에 연결하고 도구 목록을 가져온다.
        """
        server_list = self._load_server_list() # 설정 파일에서 MCP 서버 목록 로드
        if not server_list:
            print("경고: mcp_server.json 파일을 찾을 수 없거나 비어있습니다. MCP 도구를 로드할 수 없습니다.") # 서버 목록 로드 실패 시 경고 메시지
            return # 초기화 중단

        try:
            # MultiServerMCPClient 인스턴스 생성 및 초기화
            self.client = MultiServerMCPClient(server_list)
            # 비동기 컨텍스트 매니저를 사용하여 클라이언트 시작
            await self.client.__aenter__()
            # 연결된 MCP 서버로부터 사용 가능한 도구 목록 가져오기
            self.tools = self.client.get_tools() # MCP 서버로부터 Tool 가져오기
        except Exception as e:
            # 초기화 중 오류 발생 시 Runtime 에러 발생
            raise RuntimeError(f"MCP 클라이언트 초기화 실패: {str(e)}") # MCP client initialization failed: {str(e)}

    def _load_server_list(self) -> Dict[str, Any]:
        """
        mcp_server.json 파일에서 MCP 서버 목록을 로드하는 내부 메서드.

        Returns:
            dict: 로드된 서버 설정 정보 딕셔너리. 파일이 없거나 오류 발생 시 빈 딕셔너리 반환.
        """
        try:
            # JSON 파일을 읽기 모드로 열고 UTF-8 인코딩 사용
            with open("mcp_server.json", "r", encoding="utf-8") as f:
                # JSON 파일 내용을 파싱하여 "mcpServers" 키의 값 반환
                return json.load(f)["mcpServers"] # mcp_server.json 파일을 읽어 서버 목록 반환
        except FileNotFoundError:
            # 파일을 찾을 수 없을 경우 빈 딕셔너리 반환
            return {} # 파일이 없을 경우 빈 딕셔너리 반환
        except Exception as e:
            # 기타 파일 로딩/파싱 오류 발생 시 경고 출력 후 빈 딕셔너리 반환
            print(f"경고: mcp_server.json 로드 중 오류 발생: {e}")
            return {}


# 예시: 비동기 메인 함수 (실제 실행 로직은 아님)
async def main():
    client = MCPClient()
    try:
        await client.initialize()
        if client.tools:
            print("사용 가능한 MCP 도구:")
            for tool in client.tools:
                print(f"- {tool.name}: {tool.description}")
        else:
            print("로드된 MCP 도구가 없습니다.")
    except RuntimeError as e:
        print(f"오류: {e}")
    finally:
        await client.close()

# 이 스크립트가 직접 실행될 때 main 함수 실행 (테스트용)
if __name__ == "__main__":
    asyncio.run(main())
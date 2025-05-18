import sys
import os

# 현재 파일(mcp_server_k8s.py)의 절대 경로를 기준으로 프로젝트 루트 디렉토리를 계산
# os.path.abspath(__file__) -> /path/to/temp2/mcp_tools/mcp_server_k8s.py
# os.path.dirname(...) -> /path/to/temp2/mcp_tools
# os.path.dirname(os.path.dirname(...)) -> /path/to/temp2 (프로젝트 루트)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 프로젝트 루트를 sys.path에 추가하여 'resources', 'tools' 등의 모듈을 찾을 수 있도록 함
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 이 파일은 FastMCP 서버 인스턴스를 초기화하고,
# 애플리케이션의 다양한 리소스 및 도구 모듈을 로드하는 역할을 합니다.

# mcp.server.fastmcp 모듈에서 FastMCP 클래스를 가져옵니다.
from mcp.server.fastmcp import FastMCP

# "k8s-pilot"이라는 이름으로 FastMCP 서버 인스턴스를 생성합니다.
# 이 mcp 객체는 애플리케이션 전체에서 리소스 및 도구를 등록하는 데 사용됩니다.
mcp = FastMCP("k8s-pilot")


# 애플리케이션의 리소스 및 도구 모듈을 로드하는 함수입니다.
# 이 함수는 @mcp.tool 또는 @mcp.resource 데코레이터가 올바르게 동작하여
# 해당 함수들을 MCP 서버에 등록하도록 하기 위해 호출되어야 합니다.
def load_modules():
    """
    애플리케이션에서 사용되는 모든 리소스 및 도구 모듈을 임포트합니다.
    이 함수를 호출함으로써 각 모듈에 정의된 @mcp.tool 및 @mcp.resource 데코레이터가
    실행되어 해당 기능들이 MCP 서버에 등록됩니다.
    """
    import resources.contexts  # noqa: F401. Kubernetes 컨텍스트 관련 리소스를 로드합니다.
    import tools.cluster  # noqa: F401. 클러스터 관리 관련 도구를 로드합니다.
    import tools.configmap  # noqa: F401. ConfigMap 관리 도구를 로드합니다.
    import tools.daemonset  # noqa: F401. DaemonSet 관리 도구를 로드합니다.
    import tools.deployment  # noqa: F401. Deployment 관리 도구를 로드합니다.
    import tools.ingress  # noqa: F401. Ingress 관리 도구를 로드합니다.
    import tools.namespace  # noqa: F401. Namespace 관리 도구를 로드합니다.
    import tools.node  # noqa: F401. Node 관리 도구를 로드합니다.
    import tools.pod  # noqa: F401. Pod 관리 도구를 로드합니다.
    import tools.pv  # noqa: F401. PersistentVolume 관리 도구를 로드합니다.
    import tools.pvc  # noqa: F401. PersistentVolumeClaim 관리 도구를 로드합니다.
    import tools.replicaset  # noqa: F401. ReplicaSet 관리 도구를 로드합니다.
    import tools.role  # noqa: F401. Role 및 ClusterRole 관리 도구를 로드합니다.
    import tools.secret  # noqa: F401. Secret 관리 도구를 로드합니다.
    import tools.service  # noqa: F401. Service 관리 도구를 로드합니다.
    import tools.serviceaccount  # noqa: F401. ServiceAccount 관리 도구를 로드합니다.
    import tools.statefulset  # noqa: F401. StatefulSet 관리 도구를 로드합니다.


# 서버 초기화 시 모든 관련 모듈을 로드하여 MCP 서버에 도구와 리소스를 등록합니다.
load_modules()

# 스크립트가 직접 실행될 때 MCP 서버를 시작하는 부분 추가
if __name__ == "__main__":
    print("[k8s-pilot Server] Starting k8s-pilot MCP server using stdio transport...")
    # load_modules() 는 이미 위에서 호출되었으므로, mcp 객체에 도구들이 등록된 상태입니다.
    mcp.run(transport="stdio")
    print("[k8s-pilot Server] k8s-pilot MCP server stopped.")
# resources/contexts.py
# 이 파일은 Kubernetes의 kubeconfig 파일에서 사용 가능한 모든 컨텍스트 정보를
# 조회하는 MCP 리소스를 정의합니다.

import os  # 파일 경로 조작을 위해 사용합니다.
import yaml  # YAML 파일 파싱을 위해 사용합니다.

from models.context import ContextInfo  # 컨텍스트 정보 모델을 가져옵니다.
from mcp_tools.mcp_server_k8s import mcp  # MCP 서버 인스턴스를 가져옵니다.
# kubernetes.config는 직접 사용하지 않고, kubeconfig 파일 경로를 직접 사용합니다.
# 만약 kubernetes 라이브러리의 표준 방식을 사용하려면 config.list_kube_config_contexts() 등을 고려할 수 있습니다.

@mcp.resource(uri="k8s://kube-contexts", name="Kube Contexts", description="사용 가능한 모든 kube 컨텍스트를 나열합니다.")
def list_kube_contexts():
    """
    사용자의 kubeconfig 파일에서 모든 Kubernetes 컨텍스트를 읽어와
    `ContextInfo` 객체의 리스트 형태로 반환합니다.

    kubeconfig 파일의 기본 경로는 `~/.kube/config` 입니다.

    Returns:
        List[ContextInfo]: 각 컨텍스트의 이름, 클러스터, 사용자 정보 및
                           현재 활성화된 컨텍스트인지 여부를 담은 `ContextInfo` 객체의 리스트.
                           kubeconfig 파일을 읽을 수 없거나 파싱 오류 발생 시 예외가 발생할 수 있습니다.
    """
    # 사용자 홈 디렉토리의 .kube/config 파일 경로를 구성합니다.
    kubeconfig_path = os.path.expanduser("~/.kube/config")

    # kubeconfig 파일을 읽기 모드로 엽니다.
    with open(kubeconfig_path, "r") as f:
        # YAML 파서를 사용하여 파일 내용을 안전하게 로드합니다.
        config_data = yaml.safe_load(f)

    # 현재 활성화된 컨텍스트의 이름을 가져옵니다. 없으면 None이 됩니다.
    current_context = config_data.get("current-context")
    # kubeconfig 파일에서 'contexts' 섹션을 가져옵니다. 없으면 빈 리스트를 사용합니다.
    contexts = config_data.get("contexts", [])

    # 각 컨텍스트 정보를 ContextInfo 객체로 변환하여 리스트를 생성합니다.
    return [
        ContextInfo(
            name=ctx["name"],  # 컨텍스트 이름
            cluster=ctx["context"].get("cluster"),  # 컨텍스트 정의 내의 클러스터 이름
            user=ctx["context"].get("user"),  # 컨텍스트 정의 내의 사용자 이름
            current=(ctx["name"] == current_context),  # 현재 활성 컨텍스트인지 여부
        )
        for ctx in contexts  # 모든 컨텍스트에 대해 반복
    ]
# core/kubeconfig.py
# 이 파일은 Kubernetes API 클라이언트를 가져오고 kubeconfig 파일을 로드하는
# 유틸리티 함수들을 포함합니다. API 클라이언트 캐싱 기능을 제공하여
# 반복적인 설정 로드 및 클라이언트 초기화를 방지합니다.

import os  # 파일 경로 조작을 위해 사용합니다.
from typing import Dict, Any  # 타입 힌트를 위해 사용합니다.

import yaml  # YAML 파일 파싱을 위해 사용합니다.
from kubernetes import client, config  # Kubernetes 클라이언트 및 설정 관리를 위해 사용합니다.

# API 클라이언트를 캐싱하기 위한 딕셔너리입니다.
# 컨텍스트 이름을 키로 사용하며, 값으로는 해당 컨텍스트의 API 클라이언트 딕셔너리를 저장합니다.
# 이를 통해 동일 컨텍스트에 대한 반복적인 API 클라이언트 생성을 방지합니다.
_client_cache: Dict[str, Dict[str, Any]] = {}


def get_api_clients(context_name: str) -> Dict[str, Any]:
    """
    지정된 Kubernetes 컨텍스트에 대한 API 클라이언트들을 반환합니다.
    이 함수는 kubeconfig 파일을 반복적으로 로드하고 클라이언트를 재초기화하는 것을
    방지하기 위해 클라이언트를 캐싱합니다.

    Args:
        context_name (str): API 클라이언트를 가져올 Kubernetes 컨텍스트의 이름.

    Returns:
        Dict[str, Any]: CoreV1Api, AppsV1Api, BatchV1Api 등을 포함하는 API 클라이언트 딕셔너리.
                        예: {"core": CoreV1Api_instance, "apps": AppsV1Api_instance}
    """
    # 캐시에 해당 컨텍스트의 클라이언트가 없는 경우 새로 생성합니다.
    if context_name not in _client_cache:
        # 새로운 Kubernetes 클라이언트 설정을 생성합니다.
        configuration = client.Configuration()
        # 지정된 컨텍스트로 kubeconfig를 로드하고 클라이언트 설정을 적용합니다.
        config.load_kube_config(context=context_name, client_configuration=configuration)
        # 설정된 정보로 ApiClient 인스턴스를 생성합니다.
        api_client = client.ApiClient(configuration=configuration)

        # 해당 컨텍스트에 대한 API 클라이언트들을 생성하여 캐시에 저장합니다.
        _client_cache[context_name] = {
            "core": client.CoreV1Api(api_client),  # Core API (Pods, Services, Namespaces 등)
            "apps": client.AppsV1Api(api_client),  # Apps API (Deployments, StatefulSets, DaemonSets 등)
            "batch": client.BatchV1Api(api_client), # Batch API (Jobs, CronJobs 등)
            # 필요한 경우 다른 API 그룹 (예: "networking", "rbac", "storage" 등)도 추가할 수 있습니다.
            # 예시:
            # "networking": client.NetworkingV1Api(api_client),
            # "rbac": client.RbacAuthorizationV1Api(api_client),
        }
    # 캐시된 (또는 새로 생성된) API 클라이언트 딕셔너리를 반환합니다.
    return _client_cache[context_name]


def get_kubeconfig():
    """
    기본 위치에서 kubeconfig 파일을 로드합니다.
    기본 위치는 일반적으로 `~/.kube/config` 입니다.
    이 함수는 파싱된 kubeconfig 데이터를 반환합니다.
    파일이 존재하지 않거나 읽을 수 없는 경우 예외가 발생합니다.

    다른 kubeconfig 파일을 로드하려면 KUBECONFIG 환경 변수를
    사용하려는 kubeconfig 파일의 경로로 설정할 수 있습니다. (이 함수는 환경변수를 직접 사용하진 않음)

    Returns:
        dict: 파싱된 kubeconfig 데이터.

    Raises:
        FileNotFoundError: kubeconfig 파일을 찾을 수 없는 경우.
        yaml.YAMLError: kubeconfig 파일 파싱 중 오류가 발생한 경우.
    """
    # kubeconfig 파일의 기본 경로를 가져옵니다. (사용자 홈 디렉토리의 .kube/config)
    kubeconfig_path = os.path.expanduser(config.KUBE_CONFIG_DEFAULT_LOCATION)

    # kubeconfig 파일을 읽기 모드로 엽니다.
    with open(kubeconfig_path, "r") as f:
        # YAML 파서를 사용하여 파일 내용을 안전하게 로드합니다.
        config_data = yaml.safe_load(f)
    return config_data
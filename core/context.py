# core/context.py
# 이 파일은 Kubernetes 클러스터의 현재 컨텍스트 및 네임스페이스 정보를 관리하는
# 유틸리티 함수들을 포함합니다. 데코레이터를 통해 함수 호출 시 자동으로
# 현재 컨텍스트 정보를 주입하는 기능을 제공합니다.

import inspect  # 함수 시그니처를 검사하기 위해 사용합니다.
from functools import wraps  # 데코레이터 작성을 위해 사용합니다.
from typing import Callable  # 타입 힌트를 위해 사용합니다.

from kubernetes import config  # Kubernetes 설정 로드 및 컨텍스트 관리를 위해 사용합니다.
from mcp_tools.mcp_server_k8s import mcp

def get_current_context_name() -> str:
    """
    현재 활성화된 Kubernetes 컨텍스트의 이름을 반환합니다.

    kubeconfig 파일을 로드하여 현재 활성 컨텍스트 정보를 가져옵니다.

    Returns:
        str: 현재 Kubernetes 컨텍스트의 이름.
    """
    # kubeconfig를 로드하고 현재 활성 컨텍스트를 가져옵니다.
    _, active_context = config.list_kube_config_contexts()

    # 활성 컨텍스트의 이름을 반환합니다.
    return active_context['name']


def get_default_namespace(context_name: str) -> str:
    """
    주어진 Kubernetes 컨텍스트에 설정된 기본 네임스페이스를 반환합니다.
    만약 컨텍스트에 기본 네임스페이스가 명시적으로 설정되어 있지 않다면 "default"를 반환합니다.

    Args:
        context_name (str): 네임스페이스를 조회할 Kubernetes 컨텍스트의 이름.

    Returns:
        str: 해당 컨텍스트의 기본 네임스페이스. 명시적 설정이 없으면 "default".
    """
    # kubeconfig를 로드하여 모든 컨텍스트 정보를 가져옵니다.
    contexts, _ = config.list_kube_config_contexts()

    # 주어진 이름과 일치하는 컨텍스트를 찾습니다.
    for ctx in contexts:
        if ctx['name'] == context_name:
            # 컨텍스트 데이터에서 네임스페이스 정보를 가져옵니다.
            # 'namespace' 키가 없으면 'default'를 기본값으로 사용합니다.
            context_data = ctx['context']
            return context_data.get('namespace', 'default')

    # 만약 컨텍스트를 찾지 못했거나, 해당 컨텍스트에 네임스페이스가 지정되지 않은 경우,
    # "default" 네임스페이스를 반환합니다.
    return 'default'


def use_current_context(func: Callable) -> Callable:
    """
    함수가 호출될 때 `context_name` 인자가 None이거나 제공되지 않은 경우,
    자동으로 현재 활성화된 Kubernetes 컨텍스트 이름을 사용하도록 하는 데코레이터입니다.
    또한, `namespace` 인자가 None이거나 제공되지 않은 경우, 해당 컨텍스트의
    기본 네임스페이스를 사용하도록 설정합니다.

    Args:
        func (Callable): 데코레이팅할 함수.

    Returns:
        Callable: 컨텍스트 및 네임스페이스 자동 주입 기능이 추가된 데코레이팅된 함수.
    """

    @wraps(func)  # 원본 함수의 메타데이터(이름, 독스트링 등)를 유지합니다.
    def wrapper(*args, **kwargs):
        # 데코레이팅된 함수의 시그니처를 가져옵니다.
        sig = inspect.signature(func)

        # 함수 시그니처에 'context_name' 파라미터가 있는지 확인합니다.
        if 'context_name' in sig.parameters:
            # 'context_name'이 kwargs에 없거나 None이면 현재 컨텍스트 이름을 사용합니다.
            if 'context_name' not in kwargs or kwargs['context_name'] is None:
                kwargs['context_name'] = get_current_context_name()
            # context_name을 확정합니다.
            context_name = kwargs['context_name']

            # 함수 시그니처에 'namespace' 파라미터도 있는지 확인합니다.
            if 'namespace' in sig.parameters:
                # 'namespace'가 kwargs에 없거나 None이면 해당 컨텍스트의 기본 네임스페이스를 사용합니다.
                if 'namespace' not in kwargs or kwargs['namespace'] is None:
                    kwargs['namespace'] = get_default_namespace(context_name)

        # 원래 함수를 수정된 인자들로 호출합니다.
        return func(*args, **kwargs)

    return wrapper
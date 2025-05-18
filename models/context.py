# models/context.py
# 이 파일은 Kubernetes 컨텍스트 정보를 나타내는 데이터 클래스를 정의합니다.

from dataclasses import dataclass  # 데이터 클래스 생성을 위해 사용합니다.

@dataclass
class ContextInfo:
    """
    Kubernetes 컨텍스트의 정보를 나타내는 데이터 클래스입니다.

    Attributes:
        name (str): 컨텍스트의 이름.
        cluster (str): 컨텍스트가 속한 클러스터의 이름.
        user (str): 컨텍스트에 연결된 사용자의 이름.
        current (bool): 이 컨텍스트가 현재 활성화된 컨텍스트인지 여부.
    """
    name: str  # 컨텍스트 이름
    cluster: str  # 클러스터 이름
    user: str  # 사용자 이름
    current: bool  # 현재 활성 컨텍스트 여부
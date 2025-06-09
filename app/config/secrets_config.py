"""
보안 설정 파일 - 환경변수로 관리되는 민감한 정보들
"""

import os
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ElasticsearchSecrets:
    """Elasticsearch 연결 정보"""
    host: str
    username: str
    password: str
    
    @classmethod
    def from_env(cls) -> 'ElasticsearchSecrets':
        host = os.getenv("ES_HOST")
        username = os.getenv("ES_USER") 
        password = os.getenv("ES_PASSWORD")
        
        if not all([host, username, password]):
            raise EnvironmentError(
                "ES_HOST, ES_USER, ES_PASSWORD 환경변수가 설정되어야 합니다."
            )
        
        return cls(host=host, username=username, password=password)
    
    def get_credentials(self) -> Tuple[str, str]:
        """ES 인증 정보를 튜플로 반환"""
        return (self.username, self.password)


@dataclass
class GoogleCloudSecrets:
    """Google Cloud 관련 인증 정보"""
    project_id: str
    location: str
    
    @classmethod
    def from_env(cls) -> 'GoogleCloudSecrets':
        project_id = os.getenv("PROJECT_ID")
        location = os.getenv("LOCATION")
        
        if not all([project_id, location]):
            raise EnvironmentError(
                "PROJECT_ID, LOCATION 환경변수가 설정되어야 합니다."
            )
        
        return cls(project_id=project_id, location=location)


@dataclass
class MinIOSecrets:
    """MinIO 연결 정보"""
    host: str 
    access_key: str 
    secret_key: str 
    secure: bool = True
    
    @classmethod
    def from_env(cls) -> 'MinIOSecrets':
        """환경변수에서 MinIO 설정을 읽어옴 (선택적)"""
        host = os.getenv("MINIO_HOST")
        access_key = os.getenv("MINIO_ACCESS_KEY")
        secret_key = os.getenv("MINIO_SECRET_KEY")
        secure = os.getenv("MINIO_SECURE", "true").lower() == "true"
        
        return cls(
            host=host,
            access_key=access_key, 
            secret_key=secret_key,
            secure=secure
        )


@dataclass
class SecretsConfig:
    """모든 보안 설정을 통합하는 클래스"""
    elasticsearch: ElasticsearchSecrets
    google_cloud: GoogleCloudSecrets
    minio: MinIOSecrets
    
    @classmethod
    def from_env(cls) -> 'SecretsConfig':
        """환경변수에서 모든 보안 설정을 로드"""
        return cls(
            elasticsearch=ElasticsearchSecrets.from_env(),
            google_cloud=GoogleCloudSecrets.from_env(),
            minio=MinIOSecrets.from_env()
        )


# 전역 보안 설정 로더 함수
def load_secrets() -> SecretsConfig:
    """환경변수에서 보안 설정을 로드"""
    try:
        return SecretsConfig.from_env()
    except EnvironmentError as e:
        raise EnvironmentError(f"보안 설정 로드 실패: {e}")
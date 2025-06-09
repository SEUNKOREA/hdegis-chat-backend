"""
MinIO 스토리지 구현
"""

from typing import Optional
import logging
from minio import Minio
from minio.error import S3Error

from .base_storage import BaseStorage
from config.secrets_config import MinIOSecrets

logger = logging.getLogger(__name__)


class MinIOStorage(BaseStorage):
    """MinIO 스토리지 구현"""
    
    def __init__(self, secrets: MinIOSecrets, bucket_name: str):
        """
        MinIO 클라이언트 초기화
        
        Args:
            secrets: MinIO 인증 정보
            bucket_name: 버킷명
        """
        self.bucket_name = bucket_name
        self.client = Minio(
            secrets.host,
            access_key=secrets.access_key,
            secret_key=secrets.secret_key,
            secure=secrets.secure
        )
        
        # 연결 테스트
        try:
            self.client.bucket_exists(bucket_name)
            logger.info(f"MinIO 연결 성공: {secrets.host}/{bucket_name}")
        except S3Error as e:
            logger.error(f"MinIO 연결 실패: {e}")
            raise
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """MinIO에서 파일 다운로드"""
        try:
            self.ensure_local_dir(local_path)
            self.client.fget_object(
                bucket_name=self.bucket_name,
                object_name=remote_path,
                file_path=local_path
            )
            logger.debug(f"파일 다운로드 성공: {remote_path} -> {local_path}")
            return True
            
        except S3Error as e:
            logger.error(f"파일 다운로드 실패: {remote_path} - {e}")
            return False
    
    def file_exists(self, remote_path: str) -> bool:
        """MinIO에서 파일 존재 여부 확인"""
        try:
            self.client.stat_object(self.bucket_name, remote_path)
            return True
        except S3Error:
            return False
    
    def get_file_bytes(self, remote_path: str) -> Optional[bytes]:
        """MinIO에서 파일 내용을 바이트로 반환"""
        try:
            response = self.client.get_object(self.bucket_name, remote_path)
            data = response.read()
            response.close()
            return data
            
        except S3Error as e:
            logger.error(f"파일 읽기 실패: {remote_path} - {e}")
            return None
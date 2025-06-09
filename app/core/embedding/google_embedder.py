"""
Google 임베딩 모델 구현
"""

from typing import List, Optional
import logging
from google import genai
from google.genai.types import EmbedContentConfig

from app.core.embedding.base_embedder import BaseEmbedder
from app.config.model_mappings import get_embedding_model_info
from app.config.secrets_config import GoogleCloudSecrets

logger = logging.getLogger(__name__)


class GoogleEmbedder(BaseEmbedder):
    """Google 임베딩 모델 구현"""
    
    def __init__(
        self, 
        model_name: str = "text-embedding-004",
        secrets: Optional[GoogleCloudSecrets] = None
    ):
        """
        Google 임베딩 모델 초기화
        
        Args:
            model_name: 사용할 모델명
            secrets: Google Cloud 인증 정보 (None이면 환경변수 사용)
        """
        self._model_name = model_name
        
        # genai 클라이언트 초기화
        if secrets:
            self.client = genai.Client(
                vertexai=True,
                project=secrets.project_id,
                location=secrets.location
            )
        else:
            self.client = genai.Client()
        
        # 모델 정보 로드
        model_info = get_embedding_model_info(model_name)
        if model_info is None:
            logger.warning(f"알 수 없는 모델: {model_name}. 기본값을 사용합니다.")
            self._need_translation = True
            self._default_dimensionality = 768
        else:
            self._need_translation = model_info.need_translation
            self._default_dimensionality = model_info.default_dimensionality
        
        logger.info(f"Google 임베딩 모델 초기화: {model_name}")
    
    def embed_text(
        self,
        text: str,
        task: str = "RETRIEVAL_DOCUMENT",
        dimensionality: Optional[int] = None
    ) -> List[float]:
        """텍스트를 임베딩 벡터로 변환"""
        try:
            # 설정 구성
            config = EmbedContentConfig(
                task_type=task,
                output_dimensionality=dimensionality or self._default_dimensionality
            )
            
            # 임베딩 생성
            response = self.client.models.embed_content(
                model=self._model_name,
                contents=[text],
                config=config
            )
            
            return response.embeddings[0].values
            
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            raise
    
    def embed_batch(
        self,
        texts: List[str],
        task: str = "RETRIEVAL_DOCUMENT",
        dimensionality: Optional[int] = None
    ) -> List[List[float]]:
        """여러 텍스트를 배치로 임베딩"""
        try:
            # 설정 구성
            config = EmbedContentConfig(
                task_type=task,
                output_dimensionality=dimensionality or self._default_dimensionality
            )
            
            # 배치 임베딩 생성
            response = self.client.models.embed_content(
                model=self._model_name,
                contents=texts,
                config=config
            )
            
            return [embedding.values for embedding in response.embeddings]
            
        except Exception as e:
            logger.error(f"배치 임베딩 생성 실패: {e}")
            raise
    
    @property
    def model_name(self) -> str:
        """모델명 반환"""
        return self._model_name
    
    @property
    def need_translation(self) -> bool:
        """번역이 필요한지 여부 반환"""
        return self._need_translation
    
    @property
    def default_dimensionality(self) -> int:
        """기본 차원 수 반환"""
        return self._default_dimensionality
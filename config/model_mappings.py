"""
인덱스별 임베딩 모델 매핑 및 모델 관련 설정
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class EmbeddingModelInfo:
    """임베딩 모델 정보"""
    model_name: str
    need_translation: bool
    default_dimensionality: int
    supported_tasks: List[str]
    
    
# 임베딩 모델 정보 매핑
EMBEDDING_MODELS: Dict[str, EmbeddingModelInfo] = {
    "text-embedding-004": EmbeddingModelInfo(
        model_name="text-embedding-004",
        need_translation=True,  # 영어 전용
        default_dimensionality=768,
        supported_tasks=["RETRIEVAL_DOCUMENT"]
    ),
    "text-embedding-005": EmbeddingModelInfo(
        model_name="text-embedding-005", 
        need_translation=True,  # 영어 전용
        default_dimensionality=768,
        supported_tasks=["RETRIEVAL_DOCUMENT"]
    ),
    "text-multilingual-embedding-002": EmbeddingModelInfo(
        model_name="text-multilingual-embedding-002",
        need_translation=False,  # 다국어 지원
        default_dimensionality=768,
        supported_tasks=["RETRIEVAL_DOCUMENT"]
    )
}


# 인덱스별 임베딩 모델 매핑
INDEX_MODEL_MAPPING: Dict[str, str] = {
    "hdegis-text-embedding-004": "text-embedding-004",
    "hdegis-text-embedding-005": "text-embedding-005", 
    "hdegis-text-multilingual-embedding-002": "text-multilingual-embedding-002"
}


# 검색 메서드별 필수 필드 매핑
SEARCH_METHOD_REQUIREMENTS: Dict[str, List[str]] = {
    "vector": ["embedding_model_name", "vector_field"],
    "keyword": ["text_fields"],
    "hybrid": ["embedding_model_name", "vector_field", "text_fields"],
    "hyde": ["embedding_model_name", "vector_field"],
    "hyde_hybrid": ["embedding_model_name", "vector_field", "text_fields"]
}


# 기본 필드 설정
DEFAULT_FIELDS = {
    "vector_field": "embedding",
    "text_fields": ["extracted_text"]
}


def get_embedding_model_for_index(index_name: str) -> Optional[str]:
    """인덱스명으로부터 적절한 임베딩 모델을 반환"""
    return INDEX_MODEL_MAPPING.get(index_name)


def get_embedding_model_info(model_name: str) -> Optional[EmbeddingModelInfo]:
    """모델명으로부터 모델 정보를 반환"""
    return EMBEDDING_MODELS.get(model_name)


def validate_search_method_requirements(search_method: str, **kwargs) -> List[str]:
    """검색 메서드에 필요한 인자들이 제공되었는지 확인"""
    required_fields = SEARCH_METHOD_REQUIREMENTS.get(search_method, [])
    missing_fields = []
    
    for field in required_fields:
        if field not in kwargs or kwargs[field] is None:
            missing_fields.append(field)
    
    return missing_fields


def auto_configure_for_index(index_name: str, search_method: str, **kwargs) -> Dict:
    """인덱스명과 검색 메서드를 기반으로 자동 설정"""
    config = kwargs.copy()
    
    # 임베딩 모델 자동 설정
    if "embedding_model_name" not in config:
        auto_model = get_embedding_model_for_index(index_name)
        if auto_model:
            config["embedding_model_name"] = auto_model
    
    # 기본 필드 설정
    for field, default_value in DEFAULT_FIELDS.items():
        if field not in config:
            config[field] = default_value
    
    # 필수 필드 검증
    missing_fields = validate_search_method_requirements(search_method, **config)
    if missing_fields:
        raise ValueError(
            f"'{search_method}' 검색 메서드에 필요한 필드가 누락되었습니다: {missing_fields}"
        )
    
    return config
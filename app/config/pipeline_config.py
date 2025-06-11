"""
파이프라인 기본 설정 파일 - 보안이 필요하지 않은 설정들
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class SearchConfig:
    """검색 관련 설정"""
    # 핵심 검색 설정 (추가)
    index_name: str = "hdegis-text-multilingual-embedding-002"
    search_method: str = "keyword"  # keyword | vector | hybrid | hyde | hyde_hybrid
    top_k: int = 10
    tolerance: int = 3  # 페이지 확장 범위 (0이면 확장 안함)
    
    # 검색 상세 설정 (기존)
    vector_search_candidates: int = 100
    text_search_operator: str = "or"
    text_search_type: str = "best_fields"
    
    # 하이브리드 검색 가중치
    vector_weight: float = 0.3
    text_weight: float = 0.7


@dataclass
class GenerationConfig:
    """생성 관련 설정"""
    default_model: str = "gemini-2.0-flash-001"
    
    # 태스크별 설정
    keyword_generation: Dict[str, Any] = None
    hyde_generation: Dict[str, Any] = None
    answer_generation: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.keyword_generation is None:
            self.keyword_generation = {
                "model": self.default_model,
                "temperature": 0.1,
                "max_output_tokens": 256
            }
        
        if self.hyde_generation is None:
            self.hyde_generation = {
                "model": self.default_model,
                "temperature": 0.3,
                "max_output_tokens": 512
            }
            
        if self.answer_generation is None:
            self.answer_generation = {
                "model": self.default_model,
                "temperature": 0.7,
                "max_output_tokens": 2048
            }


@dataclass
class StorageConfig:
    """스토리지 관련 설정"""
    storage_type: str = "minio"  # minio | gcs
    bucket_name: str = "ksoe"
    local_temp_dir: str = "tmp"


@dataclass
class ContextConfig:
    """컨텍스트 구성 관련 설정"""
    context_type: str = "text"  # text | image | both
    text_field: str = "extracted_text"  # content | extracted_text
    

@dataclass
class ElasticsearchConfig:
    """Elasticsearch 관련 설정"""
    verify_certs: bool = False
    request_timeout: int = 30
    max_retries: int = 3
    retry_on_timeout: bool = True


@dataclass
class PipelineConfig:
    """전체 기본 설정을 통합하는 클래스"""
    search: SearchConfig = None
    generation: GenerationConfig = None
    storage: StorageConfig = None
    context: ContextConfig = None
    elasticsearch: ElasticsearchConfig = None
    
    def __post_init__(self):
        if self.search is None:
            self.search = SearchConfig()
        if self.generation is None:
            self.generation = GenerationConfig()
        if self.storage is None:
            self.storage = StorageConfig()
        if self.context is None:
            self.context = ContextConfig()
        if self.elasticsearch is None:
            self.elasticsearch = ElasticsearchConfig()


# # 전역 기본 설정 인스턴스
DEFAULT_CONFIG = PipelineConfig()


def get_default_pipeline_config() -> PipelineConfig:
    """기본 파이프라인 설정 반환"""
    return DEFAULT_CONFIG

def get_custom_pipeline_config() -> PipelineConfig:
    """커스텀 파이프라인 설정 반환"""

     # ========== 검색 설정 ==========
    search_config = SearchConfig(
        # 핵심 검색 설정
        index_name="hdegis-text-multilingual-embedding-002",  # 검색 인덱스
        search_method="hybrid",                               # 검색 방법 [keyword|vector|hybrid|hyde|hyde_hybrid]
        top_k=10,                                            # 검색 결과 개수
        tolerance=3,                                         # 페이지 확장 범위 (0이면 확장 안함)
        
        # 검색 상세 설정
        vector_search_candidates=100,                        # 벡터 검색 후보 수
        text_search_operator="or",                           # 텍스트 검색 연산자 [or|and]
        text_search_type="best_fields",                      # 텍스트 검색 타입
        vector_weight=0.4,                                   # 하이브리드 검색의 벡터 가중치
        text_weight=0.6,                                     # 하이브리드 검색의 텍스트 가중치
    )
    
    # ========== 생성 설정 ==========
    generation_config = GenerationConfig(
        default_model="gemini-2.0-flash-001",
        
        # 키워드 생성 설정
        keyword_generation={
            "model": "gemini-2.0-flash-001",
            "temperature": 0.1,
            "max_output_tokens": 256
        },
        
        # HyDE 문서 생성 설정
        hyde_generation={
            "model": "gemini-2.0-flash-001",
            "temperature": 0.3,
            "max_output_tokens": 512
        },
        
        # 최종 답변 생성 설정
        answer_generation={
            "model": "gemini-2.0-flash-001",
            "temperature": 0.7,
            "max_output_tokens": 2048
        }
    )
    
    # ========== 스토리지 설정 ==========
    storage_config = StorageConfig(
        storage_type="minio",                  # [minio|gcs]
        bucket_name="ksoe",
        local_temp_dir="tmp"
    )
    
    # ========== 컨텍스트 설정 ==========
    context_config = ContextConfig(
        context_type="text",                   # [text|image|both]
        text_field="extracted_text"            # [content|extracted_text]
    )
    
    # ========== Elasticsearch 설정 ==========
    elasticsearch_config = ElasticsearchConfig(
        verify_certs=False,
        request_timeout=30,
        max_retries=3,
        retry_on_timeout=True
    )
    
    # ========== 전체 설정 조합 ==========
    return PipelineConfig(
        search=search_config,
        generation=generation_config,
        storage=storage_config,
        context=context_config,
        elasticsearch=elasticsearch_config
    )
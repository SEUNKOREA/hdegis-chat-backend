"""
리팩토링된 RAG 파이프라인 사용 예시 - Config 중심 설계
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

import warnings
from urllib3.exceptions import InsecureRequestWarning
from dotenv import load_dotenv

# 경고 무시
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# 환경변수 로드
load_dotenv()

from app.factories import RAGPipelineFactory
from app.config.pipeline_config import PipelineConfig, SearchConfig, GenerationConfig, ContextConfig, StorageConfig, ElasticsearchConfig
from app.utils.formatters import format_search_results
import logging

# 로깅 설정 - 상세 로그는 DEBUG로 조정
def setup_logging():
    """로깅 설정 함수"""
    
    # 루트 로거 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )
    
    # 외부 라이브러리 로그 레벨을 WARNING으로 설정 (매우 상세한 로그 숨김)
    external_loggers = [
        'httpx',                    # HTTP 요청 로그 (POST, GET 등)
        'elastic_transport.transport',  # Elasticsearch 요청 로그 (매 POST 요청)
        'google_genai.models',      # Google AI 모델 AFC 로그
        'urllib3.connectionpool',   # HTTP 연결 풀 로그
        'requests.packages.urllib3.connectionpool'
    ]
    
    for logger_name in external_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)  # WARNING 이상만 출력
    
    # 주요 실행 단계는 INFO로 유지할 모듈들
    important_loggers = [
        'factories',                    # 팩토리 생성 로그
        'pipeline.rag_pipeline',        # RAG 파이프라인 실행 단계
        'pipeline.retriever',           # 검색 단계
        'pipeline.context_builder',     # 컨텍스트 구성 단계
        'pipeline.generator',           # 답변 생성 단계
        'utils.formatters',             # 실행 시간 측정
        'core.search.elastic_searcher', # Elasticsearch 연결/결과 요약
        'core.embedding.google_embedder', # 임베딩 모델 초기화
        'core.generation.gemini_generator', # 생성 모델 초기화
    ]
    
    for logger_name in important_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)  # INFO 레벨 유지

# 로깅 설정 적용
setup_logging()
logger = logging.getLogger(__name__)


def create_custom_config():
    """모든 설정 옵션을 명시적으로 설정한 커스텀 config 생성"""
    
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


def main():
    """메인 실행 함수 - 커스텀 설정 사용"""
    
    logger.info("🚀 커스텀 설정으로 RAG 파이프라인 초기화 중...")
    
    # ========== 커스텀 파이프라인 생성 ==========
    custom_config = create_custom_config()
    pipeline = RAGPipelineFactory.create_pipeline(config=custom_config)
    
    # 파이프라인 설정 확인
    logger.info(f"📋 현재 설정: {pipeline.get_config()}")
    
    # ========== 테스트 쿼리 설정 ==========
    user_query = "Are there any requirements regarding the operating method of the circuit breaker, such as spring-operated or hydraulic-operated?"
    user_filter = "3. Customer Standard Specifications/Spain/REE"
    
    # ========== 파이프라인 실행 (동적 데이터만) ==========
    logger.info("🔍 스트리밍 파이프라인 실행 중...")
    
    # 스트리밍 답변과 검색 결과를 함께 받기
    answer_stream, total_hits, original_hits = pipeline.run_stream(user_query, user_filter)
    
    # ========== 결과 출력 ==========
    print("\n" + "="*50 + " USER " + "="*50)
    print(f"Query: {user_query}")
    print(f"Filter: {user_filter}")
    
    print("\n" + "="*45 + " AI ASSISTANT " + "="*45)
    print("Answer:\n")
    
    # 스트리밍 답변 출력
    for chunk in answer_stream:
        print(chunk, end="", flush=True)
    
    print("\n\n")  # 답변 완료 후 줄바꿈
    
    print("\n" + "="*45 + " REFERENCE " + "="*46)
    print(f"Original hits: {len(original_hits)}")
    print(f"Total hits (with expansion): {len(total_hits)}")
    print(format_search_results(original_hits))
    
    print("\n" + "="*100)


if __name__ == "__main__":
    try:
        # 🚀 메인 실행 (스트리밍)
        main()
        
        logger.info("✅ 실행이 완료되었습니다!")
        
    except Exception as e:
        logger.error(f"❌ 실행 중 오류 발생: {e}")
        raise
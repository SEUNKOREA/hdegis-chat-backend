"""
컴포넌트 생성을 위한 팩토리 클래스들
"""

import logging
from typing import Optional

# Core 컴포넌트들
from app.core.storage.base_storage import BaseStorage
from app.core.storage.minio_storage import MinIOStorage
from app.core.storage.gcs_storage import GCSStorage
from app.core.search.base_searcher import BaseSearcher
from app.core.search.elastic_searcher import ElasticSearcher
from app.core.embedding.base_embedder import BaseEmbedder
from app.core.embedding.google_embedder import GoogleEmbedder
from app.core.generation.base_generator import BaseGenerator
from app.core.generation.gemini_generator import GeminiGenerator

# Pipeline 컴포넌트들
from app.pipeline.retriever import Retriever
from app.pipeline.context_builder import ContextBuilder
from app.pipeline.generator import Generator
from app.pipeline.rag_pipeline import RAGPipeline

# 유틸리티 컴포넌트들
from app.utils.input_processor import InputProcessor
from app.utils.query_enhancer import QueryEnhancer

# 설정
from app.config.pipeline_config import PipelineConfig, SearchConfig, DEFAULT_CONFIG
from app.config.secrets_config import SecretsConfig, load_secrets
from app.config.model_mappings import get_embedding_model_for_index

logger = logging.getLogger(__name__)


class StorageFactory:
    """스토리지 컴포넌트 팩토리"""
    
    @staticmethod
    def create_storage(
        storage_type: str,
        secrets: SecretsConfig,
        bucket_name: str
    ) -> BaseStorage:
        """
        스토리지 타입에 따른 스토리지 인스턴스 생성
        
        Args:
            storage_type: 스토리지 타입 ("minio", "gcs")
            secrets: 보안 설정
            bucket_name: 버킷명
            
        Returns:
            BaseStorage: 스토리지 인스턴스
        """
        if storage_type.lower() == "minio":
            return MinIOStorage(secrets.minio, bucket_name)
        elif storage_type.lower() == "gcs":
            return GCSStorage(secrets.google_cloud, bucket_name)
        else:
            raise ValueError(f"지원하지 않는 스토리지 타입: {storage_type}")


class SearcherFactory:
    """검색기 컴포넌트 팩토리"""
    
    @staticmethod
    def create_searcher(
        searcher_type: str,
        secrets: SecretsConfig,
        config: PipelineConfig
    ) -> BaseSearcher:
        """
        검색기 타입에 따른 검색기 인스턴스 생성
        
        Args:
            searcher_type: 검색기 타입 ("elasticsearch")
            secrets: 보안 설정
            config: 기본 설정
            
        Returns:
            BaseSearcher: 검색기 인스턴스
        """
        if searcher_type.lower() == "elasticsearch":
            return ElasticSearcher(secrets.elasticsearch, config.elasticsearch)
        else:
            raise ValueError(f"지원하지 않는 검색기 타입: {searcher_type}")


class EmbedderFactory:
    """임베딩 모델 팩토리"""
    
    @staticmethod
    def create_embedder(
        model_name: str,
        secrets: Optional[SecretsConfig] = None,
        provider: str = "google"
    ) -> BaseEmbedder:
        """
        임베딩 모델 인스턴스 생성
        
        Args:
            model_name: 모델명
            secrets: 보안 설정 (Google Cloud 인증용)
            provider: 제공업체 ("google")
            
        Returns:
            BaseEmbedder: 임베딩 모델 인스턴스
        """
        if provider.lower() == "google":
            google_secrets = secrets.google_cloud if secrets else None
            return GoogleEmbedder(model_name, google_secrets)
        else:
            raise ValueError(f"지원하지 않는 임베딩 제공업체: {provider}")


class GeneratorFactory:
    """생성 모델 팩토리"""
    
    @staticmethod
    def create_generator(
        secrets: SecretsConfig,
        default_model: str = "gemini-2.0-flash-001",
        provider: str = "google"
    ) -> BaseGenerator:
        """
        생성 모델 인스턴스 생성
        
        Args:
            secrets: 보안 설정
            default_model: 기본 모델명
            provider: 제공업체 ("google")
            
        Returns:
            BaseGenerator: 생성 모델 인스턴스
        """
        if provider.lower() == "google":
            return GeminiGenerator(secrets.google_cloud, default_model)
        else:
            raise ValueError(f"지원하지 않는 생성 제공업체: {provider}")


class RAGPipelineFactory:
    """RAG 파이프라인 팩토리"""
    
    @staticmethod
    def create_pipeline(
        config: Optional[PipelineConfig] = None,
        secrets: Optional[SecretsConfig] = None
    ) -> RAGPipeline:
        """
        완전한 RAG 파이프라인 생성 (config 기반)
        
        Args:
            config: 전체 설정 (None이면 기본값 사용)
            secrets: 보안 설정 (None이면 환경변수에서 로드)
            
        Returns:
            RAGPipeline: 완전히 구성된 RAG 파이프라인
        """
        # 설정 로드
        if config is None:
            config = DEFAULT_CONFIG
        if secrets is None:
            secrets = load_secrets()
        
        search_config = config.search
        logger.info(f"RAG 파이프라인 생성 시작: {search_config.search_method} 방식, {search_config.index_name} 인덱스")
        
        # 1. 기본 컴포넌트들 생성
        searcher = SearcherFactory.create_searcher("elasticsearch", secrets, config)
        generator_base = GeneratorFactory.create_generator(secrets, config.generation.default_model)
        
        # 2. 유틸리티 컴포넌트들 생성
        input_processor = InputProcessor()
        query_enhancer = QueryEnhancer(generator_base, input_processor)
        
        # 3. 임베딩 모델 생성 (벡터 검색 필요시)
        embedder = None
        if search_config.search_method in ("vector", "hybrid", "hyde", "hyde_hybrid"):
            # 인덱스에서 자동으로 모델 결정
            embedding_model = get_embedding_model_for_index(search_config.index_name)
            
            if embedding_model:
                embedder = EmbedderFactory.create_embedder(embedding_model, secrets)
                logger.info(f"임베딩 모델 설정: {embedding_model}")
            else:
                raise ValueError(f"인덱스 {search_config.index_name}에 대한 임베딩 모델을 찾을 수 없습니다")
        
        # 4. 스토리지 생성 (이미지 컨텍스트 사용시)
        storage = None
        if config.context.context_type in ("image", "both"):
            storage = StorageFactory.create_storage(
                config.storage.storage_type,
                secrets,
                config.storage.bucket_name
            )
        
        # 5. 파이프라인 컴포넌트들 조립
        retriever = Retriever(
            searcher=searcher,
            embedder=embedder,
            query_enhancer=query_enhancer,
            input_processor=input_processor,
            config=search_config  # SearchConfig 전달
        )
        
        context_builder = ContextBuilder(
            storage=storage,
            config=config.context
        )
        
        generator = Generator(
            generator=generator_base,
            config=config.generation
        )
        
        # 6. 최종 파이프라인 조립 (config 기반)
        pipeline = RAGPipeline(
            retriever=retriever,
            context_builder=context_builder,
            generator=generator
        )
        
        logger.info("RAG 파이프라인 생성 완료")
        return pipeline
    
    @staticmethod
    def create_simple_pipeline(
        index_name: str = "hdegis-text-multilingual-embedding-002",
        search_method: str = "keyword",
        top_k: int = 10,
        tolerance: int = 3
    ) -> RAGPipeline:
        """
        간단한 설정으로 RAG 파이프라인 생성
        
        Args:
            index_name: 검색할 인덱스명
            search_method: 검색 방법
            top_k: 검색 결과 수
            tolerance: 페이지 확장 범위
            
        Returns:
            RAGPipeline: RAG 파이프라인
        """
        # 간단한 설정으로 PipelinConfig 생성
        config = PipelineConfig(
            search=SearchConfig(
                index_name=index_name,
                search_method=search_method,
                top_k=top_k,
                tolerance=tolerance
            )
        )
        
        return RAGPipelineFactory.create_pipeline(config=config)
# hdegis-chat-backend

고압차단기 사내문서기반 QA 챗봇 백엔드 API

## Project Structure

```
hdegis-chat-backend/
├── README.md
├── .env
├── .gitignore
├── requirements.txt
│
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI 앱 진입점
│   │
│   ├── models/                      # 데이터 모델
│   │   ├── __init__.py
│   │   └── schemas.py               # Pydnatic 스키마
│   │
│   ├── api/                         # API 관련
│   │   ├── __init__.py
│   │   ├── dependencies.py          # FastAPI 의존성 주입
│   │   └── routes/                  # API 라우트
│   │       ├── __init__.py
│   │       └── chat.py              # 채팅 엔드포인트
│   │
│   ├── services/                    # 비즈니스 로직
│   │   ├── __init__.py
│   │   └── chat_service.py          # 채팅 서비스
│   │
│   ├── config/
│   │   ├── app_config.py            # 앱 기본 설정
│   │   ├── pipeline_config.py       # 파이프라인 설정
│   │   ├── secrets_config.py        # 보안 설정 (환경변수)
│   │   └── model_mappings.py        # 인덱스-임베딩모델 매핑
│   │
│   ├── pipeline/
│   │   ├── rag_pipeline.py          # RAG 통합 파이프라인
│   │   ├── retriever.py             # Retriever 모듈
│   │   ├── context_builder.py       # ContextBuilder 모듈
│   │   └── generator.py             # Generator 모듈
│   │
│   ├── core/
│   │   ├── storage/
│   │   │   ├── base_storage.py      # 스토리지 추상화
│   │   │   ├── gcs_storage.py       # GCS 구현
│   │   │   └── minio_storage.py     # MinIO 구현
│   │   ├── embedding/
│   │   │   ├── base_embedder.py     # 임베딩 추상화
│   │   │   └── google_embedder.py   # Google 임베딩 구현
│   │   ├── search/
│   │   │   ├── base_searcher.py     # 검색 추상화
│   │   │   └── elastic_searcher.py  # ElasticSearch 구현
│   │   └── generation/
│   │       ├── base_generator.py    # Generator 추상화
│   │       └── gemini_generator.py  # Gemini 구현
│   │
│   ├── utils/
│   │   ├── filter_builder.py        # 검색 필터 구성
│   │   ├── formatters.py            # 결과 포맷팅
│   │   ├── input_processor.py       # 입력 처리 (번역 등)
│   │   └── query_enhancer.py        # 쿼리향상 (키워드 생성, HyDE)
│   │
│   ├── factories.py                 # 컴포넌트 팩토리
│   └── main_console.py              # 콘솔 테스트 스크립트
│
└── key                              # GCP 인증 키 파일
    └── gcp_credentials.json
```

<br><br>

## Quick start

### 1. Setup

#### .env 파일 생성

```
# Elasticsearch
ES_HOST=your-elasticsearch-host
ES_USER=your-username
ES_PASSWORD=your-password

# Google Cloud
PROJECT_ID=your-project-id
LOCATION=your-location
GOOGLE_APPLICATION_CREDENTIALS=./key/gcp-service-key.json

# MinIO
MINIO_HOST=minio.hd-aic.com
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
```

#### 의존성 설치

```
conda create -n hdegis-chat-py12 python=3.12
conda activate hdegis-chat-py12
pip install -r requirements.txt
```

### 2. RAG Pipeline Configuration

#### 기본 및 커스텀 설정

```python
# ========================================
# app/api/dependencies.py
# ========================================

# ... (중략) ...
@lru_cache()
def get_chat_service() -> ChatService:
    """
    ChatService 싱글톤 인스턴스 반환

    Returns:
        ChatService 인스턴스
    """
    try:
        # TODO: 원하는 설정에 따라서 주석 해제하여 사용
        # 커스텀 설정
        pipeline_config = get_custom_pipeline_config()
        return ChatService(pipeline_config)

        # # 기본설정
        # return ChatService()

    except Exception as e:
        logger.error(f"ChatService 초기화 실패: {e}")
        raise

```

#### 커스텀 설정 (원하는 설정 값 사용)

```python
# ========================================
# app/config/pipeline_config.py
# ========================================

def get_custom_pipeline_config() -> PipelineConfig:

    # ========== 검색 설정 ==========
    search_config = SearchConfig(
        # ... (중략) ...
    )

    # ========== 생성 설정 ==========
    generation_config = GenerationConfig(
        # ... (중략) ...
    )

    # ========== 스토리지 설정 ==========
    storage_config = StorageConfig(
        # ... (중략) ...
    )

    # ========== 컨텍스트 설정 ==========
    context_config = ContextConfig(
        # ... (중략) ...
    )

    # ========== Elasticsearch 설정 ==========
    elasticsearch_config = ElasticsearchConfig(
        # ... (중략) ...
    )

    # ========== 전체 설정 조합 ==========
    return PipelineConfig(
        search=search_config,
        generation=generation_config,
        storage=storage_config,
        context=context_config,
        elasticsearch=elasticsearch_config
    )

```

### 3. Run

```bash
# 개발 서버 실행
python app/main.py

# 또는 uvicorn 직접 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 5003

# RAG Pipeline 콘솔 스크립트 실행
python app/main_console.py
```

<br><br>

## Supported search enigine (method)

| 검색 방법       | 설명                          | 필수 요소                                  |
| --------------- | ----------------------------- | ------------------------------------------ |
| **keyword**     | 키워드 기반 텍스트 검색       | text_fields                                |
| **vector**      | 임베딩 벡터 기반 의미 검색    | embedding_model, vector_field              |
| **hybrid**      | 키워드 + 벡터 하이브리드 검색 | embedding_model, vector_field, text_fields |
| **hyde**        | HyDE 가상문서 기반 벡터 검색  | embedding_model, vector_field              |
| **hyde_hybrid** | HyDE + 키워드 하이브리드 검색 | embedding_model, vector_field, text_fields |

<br><br>

## 확장방법

### 새로운 검색 엔진 추가

1. `core/search/base_searcher.py`의 BaseSearcher 인터페이스 구현
2. `factories.py`의 SearcherFactory에 새 구현체 등록

```python
class YourCustomSearcher(BaseSearcher):
    def keyword_search(self, ...):
        # 구현
        pass
```

### 새로운 임베딩 모델 추가

1. `core/embedding/base_embedder.py`의 BaseEmbedder 인터페이스 구현
2. `config/model_mappings.py`에 모델 정보 추가

### 새로운 스토리지 추가

1. `core/storage/base_storage.py`의 BaseStorage 인터페이스 구현
2. `factories.py`의 StorageFactory에 새 구현체 등록

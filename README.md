# hdegis-chat-backend

## Project structure

```
hdegis-chat-backend/
├── 📁 config/
│   ├── base_config.py          # 기본 설정 클래스들
│   ├── secrets_config.py       # 보안 설정 (환경변수)
│   └── model_mappings.py       # 인덱스-임베딩 모델 매핑
│
├── 📁 core/
│   ├── 📁 storage/
│   │   ├── base_storage.py     # 스토리지 추상화
│   │   ├── minio_storage.py    # MinIO 구현
│   │   └── gcs_storage.py      # GCS 구현
│   ├── 📁 search/
│   │   ├── base_searcher.py    # 검색 추상화
│   │   └── elastic_searcher.py # Elasticsearch 구현
│   ├── 📁 embedding/
│   │   ├── base_embedder.py    # 임베딩 추상화
│   │   └── google_embedder.py  # Google 임베딩 구현
│   └── 📁 generation/
│       ├── base_generator.py   # 생성 추상화
│       └── gemini_generator.py # Gemini 구현
│
├── 📁 pipeline/
│   ├── retriever.py           # 검색 로직
│   ├── context_builder.py     # 컨텍스트 구성
│   ├── generator.py           # 답변 생성
│   └── rag_pipeline.py        # 통합 파이프라인
│
├── 📁 utils/
│   ├── input_processor.py     # 입력 처리 (번역 등)
│   ├── query_enhancer.py      # 쿼리 향상 (키워드, HyDE)
│   ├── filter_builder.py      # 검색 필터 구성
│   └── formatters.py          # 결과 포맷팅
│
├── 📁 key/                    # GCP 인증 키 파일
│   └── gcp-service-key.json
│
├── factories.py               # 팩토리 패턴 구현
├── main.py                    # 메인 실행 파일
│
├── .env                       # 환경변수 설정
├── .gitignore
├── requirements.txt
└── README.md
```

<br><br>

## Quick start

### 1. Setup

#### 필요한 환경변수 (.env 파일 생성)

```bash
# Elasticsearch
ES_HOST=your-elasticsearch-host
ES_USER=your-username
ES_PASSWORD=your-password

# Google Cloud
PROJECT_ID=your-project-id
LOCATION=your-location
GOOGLE_APPLICATION_CREDENTIALS=./key/gcp-service-key.json

# MinIO (선택적)
MINIO_HOST=minio.hd-aic.com
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
```

#### 의존성 설치

```bash
conda create -n hdegis-chat-py12 python=3.12
conda activate hdegis-chat-py12
pip install -r requirements.txt
```

### 2. Configuration

#### 기본 설정

```python
from factories import RAGPipelineFactory

# 간단한 파이프라인 생성
pipeline = RAGPipelineFactory.create_simple_pipeline(
    index_name="your-index-name",
    search_method="hybrid",
    top_k=10,
    tolerance=3  # 페이지 확장 범위
)

# 실행 (동적 데이터만 전달)
answer, total_hits, original_hits = pipeline.run(
    user_query="사용자 질문",
    user_filter="검색 필터"
)
```

#### 커스텀 설정

```python
from config.base_config import BaseConfig, SearchConfig, GenerationConfig
from factories import RAGPipelineFactory

# 커스텀 설정
config = BaseConfig(
    search=SearchConfig(
        index_name="your-index-name",
        search_method="hybrid",
        top_k=15,
        tolerance=5,
        vector_weight=0.4,
        text_weight=0.6
    ),
    generation=GenerationConfig(
        answer_generation={
            "temperature": 0.7,
            "max_output_tokens": 2048
        }
    )
)

# 설정 기반 파이프라인 생성
pipeline = RAGPipelineFactory.create_pipeline(config=config)

# 실행
answer, total_hits, original_hits = pipeline.run("질문", "필터")
```

### 3. Run

```bash
# 메인 실행
python main.py
```

<br><br>

## Supported search method

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

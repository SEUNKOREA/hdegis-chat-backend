import os
from typing import List, Optional, Dict, Tuple, Any

from google import genai
from google.genai import types
from elasticsearch import Elasticsearch

from elastic_helpers import ESSearch
from prompts import BASIC_RAG_PROMPT, BASIC_RAG_PROMPT_2
from utils import timed

class Retriever:
    def __init__(
        self,
        index_name: str,
        top_k: int,
        search_method: str,   # vector | keyword | hybrid | hyde | hyde_hybrid
        **kwargs              # embedding_model_name, vector_field, text_fields 등 search_method에 맞는 인자들
    ):
        # --- 검색 클래스 초기화 ---
        es_host = os.getenv("ES_HOST")
        es_user = os.getenv("ES_USER")
        es_pass = os.getenv("ES_PASSWORD")
        if not all([es_host, es_user, es_pass]):
            raise EnvironmentError("ES_HOST, ES_USER, ES_PASSWORD must be set")
        self.es = ESSearch(hosts=es_host, credentials=(es_user, es_pass))

        # --- 고정 파라미터 저장 ---
        self.index_name    = index_name
        self.top_k         = top_k
        self.search_method = search_method

        # --- 동적 파라미터 ---
        self.embedding_model_name = kwargs.get("embedding_model_name")
        self.vector_field         = kwargs.get("vector_field", "embedding")
        self.text_fields          = kwargs.get("text_fields", ["content"])

        # --- 필수 인자 체크 ---
        required = []
        if search_method in ("vector", "hyde", "hyde_hybrid", "hybrid"):
            required.append("embedding_model_name")
        if search_method in ("keyword", "hybrid", "hyde_hybrid"):
            required.append("text_fields")
        missing = [r for r in required if getattr(self, r) is None]
        if missing:
            raise ValueError(f"'{search_method}' 검색에 필요한 인자가 없습니다: {missing}")
    
    def search(
        self,
        user_query: str,
        user_filter: str,
    )-> List[dict]:
        
        # --- ES 메서드 매핑 ---
        func_name = {
            "vector":       "vector_search_w_filter",
            "keyword":      "keyword_text_search_w_filter",
            "hybrid":       "hybrid_search_w_filter",
            "hyde":         "hyde_vector_search_w_filter",
            "hyde_hybrid":  "hyde_hybrid_search_w_filter",
        }[self.search_method]
        func = getattr(self.es, func_name)

        # --- 공통 인자 ---
        args: Dict[str, Any] = {
            "index_name":  self.index_name,
            "top_k":       self.top_k,
            "user_query":  user_query,
            "user_filter": user_filter,
        }

        # --- 벡터 검색 계열 인자 ---
        if self.search_method in ("vector", "hyde", "hyde_hybrid", "hybrid"):
            args["embedding_model_name"] = self.embedding_model_name
            args["vector_field"]         = self.vector_field

        # --- 키워드 검색 계열 인자 ---
        if self.search_method in ("keyword", "hybrid", "hyde_hybrid"):
            args["text_fields"] = self.text_fields

        # --- Execute ---
        resp = func(**args)
        return resp["hits"]["hits"]
        # return resp    
    
    def expand_results(
        self,
        hits: List[dict],
        tolerance: int,
    ):
        expanded_hits = []
        seen_ids = {hit["_id"] for hit in hits}

        # 각 원본 hit별로 delta→[hits] 매핑
        per_hit_deltas: List[Tuple[Dict[str, Any], Dict[int, List[Dict[str, Any]]]]] = []


        for hit in hits:
            # --- 1. 검색결과 정보 취합 ---
            src = hit.get("_source", {})
            folder_levels = src.get("folder_levels", [])
            pdf_name = src.get("pdf_name", "")
            page_str = src.get("page", "")
            if not(folder_levels and pdf_name and page_str):
                continue
            
            # --- 2. 페이지 확장 ---
            page_num = int(page_str)
            delta_map: Dict[int, List[Dict[str, Any]]] = {}
            for delta in range(-tolerance, tolerance+1):
                if delta == 0: 
                    continue
                new_num = page_num + delta
                if new_num < 0:
                    continue
                new_page = f"{new_num:05d}"

                # --- 3. 확장된 페이지 조회 ---
                must_clauses: List[Dict[str, Any]] = [
                    {"terms": {"folder_levels.keyword": folder_levels}},
                    {"term": {"pdf_name.keyword": pdf_name}},
                    {"term": {"page.keyword": new_page}}
                ]

                body = {
                    "query": {
                        "bool": {
                            "must": must_clauses
                        }
                    }
                }

                resp = self.es.conn.search(index=self.index_name, body=body)
                new_hits: List[Dict[str, Any]] = []
                for nh in resp.get("hits", {}).get("hits", []):
                    nid = nh.get("_id")
                    if nid and nid not in seen_ids:
                        nh["_score"] = -1
                        seen_ids.add(nid)
                        expanded_hits.append(nh)
                        new_hits.append(nh)
                delta_map[delta] = new_hits    
            per_hit_deltas.append((hit, delta_map))

        total_hits: List[Dict[str, Any]] = []
        for orig_hit, delta_map in per_hit_deltas:
            # 음수 델타 (앞 페이지) 부터
            for d in sorted(k for k in delta_map if k < 0):
                total_hits.extend(delta_map[d])
            # 원본
            total_hits.append(orig_hit)
            # 양수 델타 (뒷 페이지)
            for d in sorted(k for k in delta_map if k > 0):
                total_hits.extend(delta_map[d])


            # page_num = int(page_str)
            # for delta in range(-tolerance, tolerance+1):
            #     if delta == 0: 
            #         continue
            #     new_num = page_num + delta
            #     if new_num < 0:
            #         continue
            #     new_page = f"{new_num:05d}"
    
            #     # --- 3. 확장된 페이지 조회 ---
            #     must_clauses: List[Dict[str, Any]] = [
            #         {"terms": {"folder_levels.keyword": folder_levels}},
            #         {"term": {"pdf_name.keyword": pdf_name}},
            #         {"term": {"page.keyword": new_page}}
            #     ]

            #     body = {
            #         "query": {
            #             "bool": {
            #                 "must": must_clauses
            #             }
            #         }
            #     }

            #     resp = self.es.conn.search(index=self.index_name, body=body)
            #     for new_hit in resp.get("hits", {}).get("hits", []):
            #         nid = new_hit.get("_id")
            #         if nid and nid not in seen_ids:
            #             expanded_hits.append(new_hit)
            #             seen_ids.add(nid)

            # break # 검색결과 1개에 대한 처리 (전체 검색결과 보려면 주석 해제)
        
        return expanded_hits, total_hits

class ContextBuilder:
    def __init__(self, context_type: str="text"):
        """
        context_type: text | image | both 중 하나
        """
        self.context_type = context_type
        if context_type in ("image", "both"):
            # ---- (temp) MinIO ----
            # 추후에 gcs client로 변경할 예정 ..? 아마두
            from minio import Minio
            MINIO_HOST="minio.hd-aic.com"    
            MINIO_ACCESS_KEY="6ftl2BdYL5SxGTLx2HdT"
            MINIO_SECRET_KEY="toBUVQn70l4gcsD382mEqjBregeug7koYWRPcfa7"
            
            self.minio_client = Minio(
                    MINIO_HOST,
                    access_key=MINIO_ACCESS_KEY,
                    secret_key=MINIO_SECRET_KEY,
                    secure=True    
                )
            self.minio_bucket_name="ksoe"

    def build(self, hits: List[dict]) ->List[types.Part]:
        parts: List[types.Part] = []

        for hit in hits:
            src = hit["_source"]

            if self.context_type in ("text", "both"):
                # --- 1. 텍스트 컨텍스트 가져오기 ---
                # text_data = src["content"]
                text_data = src["extracted_text"]
                # --- 2. 텍스트 파트 생성 --- 
                text_part = types.Part.from_text(text=text_data)
                parts.append(text_part)

            if self.context_type in ("image", "both"):
                # --- 1. minio에 있는 이미지를 임시 경로에 다운로드 받음 ---
                minio_image_path = hit['_source']['minio_image_path']
                local_image_path = os.path.join("tmp", os.path.basename(minio_image_path))
                self.minio_client.fget_object(bucket_name="ksoe", object_name=minio_image_path, file_path=local_image_path)
                
                # --- 2. 이미지 파트 생성 ---
                with open(local_image_path, "rb") as f:
                    local_image_bytes = f.read()
                image_part = types.Part.from_bytes(data=local_image_bytes, mime_type="image/png")
                parts.append(image_part)
        
        return parts

class Generator:
    def __init__(self):
        project_id = os.getenv("PROJECT_ID")
        location = os.getenv("LOCATION")
        self.genai_client = genai.Client(vertexai=True, project=project_id, location=location)
    
    def generate_answer(self, user_query: str, context_parts: List[types.Part]) -> str:
        # --- Gemini한테 요청보낼 최종 프롬프트 만들기 (검색된 결과 포함) ---
        prompt = [
            types.Part.from_text(text=BASIC_RAG_PROMPT.strip()),
            types.Part.from_text(text="Context:\n"),
            *context_parts,
            types.Part.from_text(text=f"Query:\n{user_query}"),
            types.Part.from_text(text=BASIC_RAG_PROMPT_2.strip()),
        ]

        resp = self.genai_client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=prompt
        )
        return resp.text

class RAGPipeline:
    def __init__(
        self,
        retriever: Retriever,
        context_builder: ContextBuilder,
        generator: Generator,
    ):
        self.retriever       = retriever
        self.context_builder = context_builder
        self.generator       = generator

    def search(
        self,
        user_query: str,
        user_filter: str, 
    ):
        return self.retriever.search(user_query, user_filter)

    def build_context(
        self,
        hits: List[dict]
    )-> List[types.Part]:
        return self.context_builder.build(hits)

    def generate_answer(
        self,
        user_query: str,        
        context_parts: List[types.Part],
            
    )-> str:
        return self.generator.generate_answer(user_query, context_parts)

    def run(
        self,
        user_query: str,
        user_filter: str,      
    )-> Tuple[str, List[dict]]:
        print("\n\n")
        hits = timed("Retrieval", self.search, user_query, user_filter)
        expanded_hits, total_hits = timed("Docuemnts Loading", self.retriever.expand_results, hits, 3)
        context_parts = timed("Context Building", self.build_context, total_hits)
        generated_answer = timed("Answer Generation", self.generate_answer, user_query, context_parts)
        # hits = self.search(user_query, user_filter)
        # expanded_hits, total_hits = self.retriever.expand_results(hits, 3)
        # context_parts = self.build_context(total_hits)
        # generated_answer = self.generate_answer(context_parts, user_query)
        return generated_answer, total_hits, hits


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    import warnings
    from urllib3.exceptions import InsecureRequestWarning
    warnings.filterwarnings('ignore', category=InsecureRequestWarning)

    # ========== Retriever 모듈 초기화 ==========
    retriever = Retriever(
        index_name="hdegis-text-multilingual-embedding-002",
        top_k=10,
        search_method="hybrid",
        embedding_model_name="text-multilingual-embedding-002",
        vector_field="embedding",
        text_fields=["content"],
    )
    # user_query = "Are there any requirements regarding the operating method of the circuit breaker, such as spring-operated or hydraulic-operated?"
    # user_filter = "3. Customer Standard Specifications/Spain/REE"
    # retrieved_results = retriever.search(user_query, user_filter)
    # print(retrieved_results)

    # ========== ContextBuilder 모듈 초기화 ==========
    context_builder = ContextBuilder(context_type="text")

    # ========== Generator 모듈 초기화 ==========
    generator = Generator()

    # ========== Pipeline 조립 ==========
    pipeline = RAGPipeline(retriever, context_builder, generator)

    
    # ========== Pipeline 통합 실행 ==========
    user_query = "Are there any requirements regarding the operating method of the circuit breaker, such as spring-operated or hydraulic-operated?"
    user_filter = "3. Customer Standard Specifications/Spain/REE"
    generated_answer, total_hits, hits = pipeline.run(user_query, user_filter)


    print("\n===========================================<<  USER  >>=================================================\n")
    print(f"User: \n{user_query}")
    print(f"Filter: {user_filter}")
    print("\n========================================<< AI assitant >>==============================================\n")
    print(f"AI assitant:\n\n{generated_answer}\n")
    print("\n=========================================<<  Reference >>===============================================\n")
    print("[Search Results]")
    for i, hit in enumerate(hits, start=1):
        name = hit['_source']['gcs_pdf_path']
        page = int(hit['_source']['page_number'])
        score = hit['_score']
        print(f"[{i:02d}] {name, page} (score: {score})")
    print("\n============================================================================================================")


    # ========== Pipeline 모듈별 실행 ==========
    # user_query = "Are there any requirements regarding the operating method of the circuit breaker, such as spring-operated or hydraulic-operated?"
    # user_filter = "3. Customer Standard Specifications/Spain/REE"
    
    # hits = pipeline.search(user_query, user_filter)
    # context_parts = pipeline.build_context(hits)
    # generated_answer = pipeline.generate_answer(user_query, context_parts)
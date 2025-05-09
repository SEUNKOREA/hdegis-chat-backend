import os
from google import genai
from google.genai import types

from elastic_helpers import ESSearch
from prompts import BASIC_RAG_PROMPT, BASIC_RAG_PROMPT_2

class RAGPipeline:
    def __init__(
            self,
            # --- 1. 검색관련 설정 ---
            index_name: str,                # 공통
            top_k: int,                     # 공통
            search_method: str = "hybrid",  # vector | keyword | hybrid | hyde | hyde_hybrid
            embedding_model_name: str = None,
            vector_field: str = "embedding",
            text_fields: list = ["content"],

            # --- 2. 생성관련 설정 ---
            tolerance: int = 0,
            context_mode: str = "text",     # text | image | both
    ):
        # --- 검색 클래스 초기화 ---
        es_host = os.getenv("ES_HOST")
        es_user = os.getenv("ES_USER")
        es_pass = os.getenv("ES_PASSWORD")
        if not all([es_host, es_user, es_pass]):
            raise EnvironmentError("ES_HOST, ES_USER, ES_PASSWORD must be set")
        self.es = ESSearch(hosts=es_host, credentials=(es_user, es_pass))

        # -- 검색 설정값 저장 --
        self.index_name = index_name
        self.top_k = top_k
        self.search_method = search_method
        self.embedding_model_name = embedding_model_name
        self.vector_field = vector_field
        self.text_fields = text_fields

        # --- 생성 클라이언트 초기화 --
        project_id = os.getenv("PROJECT_ID")
        location = os.getenv("LOCATION")
        self.genai_client = genai.Client(vertexai=True, project=project_id, location=location)

        # --- 생성 설정값 저장 --
        self.tolerance = tolerance
        self.context_mode = context_mode


        # --- (temp) MinIO ---
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
    
    def _invoke_search(self, user_query: str, user_filter: str):
        print(f"[Search] method={self.search_method}, invoke search")
        # --- ESSearch function mapping ---
        m = self.search_method
        func = getattr(self.es, {
            "vector":       "vector_search_w_filter",
            "keyword":      "keyword_text_search_w_filter",
            "hybrid":       "hybrid_search_w_filter",
            "hyde":         "hyde_vector_search_w_filter",
            "hyde_hybrid":  "hyde_hybrid_search_w_filter",
        }[m])

        # --- 함수 공통 인자 ---
        kwargs = {
            "index_name": self.index_name,
            "top_k":      self.top_k,
            "user_query": user_query,
            "user_filter": user_filter,
        }

        # --- 각 함수별 추가 인자 ---
        if m in ("vector","hyde"):
            kwargs.update({
                "embedding_model_name": self.embedding_model_name,
                "vector_field": self.vector_field
            })
        elif m == "keyword":
            kwargs["text_fields"] = self.text_fields
        elif self.search_method in ["hybrid", "hyde_hybrid"]:
            kwargs.update({
                "embedding_model_name": self.embedding_model_name,
                "vector_field": self.vector_field,
                "text_fields": self.text_fields
            })
        
        # --- Execute search ---
        resp = func(**kwargs)
        hits = resp['hits']['hits']
        print(f"[Search] retrieved {len(hits)} hits")
        return hits

    def _expand_hits(self, hits): 
        return hits

    def _build_context(self, hits):
        print(f"[Context] mode={self.context_mode}, building from {len(hits)} hits")

        parts = []
        cnt_t, cnt_i = 0, 0
        for hit in hits:
            if self.context_mode in ("text", "both"):
                # --- 1. 텍스트 컨텍스트 가져오기 ---
                text_data = hit['_source']['content']
                
                # --- 2. 텍스트 파트 생성 --- 
                text_part = types.Part.from_text(text=text_data)
                parts.append(text_part)
                cnt_t += 1
            
            if self.context_mode in ("image", "both"):
                ########### 나중에 이부분 gcs uri로 처리하도록 수정해야함. ###########

                # --- 1. minio에 있는 이미지를 임시 경로에 다운로드 받음 ---
                minio_image_path = hit['_source']['minio_image_path']
                local_image_path = os.path.join("tmp", os.path.basename(minio_image_path))
                self.minio_client.fget_object(bucket_name="ksoe", object_name=minio_image_path, file_path=local_image_path)

                # --- 2. 이미지 파트 생성 ---
                with open(local_image_path, "rb") as f:
                    local_image_bytes = f.read()
                image_part = types.Part.from_bytes(data=local_image_bytes, mime_type="image/png")
                parts.append(image_part)
                cnt_i += 1

        print(f"[Context] built {len(parts)} parts (TEXT: {cnt_t}, IMAGE: {cnt_i})")
        return parts       

    def _generate_response(self, context: list, user_query: str) -> str:
        # --- Gemini한테 요청보낼 최종 프롬프트 만들기 (검색된 결과 포함) ---
        prompt = [
            types.Part.from_text(text=BASIC_RAG_PROMPT.strip()),
            types.Part.from_text(text="Context:\n"),
            *context,
            types.Part.from_text(text=f"Query:\n{user_query}"),
            types.Part.from_text(text=BASIC_RAG_PROMPT_2.strip()),
        ]

        print("[Generate] calling Gemini model...")        
        resp = self.genai_client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=prompt
        )
        print("[Generate] received response")
        return resp.text

    def run(self, user_query: str, user_filter: str) -> str:
        """
        1) 검색
        2) hits 확장 (tolerance)
        3) context 생성
        4) Gemini 생성
        5) 텍스트 리턴
        """
        print(f"\n[Run] start RAG\n- query: {user_query}\n- filter: {user_filter}")
        raw_hits = self._invoke_search(user_query, user_filter)
        hits = self._expand_hits(raw_hits) # 지금은 검색결과 그대로 전달함
        context = self._build_context(hits)
        answer = self._generate_response(context, user_query)
        print(f"[Run] done, return answer\n\n\n")
        return answer, hits

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    import warnings
    from urllib3.exceptions import InsecureRequestWarning
    warnings.filterwarnings('ignore', category=InsecureRequestWarning)

    pipeline = RAGPipeline(
        index_name="hde_hvcb_text_004",
        top_k=10,
        search_method="hybrid",
        embedding_model_name="text-embedding-004",
        vector_field="embedding",
        text_fields=["content"],
        tolerance=0,
        context_mode="both",
    )


    user_query = "Are there any requirements regarding the operating method of the circuit breaker, such as spring-operated or hydraulic-operated?"
    user_filter = "3. Customer Standard Specifications/Spain/REE"
    answer = pipeline.run(user_query, user_filter)
    
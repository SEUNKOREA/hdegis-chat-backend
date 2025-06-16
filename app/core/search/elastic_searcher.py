"""
Elasticsearch 검색기 구현
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from elasticsearch import Elasticsearch

from app.core.search.base_searcher import BaseSearcher
from app.config.secrets_config import ElasticsearchSecrets
from app.config.pipeline_config import ElasticsearchConfig

logger = logging.getLogger(__name__)


class ElasticSearcher(BaseSearcher):
    """Elasticsearch 구현"""
    
    def __init__(self, secrets: ElasticsearchSecrets, config: ElasticsearchConfig):
        """
        Elasticsearch 클라이언트 초기화
        
        Args:
            secrets: Elasticsearch 인증 정보
            config: Elasticsearch 설정
        """
        self.conn = Elasticsearch(
            hosts=[secrets.host],
            basic_auth=secrets.get_credentials(),
            verify_certs=config.verify_certs,
            request_timeout=config.request_timeout,
            max_retries=config.max_retries,
            retry_on_timeout=config.retry_on_timeout
        )
        
        # 연결 테스트
        if not self.ping():
            raise ConnectionError(f"Elasticsearch 연결 실패: {secrets.host}")
        
        logger.info(f"Elasticsearch 연결 성공: {secrets.host}")
    
    def ping(self) -> bool:
        """연결 상태 확인"""
        try:
            return self.conn.ping()
        except Exception as e:
            logger.error(f"Elasticsearch ping 실패: {e}")
            return False
    
    def keyword_search(
        self,
        index_name: str,
        query: str,
        text_fields: List[str],
        top_k: int,
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """키워드 검색 구현"""
        try:
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": text_fields,
                        "type": "best_fields",
                        "operator": "or"
                    }
                }
            }
            
            # 필터 적용
            if filters:
                search_body["query"] = {
                    "bool": {
                        "must": search_body["query"],
                        "filter": {
                            "bool": {
                                "should": filters,
                                "minimum_should_match": 1
                            }
                        }
                    }
                }
            
            response = self.conn.search(
                index=index_name, 
                body=search_body, 
                size=top_k
            )
            
            hits = response["hits"]["hits"]
            logger.debug(f"키워드 검색 완료: {len(hits)}개 결과")
            return hits
            
        except Exception as e:
            logger.error(f"키워드 검색 실패: {e}")
            raise
    
    def vector_search(
        self,
        index_name: str,
        query_vector: List[float],
        vector_field: str,
        top_k: int,
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """벡터 검색 구현"""
        try:
            search_body = {
                "knn": {
                    "field": vector_field,
                    "query_vector": query_vector,
                    "k": top_k,
                    "num_candidates": 100
                }
            }
            
            # 필터 적용
            if filters:
                search_body["knn"]["filter"] = {
                    "bool": {
                        "should": filters,
                        "minimum_should_match": 1
                    }
                }
            
            response = self.conn.search(
                index=index_name,
                body=search_body,
                size=top_k
            )
            
            hits = response["hits"]["hits"]
            logger.debug(f"벡터 검색 완료: {len(hits)}개 결과")
            return hits
            
        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            raise
    
    def hybrid_search(
        self,
        index_name: str,
        query: str,
        query_vector: List[float],
        text_fields: List[str],
        vector_field: str,
        top_k: int,
        fusion_method: str = "convex",
        fusion_params: Optional[Dict[str, Any]] = None,
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색 구현"""
        try:
            # 기본 파라미터 설정
            params = fusion_params or {}

            if fusion_method == "convex":
                return self._convex_hybrid_search(
                    index_name, query, query_vector, text_fields, vector_field, 
                    top_k, params, filters
                )
            
            elif fusion_method == "rrf":
                return self._rrf_hybrid_search(
                index_name, query, query_vector, text_fields, vector_field,
                top_k, params, filters
            )

            else:
                raise ValueError(f"Hybrid Search에서 지원하지 않는 fusion 방식: {fusion_method}")

        except Exception as e:
            logger.error(f"하이브리도 검색 실패 ({fusion_method}): {e}")
            raise
    
    def _convex_hybrid_search(
        self,
        index_name: str,
        query: str,
        query_vector: List[float],
        text_fields: List[str],
        vector_field: str,
        top_k: int,
        params: Dict[str, Any],
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """convex combination 방식으로 scoring 결합"""
        vector_weight = params.get("vector_weight", 0.3)
        text_weight = params.get("text_weight", 0.7)
        
        search_body = {
            "knn": {
                "field": vector_field,
                "query_vector": query_vector,
                "k": 100,
                "num_candidates": 100
            },
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": text_fields,
                                "type": "best_fields",
                                "operator": "or"
                            }
                        }
                    ],
                    "should": [
                        {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": f"""
                                    double vector_score = cosineSimilarity(params.query_vector, params.vector_field) + 1.0;
                                    double text_score = _score;
                                    return {vector_weight} * vector_score + {text_weight} * text_score;
                                    """,
                                    "params": {
                                        "query_vector": query_vector,
                                        "vector_field": vector_field
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        # 필터 적용 (KNN과 query 양쪽에 모두 적용)
        if filters:
            filter_clause = {
                "bool": {
                    "should": filters,
                    "minimum_should_match": 1
                }
            }
            search_body["knn"]["filter"] = filter_clause
            search_body["query"]["bool"]["filter"] = filter_clause
        
        response = self.conn.search(
            index=index_name,
            body=search_body,
            size=top_k
        )
        
        hits = response["hits"]["hits"]
        logger.debug(f"Convex 하이브리드 검색 완료: {len(hits)}개 결과")
        return hits

    def _rrf_hybrid_search(
        self,
        index_name: str,
        query: str,
        query_vector: List[float],
        text_fields: List[str],
        vector_field: str,
        top_k: int,
        params: Dict[str, Any],
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """RRF 방식 하이브리드 검색"""
        rrf_k = params.get("rrf_k", 60)
        
        # 1. 텍스트 검색 수행
        text_results = self.keyword_search(
            index_name=index_name,
            query=query,
            text_fields=text_fields,
            top_k=top_k * 2,  # 더 많이 가져와서 RRF 적용
            filters=filters
        )
        
        # 2. 벡터 검색 수행  
        vector_results = self.vector_search(
            index_name=index_name,
            query_vector=query_vector,
            vector_field=vector_field,
            top_k=top_k * 2,
            filters=filters
        )
        
        # 3. RRF 점수 계산 및 융합
        final_results = self._apply_rrf_fusion(text_results, vector_results, rrf_k, top_k)
        
        logger.debug(f"RRF 하이브리드 검색 완료: {len(final_results)}개 결과")
        return final_results

    def _apply_rrf_fusion(
        self,
        text_results: List[Dict],
        vector_results: List[Dict],
        rrf_k: int,
        top_k: int
    ) -> List[Dict]:
        """RRF 점수 계산 및 결과 융합"""
        
        # 문서별 RRF 점수 계산
        doc_scores = {}
        doc_map = {}  # 문서 ID -> 문서 객체 매핑
        
        # 텍스트 검색 결과의 RRF 점수
        for rank, hit in enumerate(text_results, 1):
            doc_id = hit["_id"]
            rrf_score = 1 / (rrf_k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
            doc_map[doc_id] = hit
        
        # 벡터 검색 결과의 RRF 점수 추가
        for rank, hit in enumerate(vector_results, 1):
            doc_id = hit["_id"]
            rrf_score = 1 / (rrf_k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
            if doc_id not in doc_map:  # 텍스트 검색에 없던 문서
                doc_map[doc_id] = hit
        
        # 점수 기준 정렬 및 상위 결과 선택
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # 절대적 정규화 (이론적 최댓값)
        theoretical_max = 2 / (rrf_k + 1)

        # 결과 재구성 with 절대적 정규화된 점수
        final_results = []
        for doc_id, original_score in sorted_docs:
            if doc_id in doc_map:
                hit = doc_map[doc_id].copy()
                
                # 절대적 정규화 (최대 100%로 제한)
                normalized_score = min(1, (original_score / theoretical_max))
                hit["_score"] = round(normalized_score, 1)
                final_results.append(hit)
                    
        return final_results

    def expand_search_results(
        self,
        index_name: str,
        hits: List[Dict[str, Any]],
        tolerance: int
    ) -> List[Dict[str, Any]]:
        """검색 결과를 페이지 단위로 확장"""
        expanded_hits = []
        seen_ids = {hit["_id"] for hit in hits}
        
        logger.debug(f"페이지 확장 시작: {len(hits)}개 원본, tolerance={tolerance}")
        
        # 각 원본 hit별로 페이지 확장
        for hit in hits:
            src = hit.get("_source", {})
            gcs_pdf_path = src.get("gcs_pdf_path", "")
            page_str = src.get("page_number", "")
            
            if not (gcs_pdf_path and page_str):
                continue
            
            page_num = int(page_str)
            
            # 페이지 범위 확장
            for delta in range(-tolerance, tolerance + 1):
                if delta == 0:
                    continue
                    
                new_num = page_num + delta
                if new_num < 0:
                    continue
                    
                new_page = f"{new_num:05d}"
                
                # 확장된 페이지 검색
                must_clauses = [
                    {"term": {"gcs_pdf_path.keyword": gcs_pdf_path}},
                    {"term": {"page_number.keyword": new_page}}
                ]
                
                search_body = {
                    "query": {
                        "bool": {
                            "must": must_clauses
                        }
                    }
                }
                
                try:
                    response = self.conn.search(index=index_name, body=search_body)
                    for new_hit in response.get("hits", {}).get("hits", []):
                        nid = new_hit.get("_id")
                        if nid and nid not in seen_ids:
                            new_hit["_score"] = -1  # 확장된 결과 표시
                            expanded_hits.append(new_hit)
                            seen_ids.add(nid)
                            
                except Exception as e:
                    # 개별 페이지 확장 실패는 DEBUG 레벨로 (너무 상세함)
                    logger.debug(f"페이지 확장 중 오류 (페이지 {new_page}): {e}")
                    continue
        
        logger.debug(f"페이지 확장 완료: +{len(expanded_hits)}개 추가")
        return expanded_hits
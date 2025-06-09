"""
Elasticsearch 검색기 구현
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from elasticsearch import Elasticsearch

from app.core.search.base_searcher import BaseSearcher
from app.config.secrets_config import ElasticsearchSecrets
from app.config.base_config import ElasticsearchConfig

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
        vector_weight: float = 0.3,
        text_weight: float = 0.7,
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색 구현"""
        try:
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
            logger.debug(f"하이브리드 검색 완료: {len(hits)}개 결과")
            return hits
            
        except Exception as e:
            logger.error(f"하이브리드 검색 실패: {e}")
            raise
    
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
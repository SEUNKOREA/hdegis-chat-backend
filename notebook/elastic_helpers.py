from utils import InputProcessor
from embedder import GoogleEmbeddingModel

from typing import List, Dict, Tuple, Optional, Any
from elasticsearch import Elasticsearch

class ESConnector:
    def __init__(self, hosts: str, credentials: Tuple[str, str]):
        self.hosts = [hosts]
        self.credentials = credentials
        self.conn = self.create_es_connection()
    
    def create_es_connection(self):
        username, password = self.credentials
        es = Elasticsearch(
            hosts=self.hosts,
            basic_auth=(username, password),
            verify_certs=False,
        )
        return es
    
    def ping(self):
        if self.conn.ping():
            print("Ping successful: Connected to Elasticsearch!")
        else:
            print("Ping unsuccessful: Elasticsearch is not available!")


class ESSearch(ESConnector):
    def __init__(self, hosts: str, credentials: Tuple[str, str]):
        super().__init__(hosts, credentials)
        self.input_processor = InputProcessor()

    def keyword_text_search(self, index_name: str, top_k: int, user_query: str, text_fields: List[str]):
        """
        - 사용자 쿼리 -> 영문 키워드 생성 -> 텍스트 검색
        """
        try:
            # 영문 키워드 생성
            user_query_en = self.input_processor.tranlate(user_query)
            keywords = self.input_processor.generate_keywords(user_query_en)
            keywords = [keyword.strip() for keyword in keywords.split(" OR ")]

            # Elastic search query
            search_body = {
                "query": {
                    "multi_match": {
                        "query": " ".join(keywords),
                        "fields": text_fields,
                        "type": "best_fields",
                        "operator": "or"
                    }
                }
            }

            # Execute
            response = self.conn.search(index=index_name, body=search_body, size=top_k)

            return response
        except Exception as e:
            raise e

    def vector_search(self):
        pass

    def keyword_text_search_w_filter(self, index_name: str, top_k: int, 
                                     user_query: str, user_filter: str, 
                                     text_fields: List[str]):
        """
        - 사용자 쿼리 -> 영문 키워드 생성 -> 텍스트 검색
        - 필터 적용
        """
        try:
            # 영문 키워드 생성
            user_query_en = self.input_processor.tranlate(user_query)
            keywords = self.input_processor.generate_keywords(user_query_en)
            keywords = [keyword.strip() for keyword in keywords.split(" OR ")]
            print(f"--- Create Keywords: {keywords}")

            # 필터 구문 생성
            filter_phrase = self.input_processor.create_filter_phrase(user_filter)
            print(f"--- Apply filter ! ")

            # Elastic search query
            search_body = {
                "query": {
                    "bool": {
                        "must": {
                            "multi_match": {
                                "query": " ".join(keywords),
                                "fields": text_fields,
                                "type": "best_fields",
                                "operator": "or",
                            }
                        },
                        "filter": {
                            "bool": {
                                "should": filter_phrase,
                                "minimum_should_match": 1
                            }
                        }
                    }
                }
            }

            # Execute
            response = self.conn.search(index=index_name, body=search_body, size=top_k)

            return response
        except Exception as e:
            raise e

    def vector_search_w_filter(self, index_name: str, embedding_model_name: str, top_k: int, 
                               user_query: str, user_filter: str, 
                               vector_field: str):
        """
        - 사용자 쿼리 -> 쿼리 임베딩 생성 -> 벡터 검색
        - 필터 적용
        """
        try:
            # 쿼리 임베딩 생성
            embedding_model = GoogleEmbeddingModel(embedding_model_name)
            if embedding_model.need_translation: # 영어전용 
                user_query_en = self.input_processor.tranlate(user_query)
                query_vector = embedding_model.get_embedding(user_query_en)
            else: # 다국어 지원
                query_vector = embedding_model.get_embedding(user_query)
            print("--- Create Query Vector !")

            # 필터 구문 생성
            filter_phrase = self.input_processor.create_filter_phrase(user_filter)
            print(f"--- Apply filter ! ")

            # Elastic Search Query
            search_body = {
                "knn": {
                    "field": vector_field,
                    "query_vector": query_vector,
                    "k": top_k,
                    "num_candidates": 100,
                    "filter": {
                        "bool": {
                            "should": filter_phrase,
                            "minimum_should_match": 1
                        }
                    }
                }
            }

            # Execute
            response = self.conn.search(index=index_name, body=search_body, size=top_k)

            return response

        except Exception as e:
            raise e

    def hyde_vector_search_w_filter(self, index_name: str, embedding_model_name: str, top_k: int, 
                                    user_query: str, user_filter: str, 
                                    vector_field: str):
        """
        사용자 쿼리 -> 가상문서 생성 -> 임베딩 생성 -> 벡터검색
        필터 적용
        """
        try:
            # 가상문서 생성
            user_query_en = self.input_processor.tranlate(user_query)
            hyde = self.input_processor.generate_HyDE_document(user_query_en)
            print(f"--- Create HyDE document !")

            # 임베딩 생성
            embedding_model = GoogleEmbeddingModel(embedding_model_name)
            query_vector = embedding_model.get_embedding(hyde)
            print("--- Create Query Vector for HyDE!")

            # 필터구문 생성
            filter_phrase = self.input_processor.create_filter_phrase(user_filter)
            print(f"--- Apply filter ! ")

            # Elastic Search Query
            # Elastic Search Query
            search_body = {
                "knn": {
                    "field": vector_field,
                    "query_vector": query_vector,
                    "k": top_k,
                    "num_candidates": 100,
                    "filter": {
                        "bool": {
                            "should": filter_phrase,
                            "minimum_should_match": 1
                        }
                    }
                }
            }

            # Execute
            response = self.conn.search(index=index_name, body=search_body, size=top_k)

            return response

        except Exception as e:
            raise e
     
    def hybrid_search_w_filter(self,
                               index_name: str, embedding_model_name: str, top_k: int,
                               user_query: str, user_filter: str,
                               vector_field: str, text_fields: List[str],
                               ):
        """
        Hybrid Search (w/ filter)
        - 사용자 쿼리 -> 임베딩벡터 생성 -> 벡터검색
        - 사용자 쿼리 -> 키워드 생성 ->  텍스트검색
        - score: 벡터 유사도 30% + 텍스트 유사도 70%
        - 필터 적용
        """
        try:
            user_query_en = self.input_processor.tranlate(user_query)

            # 쿼리 임베딩 생성
            embedding_model = GoogleEmbeddingModel(embedding_model_name)
            if embedding_model.need_translation: 
                query_vector = embedding_model.get_embedding(user_query_en) # 영어전용
            else: 
                query_vector = embedding_model.get_embedding(user_query) # 다국어 지원
            print("--- Create Query Vector !")

            # 키워드 생성
            keywords = self.input_processor.generate_keywords(user_query_en)
            keywords = [keyword.strip() for keyword in keywords.split(" OR ")]
            print(f"--- Create Keywords: {keywords}")

            # 필터 구문 생성
            filter_phrase = self.input_processor.create_filter_phrase(user_filter)
            print(f"--- Apply filter ! ")

            # Elastic Search Query
            search_body = {
                "knn": {
                    "field": vector_field,
                    "query_vector": query_vector,
                    "k": 100,
                    "num_candidates": 100,
                    "filter": {
                        "bool": {
                            "should": filter_phrase,
                            "minimum_should_match": 1
                        }
                    }
                },
                
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": " ".join(keywords),
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
                                        "source": """
                                        double vector_score = cosineSimilarity(params.query_vector, params.vector_field) + 1.0;
                                        double text_score = _score;
                                        return 0.3 * vector_score + 0.7 * text_score;
                                        """,
                                        "params": {
                                            "query_vector": query_vector,
                                            "vector_field": vector_field
                                        }
                                    }
                                }
                            }
                        ],
                        "filter": {
                            "bool": {
                                "should": filter_phrase,
                                "minimum_should_match": 1
                            }
                        }
                    }
                }
            }

            response = self.conn.search(index=index_name, body=search_body, size=top_k)

            return response

        except Exception as e:
            raise e

    def hyde_hybrid_search_w_filter(self,
                               index_name: str, embedding_model_name: str, top_k: int,
                               user_query: str, user_filter: str,
                               vector_field: str, text_fields: List[str],
                               ):
        """
        Hybrid Search (w/ filter)
        - 사용자 쿼리 -> 가상문서 생성 -> 임베딩벡터 생성 -> 벡터검색
        - 사용자 쿼리 -> 키워드 생성 ->  텍스트검색
        - score: 벡터 유사도 30% + 텍스트 유사도 70%
        - 필터 적용
        """
        try:
            # 가상문서 생성
            user_query_en = self.input_processor.tranlate(user_query)
            hyde = self.input_processor.generate_HyDE_document(user_query_en)
            print(f"--- Create HyDE document !")

            # 임베딩 생성
            embedding_model = GoogleEmbeddingModel(embedding_model_name)
            query_vector = embedding_model.get_embedding(hyde)
            print("--- Create Query Vector for HyDE!")

            # 키워드 생성
            keywords = self.input_processor.generate_keywords(user_query_en)
            keywords = [keyword.strip() for keyword in keywords.split(" OR ")]
            print(f"--- Create Keywords: {keywords}")

            # 필터 구문 생성
            filter_phrase = self.input_processor.create_filter_phrase(user_filter)
            print(f"--- Apply filter ! ")

            # Elastic Search Query
            search_body = {
                "knn": {
                    "field": vector_field,
                    "query_vector": query_vector,
                    "k": 100,
                    "num_candidates": 100,
                    "filter": {
                        "bool": {
                            "should": filter_phrase,
                            "minimum_should_match": 1
                        }
                    }
                },
                
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": " ".join(keywords),
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
                                        "source": """
                                        double vector_score = cosineSimilarity(params.query_vector, params.vector_field) + 1.0;
                                        double text_score = _score;
                                        return 0.3 * vector_score + 0.7 * text_score;
                                        """,
                                        "params": {
                                            "query_vector": query_vector,
                                            "vector_field": vector_field
                                        }
                                    }
                                }
                            }
                        ],
                        "filter": {
                            "bool": {
                                "should": filter_phrase,
                                "minimum_should_match": 1
                            }
                        }
                    }
                }
            }

            response = self.conn.search(index=index_name, body=search_body, size=top_k)

            return response

        except Exception as e:
            raise e


"""
쿼리 향상 유틸리티 (키워드 생성, HyDE 등)
"""

from typing import Optional
import logging

from app.core.generation.base_generator import BaseGenerator
from app.utils.input_processor import InputProcessor

logger = logging.getLogger(__name__)


class QueryEnhancer:
    """쿼리 향상 처리 클래스"""
    
    def __init__(self, generator: BaseGenerator, input_processor: InputProcessor):
        """
        쿼리 향상기 초기화
        
        Args:
            generator: 텍스트 생성기
            input_processor: 입력 처리기
        """
        self.generator = generator
        self.input_processor = input_processor
    
    def generate_keywords(
        self,
        query: str,
        translate_to_english: bool = True,
        generation_config: Optional[dict] = None
    ) -> str:
        """
        쿼리에서 키워드 생성
        
        Args:
            query: 원본 쿼리
            translate_to_english: 영어로 번역 여부
            generation_config: 생성 설정
            
        Returns:
            str: 생성된 키워드 (OR로 연결)
        """
        try:
            # 필요시 영어로 번역
            if translate_to_english:
                query_en = self.input_processor.translate_text(query, 'en')
            else:
                query_en = query
            
            # 키워드 생성 프롬프트
            prompt = self._get_keyword_generation_prompt(query_en)
            
            # 키워드 생성
            config = generation_config or {"temperature": 0.1, "max_output_tokens": 256}
            keywords = self.generator.generate_text(prompt, generation_config=config)
            
            logger.debug(f"생성된 키워드: {keywords}")
            return keywords.strip()
            
        except Exception as e:
            logger.error(f"키워드 생성 실패: {e}")
            # 실패 시 원본 쿼리 반환
            return query
    
    def generate_hyde_document(
        self,
        query: str,
        translate_to_english: bool = True,
        generation_config: Optional[dict] = None
    ) -> str:
        """
        HyDE 가상문서 생성
        
        Args:
            query: 원본 쿼리
            translate_to_english: 영어로 번역 여부
            generation_config: 생성 설정
            
        Returns:
            str: 생성된 가상문서
        """
        try:
            # 필요시 영어로 번역
            if translate_to_english:
                query_en = self.input_processor.translate_text(query, 'en')
            else:
                query_en = query
            
            # HyDE 생성 프롬프트
            prompt = self._get_hyde_generation_prompt(query_en)
            
            # 가상문서 생성
            config = generation_config or {"temperature": 0.3, "max_output_tokens": 512}
            hyde_doc = self.generator.generate_text(prompt, generation_config=config)
            
            logger.debug(f"생성된 HyDE 문서 길이: {len(hyde_doc)}")
            return hyde_doc.strip()
            
        except Exception as e:
            logger.error(f"HyDE 문서 생성 실패: {e}")
            # 실패 시 원본 쿼리 반환
            return query
    
    def _get_keyword_generation_prompt(self, query: str) -> str:
        """키워드 생성 프롬프트 템플릿"""
        return f"""
You are an AI assistant specialized in generating Elasticsearch query strings. Your task is to create the most effective query string for the given user question. This query string will be used to search for relevant documents in an Elasticsearch index.

Guidelines:
1. Analyze the user's question carefully.
2. Generate ONLY a query string suitable for Elasticsearch's match query.
3. Focus on key terms and concepts from the question.
4. Include synonyms, related terms, and various word forms that might be in relevant documents:
   - Include common synonyms and closely related concepts
   - Consider different tenses of verbs (e.g., walk, walks, walked, walking)
   - Include singular and plural forms of nouns
   - Add common abbreviations or acronyms if applicable
5. Use simple Elasticsearch query string syntax if helpful (e.g., OR).
6. Do not use advanced Elasticsearch features or syntax.
7. Do not include any explanations, comments, or additional text.
8. Provide only the query string, nothing else.

Use only OR as the operator. AND is not allowed.

User Question:
{query}

Generate the Elasticsearch query string:
""".strip()
    
    def _get_hyde_generation_prompt(self, query: str) -> str:
        """HyDE 생성 프롬프트 템플릿"""
        return f"""
You are an AI assistant specialized in generating hypothetical documents based on user queries. Your task is to create a detailed, factual document that would likely contain the answer to the user's question. This hypothetical document will be used to enhance the retrieval process in a Retrieval-Augmented Generation (RAG) system.

Guidelines:
1. Carefully analyze the user's query to understand the topic and the type of information being sought.
2. Generate a hypothetical document that:
   a. Is directly relevant to the query
   b. Contains factual information that would answer the query
   c. Includes additional context and related information
   d. Uses a formal, informative tone similar to an encyclopedia or textbook entry
3. Structure the document with clear paragraphs, covering different aspects of the topic.
4. Include specific details, examples, or data points that would be relevant to the query.
5. Aim for a document length of 200-300 words.
6. Do not use citations or references, as this is a hypothetical document.
7. Avoid using phrases like "In this document" or "This text discusses" - write as if it's a real, standalone document.
8. Do not mention or refer to the original query in the generated document.
9. Ensure the content is factual and objective, avoiding opinions or speculative information.
10. Output only the generated document, without any additional explanations or meta-text.

User Question:
{query}

Generate a hypothetical document that would likely contain the answer to this query:
""".strip()
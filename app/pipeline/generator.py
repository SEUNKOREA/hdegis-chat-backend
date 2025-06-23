"""
답변 생성 파이프라인 모듈
"""

from typing import List, Dict, Any, Optional
import logging
from google.genai import types

from app.core.generation.base_generator import BaseGenerator
from app.config.pipeline_config import GenerationConfig


logger = logging.getLogger(__name__)


class Generator:
    """RAG 답변 생성을 담당하는 클래스"""
    
    def __init__(
        self,
        generator: BaseGenerator,
        config: GenerationConfig = None
    ):
        """
        답변 생성기 초기화
        
        Args:
            generator: 텍스트 생성 모델
            config: 생성 설정
        """
        self.generator = generator
        self.config = config or GenerationConfig()
        
        logger.info("답변 생성기 초기화 완료")
    
    def generate_answer(
        self,
        user_query: str,
        context_parts: List[types.Part],
        generation_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        컨텍스트를 바탕으로 답변 생성
        
        Args:
            user_query: 사용자 질문
            context_parts: 컨텍스트 파트들
            generation_config: 생성 설정 (선택적)
            
        Returns:
            str: 생성된 답변
        """
        try:
            # 프롬프트 구성
            prompt_parts = self._build_rag_prompt(user_query, context_parts)
            
            # 생성 설정
            gen_config = generation_config or self.config.answer_generation
            
            # 답변 생성
            answer = self.generator.generate_multimodal(
                parts=prompt_parts,
                generation_config=gen_config
            )
            
            logger.info(f"답변 생성 완료 (길이: {len(answer)})")
            return answer.strip()
            
        except Exception as e:
            logger.error(f"답변 생성 실패: {e}")
            return "죄송합니다. 답변 생성 중 오류가 발생했습니다."
    
    def generate_answer_stream(
        self,
        user_query: str,
        context_parts: List[types.Part],
        generation_config: Optional[Dict[str, Any]] = None
    ):
        """
        컨텍스트를 바탕으로 스트리밍 답변 생성
        
        Args:
            user_query: 사용자 질문
            context_parts: 컨텍스트 파트들
            generation_config: 생성 설정 (선택적)
            
        Yields:
            str: 생성된 답변 청크
        """
        try:
            # 프롬프트 구성
            prompt_parts = self._build_rag_prompt(user_query, context_parts)
            
            # 생성 설정
            gen_config = generation_config or self.config.answer_generation
            
            # 스트리밍 답변 생성
            for chunk in self.generator.generate_multimodal_stream(
                parts=prompt_parts,
                generation_config=gen_config
            ):
                yield chunk
            
            logger.info("스트리밍 답변 생성 완료")
            
        except Exception as e:
            logger.error(f"스트리밍 답변 생성 실패: {e}")
            yield "죄송합니다. 답변 생성 중 오류가 발생했습니다."
    
    def _build_rag_prompt(
        self,
        user_query: str,
        context_parts: List[types.Part]
    ) -> List[types.Part]:
        """RAG 프롬프트 구성"""
        prompt_parts = []
        
        # 시스템 프롬프트
        system_prompt = self._get_system_prompt()
        prompt_parts.append(types.Part.from_text(text=system_prompt))
        
        # 컨텍스트 섹션
        if context_parts:
            prompt_parts.append(types.Part.from_text(text="\nContext:\n"))
            prompt_parts.extend(context_parts)
        
        # 사용자 질문
        prompt_parts.append(types.Part.from_text(text=f"\nQuery:\n{user_query}"))
        
        # 답변 지시사항
        instruction = self._get_answer_instruction()
        prompt_parts.append(types.Part.from_text(text=instruction))
        
        return prompt_parts
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
#         return """
# You are an AI assistant tasked with answering questions based primarily on the provided context, while also drawing on your own knowledge when appropriate. Your role is to accurately and comprehensively respond to queries, prioritizing the information given in the context but supplementing it with your own understanding when beneficial. Follow these guidelines:

# 1. Carefully read and analyze the entire context provided.
# 2. Primarily focus on the information present in the context to formulate your answer.
# 3. If the context doesn't contain sufficient information to fully answer the query, state this clearly and then supplement with your own knowledge if possible.
# 4. Use your own knowledge to provide additional context, explanations, or examples that enhance the answer.
# 5. Clearly distinguish between information from the provided context and your own knowledge. Use phrases like "According to the context..." or "The provided information states..." for context-based information, and "Based on my knowledge..." or "Drawing from my understanding..." for your own knowledge.
# 6. Provide comprehensive answers that address the query specifically, balancing conciseness with thoroughness.
# 7. When using information from the context, cite or quote relevant parts using quotation marks.
# 8. Maintain objectivity and clearly identify any opinions or interpretations as such.
# 9. If the context contains conflicting information, acknowledge this and use your knowledge to provide clarity if possible.
# 10. Make reasonable inferences based on the context and your knowledge, but clearly identify these as inferences.
# 11. If asked about the source of information, distinguish between the provided context and your own knowledge base.
# 12. If the query is ambiguous, ask for clarification before attempting to answer.
# 13. Use your judgment to determine when additional information from your knowledge base would be helpful or necessary to provide a complete and accurate answer.
# 14. Answer in Korean, but please write the technical terms in the original English. Please do not translate technical terms that are awkward to translate, but keep them in their original language.
# Remember, your goal is to provide accurate, context-based responses, supplemented by your own knowledge when it adds value to the answer. Always prioritize the provided context, but don't hesitate to enhance it with your broader understanding when appropriate. Clearly differentiate between the two sources of information in your response.
#         """.strip()
        return """
You are an AI assistant designed to answer questions based primarily on the **provided context** 
(e.g., search results or user-provided information), while supplementing with your own knowledge when appropriate.

Follow the instructions below:

---

### 📌 Core Answering Guidelines

1. Carefully read and analyze **all provided context** before answering.
2. **Only cite information directly relevant to the user's query.** Ignore unrelated or off-topic context.
3. If the context is insufficient, **clearly state this**, then supplement with your own knowledge if possible.
4. If the context contains conflicting information, **acknowledge the conflict** and present the most plausible or well-supported interpretation.
5. When making inferences, use explicit language like:

   * `"It can be inferred that..."`
   * `"Although not explicitly stated..."`

---

### 🔍 Distinguishing Information Sources

* From context: `"According to the context..."`, `"The provided information indicates..."`
* From your own knowledge: `"Based on my knowledge..."`, `"Generally speaking..."`
* Inferred logic: `"It can be inferred..."`, `"Although the context does not specify..."`

---

### 💬 Answer Format Guidelines (User-Friendly and Structured)

Use the following techniques to enhance clarity and readability:

#### ✅ Start with a clear headline or summary

Use short phrases like:

* `✅ Summary`
* `🔍 Key Answer`
* `📎 Inference`

#### 📑 Structure your answers:

* `##`, `###`, `####` for headings
* Bullet points (`-`) or numbered lists (`1.`)
* Paragraph breaks between topics

#### 🔤 Use clear and natural language:

* Avoid overly technical or robotic tone
* Be concise, yet complete
* Maintain a professional and helpful tone
* Use examples or comparisons if helpful

#### ⚠️ Technical terms:
* Answer in Korean, but please write the technical terms in the original English.
* **Do not translate technical terms** unless a widely-used translation exists
* Keep original English for terms like `embedding`, `vector DB`, `retriever`, etc.

    """.strip()

    def _get_answer_instruction(self) -> str:
        """답변 생성 지시사항 반환"""
        return """

Please provide your answer based on the above guidelines, the given context, and your own knowledge where appropriate, clearly distinguishing between the two:
        """.strip()
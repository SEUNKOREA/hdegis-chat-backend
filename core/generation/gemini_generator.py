"""
Gemini 생성 모델 구현
"""

from typing import List, Dict, Any, Optional
import logging
from google import genai
from google.genai import types

from .base_generator import BaseGenerator
from config.secrets_config import GoogleCloudSecrets

logger = logging.getLogger(__name__)


class GeminiGenerator(BaseGenerator):
    """Gemini 생성 모델 구현"""
    
    def __init__(self, secrets: GoogleCloudSecrets, default_model: str = "gemini-2.0-flash-001"):
        """
        Gemini 클라이언트 초기화
        
        Args:
            secrets: Google Cloud 인증 정보
            default_model: 기본 사용할 모델명
        """
        self._default_model = default_model
        self.client = genai.Client(
            vertexai=True,
            project=secrets.project_id,
            location=secrets.location
        )
        
        logger.info(f"Gemini 생성기 초기화: {default_model}")
    
    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """텍스트 생성"""
        try:
            model_name = model or self._default_model
            
            # Contents 구성
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)]
                )
            ]
            
            # GenerateContentConfig 생성
            config = self._create_generation_config(generation_config)
            
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"텍스트 생성 실패: {e}")
            raise
    
    def generate_multimodal(
        self,
        parts: List[types.Part],
        model: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """멀티모달 생성 (텍스트 + 이미지)"""
        try:
            model_name = model or self._default_model
            
            # Contents 구성
            contents = [
                types.Content(
                    role="user",
                    parts=parts
                )
            ]
            
            # GenerateContentConfig 생성
            config = self._create_generation_config(generation_config)
            
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"멀티모달 생성 실패: {e}")
            raise
    
    def _create_generation_config(self, user_config: Optional[Dict[str, Any]] = None) -> types.GenerateContentConfig:
        """GenerateContentConfig 객체 생성"""
        
        # 기본 설정
        config_dict = {
            "temperature": 0.7,
            "top_p": 1.0,
            "max_output_tokens": 2048
        }
        
        # 사용자 설정으로 업데이트
        if user_config:
            config_dict.update(user_config)
        
        # Safety settings (항상 포함)
        safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", 
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="OFF"
            )
        ]
        
        return types.GenerateContentConfig(
            temperature=config_dict.get("temperature", 0.7),
            top_p=config_dict.get("top_p", 1.0),
            max_output_tokens=config_dict.get("max_output_tokens", 2048),
            safety_settings=safety_settings
        )
    
    @property
    def default_model(self) -> str:
        """기본 모델명 반환"""
        return self._default_model
    
    @property
    def supported_models(self) -> List[str]:
        """지원하는 모델 목록 반환"""
        return [
            "gemini-2.0-flash-001",
            "gemini-1.5-pro-001", 
            "gemini-1.5-flash-001"
        ]
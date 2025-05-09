import os
from typing import List, Dict, Optional
from google.cloud import translate_v2 as translate
from google import genai
import pandas as pd
import time
from functools import wraps

class InputProcessor:
    def __init__(self):
        self.translate_client = translate.Client()
        self.genai_client = genai.Client(
            vertexai=True,
            project=os.getenv("PROJECT_ID"),
            location=os.getenv("LOCATION")
        )
    
    def detect_language(self, text: str) -> str:
        """
        주어진 텍스트의 언어를 감지합니다.
        """
        result = self.translate_client.detect_language(text)
        return result['language']

    def tranlate(self, text: str, target_language: str = 'en'):
        """
        주어진 텍스트의 언어를 감지후 타겟 언어와 다르다면 타겟 언어로 번역합니다. 
        (기본 영어로 번역)
        """
        if self.detect_language(text) == target_language:
            return text

        result = self.translate_client.translate(text, target_language)
        return result['translatedText']

    def create_filter_phrase(self, user_filter: str) -> List[Dict[str, Dict[str, str]]]:
        """
        사용자 입력 필터 문자열을 받아 '&' 로 분리하고, 각 항목의 마지막 폴더 레벨만 추출하여
        Elasticsearch의 match_phrase 형식 필터 목록을 반환합니다.

        예) "폴더A/서브폴더1 & 폴더B/서브폴더2"  -> 
            [{'match_phrase': {'folder_levels': '서브폴더1'}}, 
             {'match_phrase': {'folder_levels': '서브폴더2'}}]
        """
        # '&' 기준으로 분리
        filter_list = user_filter.strip().split('&')
        # 각 항목별로 '/' 로 분리 후 마지막 값 추출 (빈 문자열 무시)
        els_filters = [filt.split('/')[-1].strip() for filt in filter_list if filt.strip()]
        # match_phrase 쿼리 목록 구성
        match_phrase_filters = [{'match_phrase': { 'folder_levels': phrase }} for phrase in els_filters]
        return match_phrase_filters
    
    def generate_keywords(self, text: str) -> str:
        from prompts import ELASTIC_KEYWORD_SEARCH_QUERY_GENERATOR_PROMPT
        response = self.genai_client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=ELASTIC_KEYWORD_SEARCH_QUERY_GENERATOR_PROMPT.format(user_query=text)
        )
        return response.text

    def generate_HyDE_document(self, text: str) -> str:
        from prompts import HYDE_DOCUMENT_GENERATOR_PROMPT
        response = self.genai_client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=HYDE_DOCUMENT_GENERATOR_PROMPT.format(user_query=text)
        )
        return response.text

def convert_to_excel_name(original_name):
    """
    엑셀 표 이름 규칙에 맞게 변환
    - 공백 → _
    - 슬래시(/) → __ (이중 언더스코어)
    - 숫자 + 점 제거 (예: '1. ' → '')
    - 특수 문자 제거 ('(', ')', '-')
    """
    import re
    # 숫자 + 점(`1.`) 제거
    modified_name = re.sub(r'^\d+\.\s*', '', original_name)
    # 슬래시(`/`) → `__`
    modified_name = modified_name.replace("/", "__")
    # 공백 → `_`
    modified_name = modified_name.replace(" ", "_")
    # 특수 문자 제거 (`(`, `)`, `-`)
    modified_name = re.sub(r'[()-]', '', modified_name)

    return modified_name

def revert_to_original_name(modified_name):
    """
    변환된 엑셀 표 이름을 원래대로 복원
    """
    mappings = {
        'International_Standards__IEC': '1. International Standards/IEC',
        'International_Standards__IEEE': '1. International Standards/IEEE',
        'Type_Test_Reports__145SP3__145_kV_40_kA_MS_2017': '2. Type Test Reports/145SP-3/145 kV 40 kA MS (2017)',
        'Type_Test_Reports__300SR__245_kV_50_kA_MS_2020': '2. Type Test Reports/300SR/245 kV 50 kA MS (2020)',
        'Type_Test_Reports__300SR__245_kV_63_kA_MS_2024': '2. Type Test Reports/300SR/245 kV 63 kA MS (2024)',
        'Customer_Standard_Specifications__Australia__Endeavour_Energy': '3. Customer Standard Specifications/Australia/Endeavour Energy',
        'Customer_Standard_Specifications__Oman__OETC': '3. Customer Standard Specifications/Oman/OETC',
        'Customer_Standard_Specifications__Saudi_Arabia__SEC': '3. Customer Standard Specifications/Saudi Arabia/SEC',
        'Customer_Standard_Specifications__Spain__Iberdrola': '3. Customer Standard Specifications/Spain/Iberdrola',
        'Customer_Standard_Specifications__Spain__REE': '3. Customer Standard Specifications/Spain/REE'
    }
    return mappings.get(modified_name, None)    

def get_gt_refs(row: pd.Series) -> list:
    """
    QA 성능평가 데이터셋에서 gt_refs 모으기
    """
    gt_refs = []
    for n in range(1, 14):
        if pd.isna(row[f"page_{n}"]):
            break
        
        path = row[f"path_{n}"]
        filename = row[f"filename_{n}"]
        page = int(row[f'page_{n}'])
        
        gt_refs.append((path, filename, page))
    return gt_refs

def get_search_refs(hits):
    search_refs = []
    for hit in hits:
        search_path = convert_to_excel_name('/'.join(hit['_source']['folder_levels']))
        search_filename = hit['_source']['pdf_name']
        search_page = int(hit['_source']['page'])

        search_refs.append((search_path, search_filename, search_page))
    return search_refs

def get_retrieved_context(hits):
    search_contents = []
    for hit in hits:
        search_content = hit['_source']['content']
        search_contents.append(search_content)
    
    return '\n\n'.join(f"### Retrieved Context {i+1}: {text}" for i, text in enumerate(search_contents))

def timed(label, func, *args, **kwargs):
    print(f"[{label}] started ...")
    start = time.time()
    result = func(*args, **kwargs)
    end = time.time()
    print(f"[{label}] completed - elapsed time: {end - start:.3f}seconds\n")
    return result
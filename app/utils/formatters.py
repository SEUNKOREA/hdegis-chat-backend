"""
포맷팅 및 유틸리티 함수들
"""
import pandas as pd
import time
import logging
from functools import wraps
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def timed(label: str, func, *args, **kwargs):
    """
    함수 실행 시간 측정 및 로깅
    
    Args:
        label: 로그 라벨
        func: 실행할 함수
        *args, **kwargs: 함수 인자들
        
    Returns:
        함수 실행 결과
    """
    logger.info(f"======================== [{label}] 시작 ========================")
    start = time.time()
    
    try:
        result = func(*args, **kwargs)
        end = time.time()
        logger.info(f"======================== [{label}] 완료 - (소요시간: {end - start:.3f}초) ========================\n")
        return result
    except Exception as e:
        end = time.time()
        logger.error(f"======================== [{label}] 실패 - (소요시간: {end - start:.3f}초): {e} ========================\n")
        raise


def format_search_results(hits: List[Dict[str, Any]]) -> str:
    """
    검색 결과를 읽기 쉬운 형태로 포맷팅
    
    Args:
        hits: 검색 결과
        
    Returns:
        str: 포맷팅된 결과 문자열
    """
    if not hits:
        return "검색 결과가 없습니다."
    
    formatted_results = ["[검색 결과]"]
    
    for i, hit in enumerate(hits, start=1):
        src = hit.get("_source", {})
        score = hit.get("_score", 0)
        
        # 파일 정보 추출
        name = src.get("gcs_pdf_path", src.get("pdf_name", "Unknown"))
        page = src.get("page_number", src.get("page", "Unknown"))
        
        formatted_results.append(f"[{i:02d}] {name}, 페이지 {page} (점수: {score:.3f})")
    
    return "\n".join(formatted_results)


def convert_to_excel_name(original_name: str) -> str:
    """
    엑셀 표 이름 규칙에 맞게 변환
    
    Args:
        original_name: 원본 이름
        
    Returns:
        str: 변환된 이름
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


def revert_to_original_name(modified_name: str) -> str:
    """
    변환된 엑셀 표 이름을 원래대로 복원
    
    Args:
        modified_name: 변환된 이름
        
    Returns:
        str: 원본 이름
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
    return mappings.get(modified_name, modified_name)


def get_gt_refs(row) -> List[Tuple[str, str, int]]:
    """
    QA 성능평가 데이터셋에서 ground truth 참조 추출
    
    Args:
        row: 데이터 행
        
    Returns:
        List[Tuple]: (path, filename, page) 튜플 리스트
    """
    gt_refs = []
    for n in range(1, 14):
        page_col = f"page_{n}"
        if hasattr(row, page_col) and not pd.isna(getattr(row, page_col)):
            path = getattr(row, f"path_{n}")
            filename = getattr(row, f"filename_{n}")
            page = int(getattr(row, page_col))
            gt_refs.append((path, filename, page))
        else:
            break
    return gt_refs


def get_search_refs(hits: List[Dict[str, Any]]) -> List[Tuple[str, str, int]]:
    """
    검색 결과에서 참조 정보 추출
    
    Args:
        hits: 검색 결과
        
    Returns:
        List[Tuple]: (path, filename, page) 튜플 리스트
    """
    search_refs = []
    for hit in hits:
        src = hit.get("_source", {})
        
        # 경로 정보
        folder_levels = src.get("folder_levels", [])
        if folder_levels:
            search_path = convert_to_excel_name('/'.join(folder_levels))
        else:
            search_path = "Unknown"
        
        # 파일명과 페이지
        search_filename = src.get("pdf_name", "Unknown")
        search_page = int(src.get("page", 0))
        
        search_refs.append((search_path, search_filename, search_page))
    
    return search_refs


def get_retrieved_context(hits: List[Dict[str, Any]], text_field: str = "content") -> str:
    """
    검색 결과에서 컨텍스트 텍스트 추출
    
    Args:
        hits: 검색 결과
        text_field: 텍스트 필드명
        
    Returns:
        str: 결합된 컨텍스트 텍스트
    """
    search_contents = []
    for hit in hits:
        content = hit.get("_source", {}).get(text_field, "")
        if content:
            search_contents.append(content)
    
    return '\n\n'.join(
        f"### Retrieved Context {i+1}: {text}" 
        for i, text in enumerate(search_contents)
    )
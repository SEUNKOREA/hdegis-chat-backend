from typing import List, Dict, Tuple, Optional, Any


def evaluate_hit(
        gt_refs: List[Tuple],
        search_refs: List[Tuple],
):
    """
    질문 한 개에 대한 개별 검색결과들에 정답이 포함되어있으면 True, 그렇지 않으면 False
    """
    gt_set = set(gt_refs)
    hit = any(search_ref in gt_set for search_ref in search_refs)
    return hit

def evaluate_rr(
        gt_refs: List[Tuple],
        search_refs: List[Tuple],
):
    """
    질문 한 개에 대한 개별 검색결과들에 대해서 RR 구하기
    """
    rr = 0
    gt_set = set(gt_refs)
    for rank, search_ref in enumerate(search_refs, start=1):
        if search_ref in gt_set:
            rr = 1 / rank
            break
    return rr






class Evaluator:
    def __init__(self):
        pass

    def evaluate_hit(
            gt_refs: list[tuple],
            search_refs: list[tuple],
    ) -> bool:
        """
        검색된 결과에 정답이 포함되어있는지
        """
        gt_set = set(gt_refs)
        is_hit = any([search_ref in gt_set for search_ref in search_refs])
        return is_hit


    def evaluate_rr(
            
    ):
        pass

    def evaluate_accuracy(
            self, 
            user_query: str,
            gen_answer: str,
            gt_answer: str,
        ):
        """
        정확성(Accuracy) 평가함수: 생성된 답변이 정답과 얼마나 똑같은지
        5점	답변이 정답과 거의 완벽하게 일치하며, 오류가 없다.
        4점	답변이 대부분 정답과 일치하나, 사소한 부정확성이 있다. (핵심 내용에는 영향 없음)
        3점	답변이 정답과 부분적으로 일치하지만 중요한 오류가 있다.
        2점	답변이 정답과 거의 맞지 않으며, 여러 오류가 존재한다.
        1점	답변이 정답과 완전히 다르거나 잘못된 정보를 제공한다.
        """
        ACCURACY_PROMPT_TEMPLATE = """


"""





        pass

    def evaluate_relevance(
            self,
            user_query: str,
            gen_answer: str,
        ):
        """
        관련성(Relevance) 평가함수: 생성된 답변이 질문과 관련이 있는지
        5점	답변이 질문 의도와 매우 밀접하며, 핵심을 정확히 짚었다.
        4점	답변이 질문과 대부분 관련 있으나, 약간의 부차적 내용이 포함되어 있다.
        3점	답변이 질문과 부분적으로만 관련 있고, 일부 엉뚱한 내용이 있다.
        2점	답변이 질문과 크게 관련이 없으며, 중심을 벗어난 내용이 많다.
        1점	답변이 질문과 전혀 관련이 없다.
        """
        pass

    def evaluate_completeness(
            self,
            user_query: str,
            gen_answer: str,
            gt_answer: str,
        ):
        """
        완전성(Completeness) 평가함수: 질문에서 요구한 모든 정보를 답변에 담았는지
        5점	답변이 질문에 필요한 모든 정보를 포괄하고 있다. (누락 없음)
        4점	답변이 핵심 정보는 모두 포함하나, 부가적인 정보가 약간 부족하다.
        3점	답변이 필요한 정보 중 일부만 제공하고 중요한 부분이 누락되었다.
        2점	답변이 질문에 필요한 대부분의 정보를 제공하지 못했다.
        1점	답변이 질문에 대해 거의 정보를 제공하지 못하거나 무의미하다.
        """
        pass

    def evaluate_groundedness(
            self,
            search_refs,
            gen_answer: str,
        ):
        """
        출처기반성(Groundedness) 평가함수: 답변이 컨텍스트를 기반으로 작성되었는지
        5점	답변이 검색 컨텍스트(문서/이미지)와 완전히 일치하며, 독자적 추론 없이 근거를 따른다.
        4점	답변이 대부분 컨텍스트를 기반으로 하지만 약간의 추론이 있다. (큰 문제 없음)
        3점	답변이 일부 컨텍스트를 참고했지만, 추론 또는 창작이 상당 부분 포함되어 있다.
        2점	답변이 컨텍스트를 거의 활용하지 않고 독자적 내용에 의존한다.
        1점	답변이 컨텍스트를 전혀 사용하지 않고 임의로 생성되었다.
        """
        pass
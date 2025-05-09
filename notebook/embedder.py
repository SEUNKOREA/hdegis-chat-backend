from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

class GoogleEmbeddingModel:
    _ENGLISH_ONLY_MODELS = {
        "text-embedding-004": True,
        "text-embedding-005": True,
        "text-multilingual-embedding-002": False
    }

    def __init__(self, model_name: str = "text-embedding-004"):
        self.model_name = model_name
        self.embedding_model = TextEmbeddingModel.from_pretrained(model_name)
        self.need_translation = self._ENGLISH_ONLY_MODELS.get(model_name, True)
    
    def get_embedding(self, text: str, task: str = "RETRIEVAL_DOCUMENT", dimensionality: int = 768, auto_truncate: bool = True) -> list:
        """
        주어진 텍스트에 대한 임베딩 벡터를 반환합니다.
        """
        inputs = [TextEmbeddingInput(text, task)]
        kwargs = {"output_dimensionality": dimensionality} if dimensionality else {}
        kwargs['auto_truncate'] = auto_truncate
        embeddings = self.embedding_model.get_embeddings(inputs, **kwargs)
        # 첫 번째 임베딩 결과의 벡터를 반환 (여러 문장이면 리스트 확장 가능)
        return embeddings[0].values

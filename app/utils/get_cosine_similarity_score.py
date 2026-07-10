import numpy as np
from sentence_transformers import SentenceTransformer

# Load once at module import time; reused across all calls.
# This avoids a multi-second model reload on every verification request.
_model: SentenceTransformer | None = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def cosine_similarity_score(outputs: list[str]) -> float:
    """
    Computes the mean pairwise cosine similarity across all output strings.
    Returns a float in [0, 1].
    """
    model = _get_model()
    embeddings = np.array([model.encode(output) for output in outputs])
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    # Avoid division by zero for empty strings
    norms = np.where(norms == 0, 1e-10, norms)
    normalized = embeddings / norms
    cosine_similarities = np.dot(normalized, normalized.T)
    return float(np.mean(cosine_similarities))

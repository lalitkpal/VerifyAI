import numpy as np
from sentence_transformers import SentenceTransformer

def cosine_similarity_score(outputs):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = np.array([model.encode(output) for output in outputs])
    print("Embeddings ready")
    cosine_similarities = np.dot(embeddings, embeddings.T) / (np.linalg.norm(embeddings, axis=1) * np.linalg.norm(embeddings, axis=1).T)
    print("Got similarity score")
    return float(np.mean(cosine_similarities))  # Ensure JSON serializable

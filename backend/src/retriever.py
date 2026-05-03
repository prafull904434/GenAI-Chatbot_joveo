import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import google.genai as genai

from backend.src.config import CHUNKS_PATH, EMBEDDINGS_PATH, TOP_K


@dataclass
class RetrievedChunk:
    url: str
    content: str
    score: float


class EmbeddingRetriever:
    def __init__(
        self,
        chunks_path: Path = CHUNKS_PATH,
        embeddings_path: Path = EMBEDDINGS_PATH,
    ) -> None:
        if not chunks_path.exists() or not embeddings_path.exists():
            raise FileNotFoundError(
                "Index files are missing. Run `python -m src.ingest` first."
            )
        self.df = pd.read_csv(chunks_path)
        self.embeddings = np.load(embeddings_path)
        
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY for embedding.")
        self.client = genai.Client(api_key=api_key)


    def search(self, query: str, k: int = TOP_K) -> List[RetrievedChunk]:
        # generate query embedding
        resp = self.client.models.embed_content(
            model="gemini-embedding-2",
            contents=query,
            config={"task_type": "RETRIEVAL_QUERY"},
        )

        query_vector = np.array(
            [resp.embeddings[0].values],
            dtype=np.float32,
        )
# compute similarity against stored embeddings
        similarity_scores = cosine_similarity(query_vector, self.embeddings)[0]
# get top-k matches
        top_indices = np.argsort(similarity_scores)[-k:][::-1]

        results: List[RetrievedChunk] = []
        for idx in top_indices:
            row = self.df.iloc[idx]

            results.append(
                RetrievedChunk(
                    url=row["url"],
                    content=row["content"],
                    score=float(similarity_scores[idx]),
                )
            )

        return results
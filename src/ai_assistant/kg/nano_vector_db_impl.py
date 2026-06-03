from typing import TypedDict, Callable, Any
from dataclasses import dataclass
import numpy as np

from ai_assistant.utils import logger

from lightrag.kg.nano_vector_db_impl import NanoVectorDBStorage as LightRAGNanoVectorDBStorage

Data = TypedDict("Data", {"__id__": str, "__vector__": np.ndarray})
ConditionLambda = Callable[[Data], bool]

@dataclass
class NanoVectorDBStorage(LightRAGNanoVectorDBStorage):

    async def query(
        self, query: str, top_k: int, ids: list[str] | None = None, filter_lambda: ConditionLambda = None
    ) -> list[dict[str, Any]]:

        # Execute embedding outside of lock to avoid improve cocurrent
        embedding = await self.embedding_func(
            [query], _priority=5
        )  # higher priority for query
        embedding = embedding[0]

        client = await self._get_client()
        results = client.query(
            query=embedding,
            top_k=top_k,
            better_than_threshold=self.cosine_better_than_threshold,
            filter_lambda=filter_lambda,
        )
        results = [
            {
                **dp,
                "id": dp["__id__"],
                "distance": dp["__metrics__"],
                "created_at": dp.get("__created_at__"),
            }
            for dp in results
        ]
        return results

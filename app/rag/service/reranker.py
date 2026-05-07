"""DashScope 重排序器"""
from typing import Optional, Sequence

import dashscope
from langchain_core.documents import Document
from langchain_core.documents.compressor import BaseDocumentCompressor
from langchain_core.callbacks.manager import Callbacks


class DashScopeReranker(BaseDocumentCompressor):
    model: str = "gte-rerank"
    top_n: int = 4

    class Config:
        arbitrary_types_allowed = True

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        if not documents:
            return []

        passages = [doc.page_content for doc in documents]
        response = dashscope.TextReRank.call(
            model=self.model,
            query=query,
            documents=passages,
            top_n=self.top_n,
            return_documents=False,
        )

        if response.status_code != 200:
            print(f"[Reranker] 调用失败: {response.status_code} {response.message}，回退到原始顺序")
            return list(documents[: self.top_n])

        reranked = []
        for item in response.output.results:
            original = documents[item.index]
            reranked.append(
                Document(
                    page_content=original.page_content,
                    metadata={**original.metadata, "rerank_score": item.relevance_score},
                )
            )
        return reranked

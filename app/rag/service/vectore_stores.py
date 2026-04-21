"""向量存储器
"""
from langchain_chroma import Chroma
import app.rag.config_data as config
import os

os.environ["DASHSCOPE_API_KEY"] = config.DASHSCOPE_API_KEY


class VectorStoreService(object):
    def __init__(self, embedding):
        self.embedding = embedding
        self.vector_store = Chroma(
            collection_name=config.collection_name,
            embedding_function=self.embedding,
            persist_directory=config.persist_directory,
        )

    def get_retriever(self):
        """返回向量检索器，方便加入chain"""
        return self.vector_store.as_retriever(search_type="similarity",
                                              search_kwargs={"k": config.similarity_threshold})


if __name__ == '__main__':
    from langchain_community.embeddings import DashScopeEmbeddings

    retriever = VectorStoreService(DashScopeEmbeddings(model="text-embedding-v4")).get_retriever()
    res = retriever.stream("我想吃牛肉，给我做几道菜")
    # retriever = vector_store.get_retriever()
    for docs in res:
        for doc in docs:
            print(doc.page_content)

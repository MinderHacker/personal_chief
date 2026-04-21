"""
实现知识库功能
"""

from idlelib.iomenu import encoding
from datetime import datetime
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import app.rag.config_data as config
import os
import hashlib

os.environ["DASHSCOPE_API_KEY"] = config.DASHSCOPE_API_KEY


def check_md5(md5_str: str):
    """
    检查传入的md5字符串是否已经被处理过
     return False(md5未处理过)  True(已经处理过，已有记录）
    """
    if not os.path.exists(config.md5_path):
        # 进入表示文件不存在，那肯定没有处理过这个md5了
        open(config.md5_path, "w", encoding='utf-8').close()
        return False
    else:
        with open(config.md5_path, "r", encoding='utf-8') as f:
            for line in f.readlines():
                if line.strip() == md5_str:
                    return True
        return False


def save_md5(md5_str: str):
    """将传入的md5保存到文件"""
    with open(config.md5_path, "a", encoding='utf-8') as f:
        f.write(md5_str + "\n")


def get_str_md5(input_str: str):
    """
    获取字符串的md5
    :param string:
    :return:
    """
    # 将字符串转换为bytes字节数组
    str_bytes = input_str.encode(encoding=encoding)

    # 创建md5对象
    md5_obj = hashlib.md5()  # 得到md5对象
    md5_obj.update(str_bytes)  # 更新内容（传入即将要转换的字节数组）
    md5_hex = md5_obj.hexdigest()  # 得到md5的十六进制字符串
    return md5_hex


class KnowledgeBaseService(object):
    """
    知识库服务
    1.设置chroma
    2.设置分割器
    3.数据存入向量数据库，保存文件的md5
    """

    def __init__(self):
        self.chroma = Chroma(
            collection_name=config.collection_name,  # 数据库的表名
            embedding_function=DashScopeEmbeddings(model="text-embedding-v4"),
            persist_directory=config.persist_directory,  # 数据库本地存储文件夹
        )  # 向量存储的实例，Chroma的存储对象
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,  # 分割后的文本段最大长度
            chunk_overlap=config.chunk_overlap,  # 连续文本段之间的字符重叠数量
            separators=config.separators,  # 自然段落划分的符号
            length_function=len  # 使用Python自带的len函数做长度统计的依据
        )  # 分词器实例

    def upload_by_str(self, data: str, filename):
        """
        将传入的字符串向量化，存入向量数据库
        1.获取md5值
        2.判断是否在文件里
         -->在：跳过
         -->不在：2.1.存入向量数据库;2.2.把文件的md5值保存起来
        :param data:
        :param filename:
        :return:
        """
        # 获取md5值
        md5_hex = get_str_md5(data)
        # 判断是否在文件里
        if check_md5(md5_hex):
            return "[跳过]内容已经存在知识库中"
        # 向量化
        if len(data) > config.max_split_char_number:
            # 拆分
            knowledge_chunks: list[str] = self.spliter.split_text(text=data)
        else:
            knowledge_chunks = [data]

        # 存入向量数据库

        # 存入向量数据库（补全 metadata，必传参数）
        # 为每个文本块生成对应的元数据（可自定义字段）
        metadata = {
            "source": filename,
            # 2025-01-01 10:00:00
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator": "Adrian",
        }
        self.chroma.add_texts(knowledge_chunks,
                              metadatas=[metadata for _ in knowledge_chunks])
        # 把文件的md5值保存起来
        save_md5(md5_hex)

        return "[成功]内容已经成功载入向量库"


if __name__ == '__main__':
    # res1 = get_str_md5("123")
    # print(res1)
    service = KnowledgeBaseService()
    data = "春风拂过枝头，嫩芽悄悄舒展，暖阳洒在松软的泥土上。花开遍地，溪水叮咚，万物在温柔里苏醒，满眼皆是清新与生机，处处洋溢着希望与美好。"
    res = service.upload_by_str(data, "spring")
    print(res)

"""
基于streamlit实现网页上传文件
pip install streamlit
运行：streamlit run app_file_upload.py
"""
import time
import streamlit as st
from knowledge_base import KnowledgeBaseService


st.title("文件上传")

# 1. 创建文件上传组件（单文件）
uploaded_file = st.file_uploader(
    label="选择一个文件",  # 组件显示的文字
    type=None,  # 支持的文件类型，None=所有类型；也可以写 ["csv", "txt", "jpg"]
    accept_multiple_files=False  # 单文件
)

# session_state就是一个字典
if "service" not in st.session_state:
    st.session_state["service"] = KnowledgeBaseService()

# 2. 判断用户是否上传了文件
if uploaded_file is not None:
    # 查看文件基本信息
    st.subheader("✅ 文件信息")
    st.write("文件名：", uploaded_file.name)
    st.write("文件大小：", uploaded_file.size, "字节")
    st.write("文件类型：", uploaded_file.type)

    # 3. 读取文件内容（根据类型处理）
    st.subheader("📄 文件内容预览")

    # 读取为字节数据（通用）
    # bytes_data = uploaded_file.getvalue()

    # 读取为文本（适合 txt、csv 等）
    # text_data = uploaded_file.read().decode("utf-8")
    text = uploaded_file.getvalue().decode("utf-8")
    # st.text_area("文件内容", text_data, height=300)

    with st.spinner("载入知识库中。。。"):       # 在spinner内的代码执行过程中，会有一个转圈动画
        time.sleep(1)
        result = st.session_state["service"].upload_by_str(text, uploaded_file.name)
        st.write(result)



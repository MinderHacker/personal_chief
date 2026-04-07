import os
from dotenv import load_dotenv
import requests

# 手动加载环境变量
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

print("测试直接调用DashScope API...")

# 获取API密钥
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    print("未找到DASHSCOPE_API_KEY环境变量")
    exit(1)

# 测试DashScope API
try:
    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "qwen3.5-plus",
        "input": {
            "prompt": "我有土豆和鸡蛋，能做什么菜？"
        },
        "parameters": {
            "max_tokens": 1000,
            "temperature": 0.7
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    result = response.json()
    print("API响应:")
    print(result.get("output", {}).get("text", "无响应内容"))
except Exception as e:
    print(f"API调用失败: {str(e)}")

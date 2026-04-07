import logging
import sys

# 配置日志格式：时间 - 级别 - 模块 - 消息
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"


def setup_logging(level=logging.INFO):
    """配置全局日志"""
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),  # 输出到控制台
            # logging.FileHandler("app.log")   # 如果需要存到文件可以开启
        ]
    )


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger"""
    return logging.getLogger(f"personal_chief.{name}")


# 初始化日志
setup_logging()

# 创建默认 logger
logger = get_logger("default")

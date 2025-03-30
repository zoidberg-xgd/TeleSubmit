"""
会话状态模型定义
"""

# 会话状态常量定义
STATE = {
    'START_MODE': 0,  # 选择上传模式（仅在混合模式时使用）
    'DOC': 1,         # 文档上传
    'MEDIA': 2,       # 媒体上传
    'DONE_MEDIA': 3,  # 完成媒体上传（混合模式时使用）
    'TAG': 4,         # 标签
    'LINK': 5,        # 链接
    'TITLE': 6,       # 标题
    'NOTE': 7,        # 简介
    'SPOILER': 8      # 是否将所有媒体设为剧透（是/否）
}

# 流程模式定义
MODE = {
    'MEDIA_ONLY': 1,    # 仅媒体上传模式
    'DOCUMENT_ONLY': 2, # 仅文档上传模式
    'MIXED': 3          # 混合上传模式
}
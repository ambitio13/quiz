# score_config.py
# 1. 各页面包含的交互对象（用于多样性好奇心计算）
PAGE_OBJECTS = {
    "index01": ["tree", "fish", "stone", "moss", "stream"],
    "index02": ["warm_room", "echo_horn", "dark_chef", "glow_bug", "rock_grandpa"],
    "index03": ["island", "photosynthesis", "water_cycle", "rock_weathering", "bird_flock", "traditional_arch"],
    "index04": ["desert_landform", "desert_rock", "desert_plant", "oasis", "camel", "ancient_civilization"],
    "index05": ["wooden_house", "winding_path", "tall_tree", "stream_step", "roof_flag", "glowing_window"]
}

# 2. 特异性好奇心计分标准（A/B/C选项，"我还想问"暂为0）
SPECIFIC_SCORE = {
    "A": 1,  # 概念性问题
    "B": 2,  # 解释性问题
    "C": 3,  # 假设性问题
    "ask": 1  # 暂未实现，固定为0
}

# 3. 其他好奇心计分标准
COGNITIVE_SCORE = 1  # 每个D选项（冷知识）得1分
DIVERSITY_SCORE = 1   # 每个交互对象得1分
PERCEPTUAL_MAX = 3    # 单个地图模糊对象最高得3分
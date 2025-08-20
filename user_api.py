# user_api.py
from flask import Blueprint, request, jsonify
import uuid, time
from redis_client import get as redis_get, set as redis_set
import mysql.connector
from config import DB  # 导入 DB 配置

user_bp = Blueprint('user', __name__)

@user_bp.route('/register', methods=['POST'])
def register_user():
    data = request.json
    name   = data.get('name', '').strip()
    age    = data.get('age')
    grade  = data.get('grade', '').strip()
    gender = data.get('gender', '').strip()
    region = data.get('region', '').strip()
    user_id = str(uuid.uuid4())  # 生成唯一用户ID
    
    if not all([name, age, grade, gender, region]) or gender not in {'男', '女'}:
        return jsonify({"msg": "invalid"}), 400

    # 写 user_info
    try:
        cnx = mysql.connector.connect(**DB)
        cur = cnx.cursor()
        cur.execute("""
            INSERT INTO user_info (id, name, age, grade, gender, region)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, name, int(age), grade, gender, region))
        cnx.commit()
        cur.close()
        cnx.close()
    except Exception as e:
        return jsonify({"msg": str(e)}), 500

    # 创建 Redis session（key: session:<uuid>）
    sid = str(uuid.uuid4())   # 放在 redis_set 之前即可
    session_obj = {
        "user_id": user_id,  # 绑定唯一用户ID
        "name": name,
        "gender": gender,
        "start": time.time(),

        # 把所有 index 可能用到的对象一次性写全
        "answers": {
            # index01
            "tree": [], "fish": [], "stone": [], "moss": [], "stream": [],
            # index02
            "glow_bug": [], "echo_horn": [], "warm_room": [],
            "rock_grandpa": [], "dark_chef": [],
            # 新增index03字段（对应6个对象）
            "island": [],               # block1：岛屿
            "photosynthesis": [],       # block2：光合作用
            "water_cycle": [],          # block3：水循环
            "rock_weathering": [],      # block4：岩石风化
            "bird_flock": [],           # block5：鸟群
            "traditional_arch": [],      # block6：传统建筑
            # 新增index04（沙漠场景）字段
            "desert_landform": [],    # 沙漠地貌
            "desert_rock": [],        # 岩石
            "desert_plant": [],       # 沙漠植物
            "oasis": [],              # 绿洲
            "camel": [],              # 骆驼
            "ancient_civilization": [],# 古代沙漠文明
            # 新增index05（乡野村庄）字段
            "wooden_house": [],     # 木质房屋
            "winding_path": [],     # 蜿蜒小径
            "tall_tree": [],        # 高大树木
            "stream_step": [],      # 溪流与石阶
            "roof_flag": [],        # 屋顶旗帜
            "glowing_window": []    # 发光窗户
        },
        "counts": {
            k: {"A":0,"B":0,"C":0,"D":0}
            for k in [
                "tree","fish","stone","moss","stream",
                "glow_bug","echo_horn","warm_room",
                "rock_grandpa","dark_chef"
                # 新增index03字段（对应6个对象）
                "island",
                "photosynthesis" ,
                "water_cycle",
                "rock_weathering",
                "bird_flock",
                "traditional_arch",
                 # 新增index04（沙漠场景）字段
                "desert_landform",
                "desert_rock",
                "desert_plant",
                "oasis",
                "camel",
                "ancient_civilization",
                 # 新增index05（乡野村庄）字段
                "wooden_house",
                "winding_path",
                "tall_tree",
                "stream_step",
                "roof_flag",
                "glowing_window"
            ]
        },
        "status_clicks": 0
    }
    redis_set(f"session:{sid}", session_obj, ex=3600)  # 1 小时过期
    return jsonify({"sessionId": sid})
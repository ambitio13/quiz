# user_api.py
from flask import Blueprint, request, jsonify
import uuid, time
from redis_client import set as redis_set
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

    if not all([name, age, grade, gender, region]) or gender not in {'男', '女'}:
        return jsonify({"msg": "invalid"}), 400

    # 写 user_info
    try:
        cnx = mysql.connector.connect(**DB)
        cur = cnx.cursor()
        cur.execute("""
            INSERT INTO user_info (id, name, age, grade, gender, region)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (str(uuid.uuid4()), name, int(age), grade, gender, region))
        cnx.commit()
        cur.close()
        cnx.close()
    except Exception as e:
        return jsonify({"msg": str(e)}), 500

    # 创建 Redis session（key: session:<uuid>）
    sid = str(uuid.uuid4())
    session_obj = {
        "name": name,
        "gender": gender,
        "start": time.time(),
        "answers": {k: [] for k in ["tree", "fish", "stone", "moss", "stream"]},
        "counts":  {k: {"A":0,"B":0,"C":0,"D":0} for k in ["tree","fish","stone","moss","stream"]},
        "status_clicks": 0
    }
    redis_set(f"session:{sid}", session_obj, ex=3600)  # 1 小时过期
    return jsonify({"sessionId": sid})
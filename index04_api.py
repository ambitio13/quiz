from flask import Blueprint, request, jsonify
import uuid, time, json
from redis_client import get as redis_get, set as redis_set, delete as redis_delete
import mysql.connector
from config import DB  # 导入 DB 配置
from score_utils import calculate_scores, update_score_tables  # 新增导入

index04_bp = Blueprint('index04', __name__)

def _get_session(sid):
    return redis_get(f"session:{sid}")

def _save_session(sid, session_obj):
    redis_set(f"session:{sid}", session_obj, ex=3600)



@index04_bp.route('/status_click_index04', methods=['POST'])
def status_click():
    data = request.json
    sid, cnt = data.get('sessionId'), data.get('count')
    sess = _get_session(sid)
    print("DEBUG sid:", sid)
    print("DEBUG cnt:", cnt)
    print("DEBUG session data:", sess)
    cnt = int(data.get('count', 0))
    if not sess or cnt not in {1, 2, 3}:
        return jsonify({"msg": "invalid"}), 400
    sess['status_clicks'] = cnt
    _save_session(sid, sess)
    return jsonify({"msg": "ok"})

@index04_bp.route('/answer_index04', methods=['POST'])
def collect_answer():
    data = request.json
    sid, block, key = data.get('sessionId'), data.get('block'), data.get('key')
    sess = _get_session(sid)
    if not sess or block not in sess["answers"]:
        return jsonify({"msg": "invalid"}), 400
    if len(sess["answers"][block]) >= 4:
        return jsonify({"msg": "max 4"}), 400
    sess["answers"][block].append(key)
    sess["counts"][block][key] += 1
    _save_session(sid, sess)
    return jsonify({"msg": "ok"})

@index04_bp.route('/finish_index04', methods=['POST'])
def finish_index04():
    print("finish payload:", request.json)
    data = request.json
    sid = data.get('sessionId')
    sess = redis_get(f"session:{sid}")
    if not sess:
        return jsonify({"msg": "no session"}), 400
    
    # 关键修改：从会话中获取用户注册时生成的唯一user_id
    user_id = sess.get("user_id")
    if not user_id:
        # 异常处理：若会话中无user_id，生成临时ID并记录警告
        user_id = f"temp_{str(uuid.uuid4())[:8]}"
        print(f"警告：会话{sid}未找到用户ID，使用临时ID：{user_id}")

    duration = int(time.time() - sess["start"])
    status_clicks = sess.get('status_clicks', 0)

    # 1. 沙漠场景空答案结构
    empty_answers = {k: [] for k in [
        "desert_landform", "desert_rock", "desert_plant",
        "oasis", "camel", "ancient_civilization"
    ]}

    # 2. 组装答案和计数
    answers = {k: json.dumps(sess["answers"].get(k, empty_answers[k])) for k in empty_answers}
    counts = {
        k: "|".join(f"{kk}:{vv}" for kk, vv in
                    sess["counts"].get(k, {"A":0,"B":0,"C":0,"D":0}).items())
        for k in empty_answers
    }

     # 新增：计算得分并更新数据库
    scores = calculate_scores("index04", sess)
    update_score_tables(
        page="index04",
        user_id=user_id,  # 传入统一用户ID
        user_name=sess["name"],
        gender=sess["gender"],
        scores=scores
    )

    sql = """
    INSERT INTO index04
        (
        id,
        name,
        gender,
        duration,
        desert_landform_answers,
        desert_rock_answers,
        desert_plant_answers,
        oasis_answers,
        camel_answers,
        ancient_civilization_answers,
        desert_landform_counts,
        desert_rock_counts,
        desert_plant_counts,
        oasis_counts,
        camel_counts,
        ancient_civilization_counts,
        status_clicks,
        desert_landform_ask,
        desert_rock_ask,
        desert_plant_ask,
        oasis_ask,
        camel_ask,
        ancient_civilization_ask
        )
        VALUES
        (
        %s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s
        )
    """

    # 4. 调整参数顺序（与SQL字段顺序一致）
    params = (
        user_id,
        sess["name"],
        sess["gender"],
        duration,

        # 答案字段
        answers["desert_landform"],
        answers["desert_rock"],
        answers["desert_plant"],
        answers["oasis"],
        answers["camel"],
        answers["ancient_civilization"],

        # 计数字段
        counts["desert_landform"],
        counts["desert_rock"],
        counts["desert_plant"],
        counts["oasis"],
        counts["camel"],
        counts["ancient_civilization"],

        # 知觉点击
        status_clicks,

        # “我还想问”次数
        sess["ask_counts"].get("desert_landform", 0),
        sess["ask_counts"].get("desert_rock", 0),
        sess["ask_counts"].get("desert_plant", 0),
        sess["ask_counts"].get("oasis", 0),
        sess["ask_counts"].get("camel", 0),
        sess["ask_counts"].get("ancient_civilization", 0),
    )
    try:
        cnx = mysql.connector.connect(** DB)
        cur = cnx.cursor()
        cur.execute(sql, params)
        cnx.commit()
        cur.close()
        cnx.close()
    except Exception as e:
        print(e)
        return jsonify({"msg": str(e)}), 500

    return jsonify({
        "msg": "saved",
        "user_id": user_id,  # 返回统一用户ID，便于前端跟踪
        "scores": scores
    })

@index04_bp.route('/record_ask_index04', methods=['POST'])
def record_ask_index04():
    data = request.json
    sid   = data.get('sessionId')
    block = data.get('block')
    sess  = _get_session(sid)
    valid_blocks = ["desert_landform", "desert_rock", "desert_plant",
                    "oasis", "camel", "ancient_civilization"]
    if not sess or block not in valid_blocks:
        return jsonify({"msg": "invalid"}), 400

    sess.setdefault("ask_counts", {})
    sess["ask_counts"].setdefault(block, 0)
    sess["ask_counts"][block] += 1
    _save_session(sid, sess)
    return jsonify({"msg": "ok"})
from flask import Blueprint, request, jsonify
import uuid, time, json
from redis_client import get as redis_get, set as redis_set, delete as redis_delete
import mysql.connector
from config import DB  # 导入 DB 配置
from score_utils import calculate_scores, update_score_tables  # 新增导入

index03_bp = Blueprint('index03', __name__)

def _get_session(sid):
    return redis_get(f"session:{sid}")

def _save_session(sid, session_obj):
    redis_set(f"session:{sid}", session_obj, ex=3600)



@index03_bp.route('/status_click_index03', methods=['POST'])
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

@index03_bp.route('/answer_index03', methods=['POST'])
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

@index03_bp.route('/finish_index03', methods=['POST'])
def finish_index03():
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

    # 拼 SQL 参数（与原逻辑一致）
    empty_answers = {k: [] for k in [
        "island", "photosynthesis", "water_cycle",
        "rock_weathering", "bird_flock", "traditional_arch"
    ]}

    answers = {k: json.dumps(sess["answers"].get(k, empty_answers[k])) for k in empty_answers}
    counts = {
        k: "|".join(f"{kk}:{vv}" for kk, vv in
                    sess["counts"].get(k, {"A":0,"B":0,"C":0,"D":0}).items())
        for k in empty_answers
    }

    # 新增：计算得分并更新数据库
    scores = calculate_scores("index03", sess)
    update_score_tables(
        page="index03",
        user_id=user_id,  # 传入统一用户ID
        user_name=sess["name"],
        gender=sess["gender"],
        scores=scores
    )

    sql = """
    INSERT INTO index03
    (id, name, gender, duration,
     island_answers, photosynthesis_answers, water_cycle_answers,
     rock_weathering_answers, bird_flock_answers, traditional_arch_answers,
     island_counts, photosynthesis_counts, water_cycle_counts,
     rock_weathering_counts, bird_flock_counts, traditional_arch_counts,
     status_clicks,island_ask, photosynthesis_ask, water_cycle_ask,
    rock_weathering_ask, bird_flock_ask, traditional_arch_ask)
    VALUES
    (%s,%s,%s,%s,
     %s,%s,%s,%s,%s,%s,
     %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    # 4. 调整参数顺序（与SQL字段顺序一致）
    params = (
        user_id,  # 关键修改：使用统一用户ID
        sess["name"],
        sess["gender"],
        duration,
        # 答案字段（按SQL顺序）
        answers["island"],
        answers["photosynthesis"],
        answers["water_cycle"],
        answers["rock_weathering"],
        answers["bird_flock"],
        answers["traditional_arch"],
        # 计数字段（按SQL顺序）
        counts["island"],
        counts["photosynthesis"],
        counts["water_cycle"],
        counts["rock_weathering"],
        counts["bird_flock"],
        counts["traditional_arch"],
        status_clicks,

        sess["ask_counts"].get("island", 0),
        sess["ask_counts"].get("photosynthesis", 0),
        sess["ask_counts"].get("water_cycle", 0),
        sess["ask_counts"].get("rock_weathering", 0),
        sess["ask_counts"].get("bird_flock", 0),
        sess["ask_counts"].get("traditional_arch", 0),
    )
    try:
        cnx = mysql.connector.connect(**DB)
        cur = cnx.cursor()
        cur.execute(sql, params)
        cnx.commit()
        cur.close()
        cnx.close()
    except Exception as e:
        print(e)
        return jsonify({"msg": str(e)}), 500

    # 完成后清掉 Redis
    # redis_delete(f"session:{sid}")
    return jsonify({
        "msg": "saved",
        "user_id": user_id,  # 返回统一用户ID，便于前端跟踪
        "scores": scores
    })

@index03_bp.route('/record_ask_index03', methods=['POST'])
def record_ask_index03():
    data = request.json
    sid   = data.get('sessionId')
    block = data.get('block')
    sess  = _get_session(sid)
    valid_blocks = ["island", "photosynthesis", "water_cycle",
                    "rock_weathering", "bird_flock", "traditional_arch"]
    if not sess or block not in valid_blocks:
        return jsonify({"msg": "invalid"}), 400

    sess.setdefault("ask_counts", {})
    sess["ask_counts"].setdefault(block, 0)
    sess["ask_counts"][block] += 1
    _save_session(sid, sess)
    return jsonify({"msg": "ok"})
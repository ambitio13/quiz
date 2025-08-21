from flask import Blueprint, request, jsonify
import uuid, time, json
from redis_client import get as redis_get, set as redis_set, delete as redis_delete
import mysql.connector
from config import DB  # 导入 DB 配置
from score_utils import calculate_scores, update_score_tables  # 新增导入


index02_bp = Blueprint('index02', __name__)

def _get_session(sid):
    return redis_get(f"session:{sid}")

def _save_session(sid, session_obj):
    redis_set(f"session:{sid}", session_obj, ex=3600)



@index02_bp.route('/status_click_index02', methods=['POST'])
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

@index02_bp.route('/answer_index02', methods=['POST'])
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

@index02_bp.route('/finish_index02', methods=['POST'])
def finish_index02():
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
    "warm_room", "echo_horn", "dark_chef",
    "glow_bug", "rock_grandpa"
    ]}
    answers = {k: json.dumps(sess["answers"].get(k, empty_answers[k]))
            for k in empty_answers}

    counts = {
        k: "|".join(f"{kk}:{vv}" for kk, vv in
                    sess["counts"].get(k, {"A":0,"B":0,"C":0,"D":0}).items())
        for k in empty_answers
    }
    # 新增：计算得分并更新数据库
    scores = calculate_scores("index02", sess)
    update_score_tables(
        page="index02",
        user_id=user_id,  # 传入统一用户ID
        user_name=sess["name"],
        gender=sess["gender"],
        scores=scores
    )

    sql = """
    INSERT INTO index02
    (id,
    name,
    gender,
    duration,
    warm_room_answers,
    echo_horn_answers,
    dark_chef_answers,
    glow_bug_answers,
    rock_grandpa_answers,
    warm_room_counts,
    echo_horn_counts,
    dark_chef_counts,
    glow_bug_counts,
    rock_grandpa_counts,
    status_clicks,
    warm_room_ask, echo_horn_ask, dark_chef_ask, glow_bug_ask, rock_grandpa_ask)
    VALUES
    (%s,%s,%s,%s,
    %s,%s,%s,%s,%s,
    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    params = (
        user_id,  # 关键修改：使用统一用户ID
        sess["name"],
        sess["gender"],
        duration,

        # 字段顺序：glow_bug, echo_horn, warm_room, rock_grandpa, dark_chef
        answers["warm_room"],    
        answers["echo_horn"],    
        answers["dark_chef"],   
        answers["glow_bug"], 
        answers["rock_grandpa"],    

        counts["warm_room"],
        counts["echo_horn"],
        counts["dark_chef"],
        counts["glow_bug"],
        counts["rock_grandpa"],

        status_clicks,

        sess["ask_counts"].get("warm_room", 0),
        sess["ask_counts"].get("echo_horn", 0),
        sess["ask_counts"].get("dark_chef", 0),
        sess["ask_counts"].get("glow_bug", 0),
        sess["ask_counts"].get("rock_grandpa", 0)
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


@index02_bp.route('/record_ask_index02', methods=['POST'])
def record_ask_index02():
    data = request.json
    sid   = data.get('sessionId')
    block = data.get('block')         # 期望是 warm_room / echo_horn ...
    sess  = _get_session(sid)
    valid_blocks = ["warm_room", "echo_horn", "dark_chef", "glow_bug", "rock_grandpa"]
    if not sess or block not in valid_blocks:
        return jsonify({"msg": "invalid"}), 400

    sess.setdefault("ask_counts", {})
    sess["ask_counts"].setdefault(block, 0)
    sess["ask_counts"][block] += 1
    _save_session(sid, sess)
    return jsonify({"msg": "ok"})
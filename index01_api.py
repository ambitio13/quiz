from flask import Blueprint, request, jsonify
import uuid, time, json
from redis_client import get as redis_get, set as redis_set, delete as redis_delete
import mysql.connector
from config import DB  # 导入 DB 配置

index01_bp = Blueprint('index01', __name__)

def _get_session(sid):
    return redis_get(f"session:{sid}")

def _save_session(sid, session_obj):
    redis_set(f"session:{sid}", session_obj, ex=3600)

@index01_bp.route('/status_click', methods=['POST'])
def status_click():
    data = request.json
    sid, cnt = data.get('sessionId'), data.get('count')
    sess = _get_session(sid)
    if not sess or cnt not in {1, 2, 3}:
        return jsonify({"msg": "invalid"}), 400
    sess['status_clicks'] = cnt
    _save_session(sid, sess)
    return jsonify({"msg": "ok"})

@index01_bp.route('/answer', methods=['POST'])
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

@index01_bp.route('/finish', methods=['POST'])
def finish_index01():
    data = request.json
    sid = data.get('sessionId')
    sess = _get_session(sid)
    if not sess:
        return jsonify({"msg": "no session"}), 400

    duration = int(time.time() - sess["start"])
    status_clicks = sess.get('status_clicks', 0)

    # 拼 SQL 参数（与原逻辑一致）
    empty_answers = {k: [] for k in ["tree", "fish", "stone", "moss", "stream"]}
    answers = {k: json.dumps(sess["answers"].get(k, empty_answers[k])) for k in empty_answers}
    counts = {
        k: "|".join(f"{kk}:{vv}" for kk, vv in sess["counts"].get(k, {"A":0,"B":0,"C":0,"D":0}).items())
        for k in ["tree","fish","stone","moss","stream"]
    }

    sql = """
    INSERT INTO index01
    (id,name,gender,duration,
     tree_answers,fish_answers,stone_answers,moss_answers,stream_answers,
     tree_counts,fish_counts,stone_counts,moss_counts,stream_counts,
     status_clicks)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    params = (
        str(uuid.uuid4()),
        sess["name"],
        sess["gender"],
        duration,
        answers["tree"],
        answers["fish"],
        answers["stone"],
        answers["moss"],
        answers["stream"],
        counts["tree"],
        counts["fish"],
        counts["stone"],
        counts["moss"],
        counts["stream"],
        status_clicks
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
    redis_delete(f"session:{sid}")
    return jsonify({"msg": "saved"})
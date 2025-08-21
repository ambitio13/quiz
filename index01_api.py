from flask import Blueprint, request, jsonify
import uuid, time, json
from redis_client import get as redis_get, set as redis_set, delete as redis_delete
import mysql.connector
from config import DB  # 导入 DB 配置
from score_utils import calculate_scores, update_score_tables  # 新增导入

from duihuademo import chat_once

index01_bp = Blueprint('index01', __name__)

def _get_session(sid):
    return redis_get(f"session:{sid}")

def _save_session(sid, session_obj):
    redis_set(f"session:{sid}", session_obj, ex=3600)

@index01_bp.route('/status_click_index01', methods=['POST'])
def status_click():
    data = request.json
    sid, cnt = data.get('sessionId'), data.get('count')
    sess = _get_session(sid)
    if not sess or cnt not in {1, 2, 3}:
        return jsonify({"msg": "invalid"}), 400
    sess['status_clicks'] = cnt
    _save_session(sid, sess)
    return jsonify({"msg": "ok"})

@index01_bp.route('/answer_index01', methods=['POST'])
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

@index01_bp.route('/finish_index01', methods=['POST'])
def finish_index01():
    data = request.json
    sid = data.get('sessionId')
    sess = _get_session(sid)
    if not sess:
        return jsonify({"msg": "no session"}), 400
    
    # 关键修改：从会话中获取用户注册时生成的唯一user_id
    # （该ID在用户注册时存入Redis，贯穿所有页面）
    user_id = sess.get("user_id")
    if not user_id:
        # 异常处理：若会话中无user_id，生成临时ID并记录警告
        user_id = f"temp_{str(uuid.uuid4())[:8]}"
        print(f"警告：会话{sid}未找到用户ID，使用临时ID：{user_id}")

    duration = int(time.time() - sess["start"])
    status_clicks = sess.get('status_clicks', 0)
    
    print("ask_counts from Redis:", sess.get("ask_counts"))

    # 拼 SQL 参数（与原逻辑一致）
    empty_answers = {k: [] for k in ["tree", "fish", "stone", "moss", "stream"]}
    answers = {k: json.dumps(sess["answers"].get(k, empty_answers[k])) for k in empty_answers}
    counts = {
        k: "|".join(f"{kk}:{vv}" for kk, vv in sess["counts"].get(k, {"A":0,"B":0,"C":0,"D":0}).items())
        for k in ["tree","fish","stone","moss","stream"]
    }

    # 计算得分并更新数据库（使用统一user_id）
    scores = calculate_scores("index01", sess)
    update_score_tables(
        page="index01",
        user_id=user_id,  # 传入统一用户ID
        user_name=sess["name"],
        gender=sess["gender"],
        scores=scores
    )

    # 插入index01表时使用统一user_id作为主键
    sql = """
    INSERT INTO index01
    (id, name, gender, duration,
    tree_answers, fish_answers, stone_answers, moss_answers, stream_answers,
    tree_counts, fish_counts, stone_counts, moss_counts, stream_counts,
    status_clicks,
    ask_count_tree, ask_count_fish, ask_count_stone, ask_count_moss, ask_count_stream)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    params = (
        user_id,
        sess["name"],
        sess["gender"],
        duration,
        answers["tree"], answers["fish"], answers["stone"], answers["moss"], answers["stream"],
        counts["tree"], counts["fish"], counts["stone"], counts["moss"], counts["stream"],
        status_clicks,
        sess["ask_counts"]["tree"],
        sess["ask_counts"]["fish"],
        sess["ask_counts"]["stone"],
        sess["ask_counts"]["moss"],
        sess["ask_counts"]["stream"]
    )
    try:
        cnx = mysql.connector.connect(**DB)
        cur = cnx.cursor()
        cur.execute(sql, params)
        cnx.commit()
        cur.close()
        cnx.close()
        
    except Exception as e:
        return jsonify({"msg": str(e)}), 500

    return jsonify({
        "msg": "saved",
        "user_id": user_id,  # 返回统一用户ID，便于前端跟踪
        "scores": scores
    })

#
@index01_bp.route('/chat_index01', methods=['POST'])
def chat():
    data = request.json
    sid, question = data.get('sessionId'), data.get('question')
    if not sid or not question:
        return jsonify({"msg": "invalid"}), 400

    # 调用大模型获取回答
    messages = [
        {"role": "system", "content": "你是魔法森林的智者，用简洁易懂的语言回答问题"},
        {"role": "user", "content": question}
    ]
    answer = chat_once(messages)  # 使用提供的大模型调用工具

    return jsonify({"answer": answer})

@index01_bp.route('/record_ask_index01', methods=['POST'])
def record_ask():
    """记录每个对象的"我还想问"交互次数"""
    data = request.json
    sid = data.get('sessionId')
    block = data.get('block')  # 新增：接收对象标识（tree/fish等）
    sess = _get_session(sid)
    valid_blocks = ["tree", "fish", "stone", "moss", "stream"]  # 验证对象合法性
    #rizhi
    print("record_ask received:", data)
    print("sid:", sid, "block:", block)
    print("session:", sess)
    sess = _get_session(sid)
    if not sess or block not in valid_blocks:
        print("invalid because:", "no session" if not sess else "block invalid")
        return jsonify({"msg": "invalid"}), 400

    # 累加对应对象的询问次数
    sess["ask_counts"][block] += 1
    _save_session(sid, sess)
    print("record_ask received data:", request.json)

    return jsonify({"msg": "ok"})
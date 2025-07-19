import os, uuid, json, time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import logging
import redis  # 导入redis库

# ------------------ 日志 ------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
CORS(app)

# ------------------ 数据库配置 ------------------
DB = {
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "8520456qwebq"),
    "host":     os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "interactive_quiz"),
    "port":     3306,
}

# ------------------ Redis 配置 ------------------
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_db = int(os.getenv("REDIS_DB", 0))

r = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)

sessions = r  # 使用Redis存储会话

# 根路由 -> 姓名页
@app.route('/')
def name_page():
    return send_from_directory('templates', 'name.html')

# 托管任意 .html
@app.route('/<page>.html')
def any_page(page):
    return send_from_directory('templates', f'{page}.html')

@app.route('/start', methods=['POST'])
def start_session():
    data = request.json
    name, gender = data.get('name'), data.get('gender')
    if not name or gender not in {'男', '女'}:
        return jsonify({"msg": "invalid"}), 400
    sid = str(uuid.uuid4())
    r.setex(sid, 3600, json.dumps({
        "name": name,
        "gender": gender,
        "start": time.time(),
        "answers": {k: [] for k in ["tree", "fish", "stone", "moss", "stream"]},
        "counts": {k: {"A": 0, "B": 0, "C": 0, "D": 0} for k in ["tree", "fish", "stone", "moss", "stream"]}
    }))
    return jsonify({"sessionId": sid})

@app.route('/answer', methods=['POST'])
def collect_answer():
    data = request.json
    sid, block, key = data.get('sessionId'), data.get('block'), data.get('key')
    if sid not in r.keys():
        return jsonify({"msg": "invalid"}), 400
    sess = json.loads(r.get(sid))
    if len(sess["answers"][block]) >= 4:
        return jsonify({"msg": "max 4"}), 400
    sess["answers"][block].append(key)
    sess["counts"][block][key] += 1
    r.setex(sid, 3600, json.dumps(sess))  # 更新会话
    return jsonify({"msg": "ok"})

@app.route('/status_click', methods=['POST'])
def status_click():
    data = request.json
    sid, cnt = data.get('sessionId'), data.get('count')
    if cnt not in {1, 2, 3}:
        return jsonify({"msg": "invalid"}), 400

    sess_json = sessions.get(sid)
    if not sess_json:
        return jsonify({"msg": "invalid"}), 400

    sess = json.loads(sess_json)
    sess['status_clicks'] = cnt
    sessions.setex(sid, 3600, json.dumps(sess))
    return jsonify({"msg": "ok"})

@app.route('/finish', methods=['POST'])
def finish_session():
    data = request.json
    sid = data.get('sessionId')

    sess_json = sessions.get(sid)
    if not sess_json:
        return jsonify({"msg": "no session"}), 400

    sess = json.loads(sess_json)
    sessions.delete(sid)  # 删除 Redis key
    duration = int(time.time() - sess["start"])
    status_clicks = sess.get('status_clicks', 0)

    # 默认值
    empty_answers = {k: [] for k in ["tree", "fish", "stone", "moss", "stream"]}
    empty_counts = {k: "A:0|B:0|C:0|D:0" for k in ["tree", "fish", "stone", "moss", "stream"]}

    answers = {k: json.dumps(sess["answers"].get(k, empty_answers[k])) for k in empty_answers}
    counts = {
        k: "|".join(f"{kk}:{vv}" for kk, vv in sess["counts"].get(k, {"A":0,"B":0,"C":0,"D":0}).items())
        for k in empty_counts
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
        return jsonify({"msg": "saved"})
    except Exception as e:
        print(e)
        return jsonify({"msg": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=False)
import os, uuid, json, time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

DB = {
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "123456"),
    "host":     os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "interactive_quiz"),
    "port":     3306,
}

sessions = {}

# ------------------ 路由 ------------------
@app.route('/')
def name_page():
    return send_from_directory('templates', 'name.html')

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
    sessions[sid] = {
        "name": name,
        "gender": gender,
        "start": time.time(),
        "answers": {k: [] for k in ["tree", "fish", "stone", "moss", "stream"]},
        "counts":  {k: {"A":0,"B":0,"C":0,"D":0} for k in ["tree","fish","stone","moss","stream"]},
        "status_clicks": 0
    }
    return jsonify({"sessionId": sid})

@app.route('/status_click', methods=['POST'])
def status_click():
    """仅把点击次数写回会话，不立即入库"""
    data = request.json
    sid, cnt = data.get('sessionId'), data.get('count')
    if sid not in sessions or cnt not in {1, 2, 3}:
        return jsonify({"msg": "invalid"}), 400
    sessions[sid]['status_clicks'] = cnt
    return jsonify({"msg": "ok"})

@app.route('/answer', methods=['POST'])
def collect_answer():
    data = request.json
    sid, block, key = data.get('sessionId'), data.get('block'), data.get('key')
    if sid not in sessions or block not in sessions[sid]["answers"]:
        return jsonify({"msg": "invalid"}), 400
    sess = sessions[sid]
    if len(sess["answers"][block]) >= 4:
        return jsonify({"msg": "max 4"}), 400
    sess["answers"][block].append(key)
    sess["counts"][block][key] += 1
    return jsonify({"msg": "ok"})

@app.route('/finish', methods=['POST'])
def finish_session():
    data = request.json
    sid = data.get('sessionId')
    if sid not in sessions:
        return jsonify({"msg": "no session"}), 400

    # ✅ 必须先弹出会话
    sess = sessions.pop(sid)
    duration = int(time.time() - sess["start"])

    # ✅ 使用会话中记录的状态点击次数
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
    app.run( debug=False)
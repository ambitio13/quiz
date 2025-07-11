import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import logging

# ------------------ 日志 ------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # 启用 CORS

@app.route('/')
def index():
    return send_from_directory('.', 'index01.html')

# ------------------ 数据库配置 ------------------
# 优先读环境变量，没有就用默认值
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "8520456qwebq")
DB_HOST     = os.getenv("DB_HOST", "localhost")   # 部署时改成服务器公网或内网 IP
DB_NAME     = os.getenv("DB_NAME", "interactive_quiz")

db_config = {
    "user":     DB_USER,
    "password": DB_PASSWORD,
    "host":     DB_HOST,
    "database": DB_NAME,
    "port":     3306,
}

# ------------------ 路由 ------------------
@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    block_id       = data.get("blockId")
    selected_option = data.get("selectedOption")

    if not (block_id and selected_option):
        return jsonify({"message": "Invalid data"}), 400

    try:
        conn   = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        table_name = f"block{block_id[-1]}"
        sql = f"INSERT INTO {table_name} (selected_option) VALUES (%s)"
        cursor.execute(sql, (selected_option,))
        conn.commit()

        cursor.close()
        conn.close()
        logging.info("Inserted into %s: %s", table_name, selected_option)
        return jsonify({"message": "Data received and stored successfully!"})

    except mysql.connector.Error as e:
        logging.error("MySQL error: %s", e)
        return jsonify({"message": "DB error"}), 500

# ------------------ 启动 ------------------
if __name__ == "__main__":
    # 在服务器上把 host 设为 0.0.0.0 才能对外暴露
    app.run(host="0.0.0.0", port=8000, debug=False)
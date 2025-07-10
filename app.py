from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 启用 CORS

# 定义一个路由，用于接收前端发送的 POST 请求
@app.route('/submit', methods=['POST'])
def submit():
    # 获取前端发送的 JSON 数据
    data = request.json
    # 打印接收到的数据（可以替换为其他处理逻辑）
    print("Received data:", data)
    # 返回一个响应
    return jsonify({"message": "Data received successfully!"})

if __name__ == '__main__':
    app.run(debug=True)
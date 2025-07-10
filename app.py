from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # 启用 CORS

# 修复拼写错误: @qpp -> @app
@app.route('/')
def index():
    return send_from_directory('.', 'index01.html')

# 修复拼写错误: method -> methods
@app.route('/submit', methods=['POST'])
def submit():
    # 获取前端发送的 JSON 数据
    data = request.json
    # 打印接收到的数据（可以替换为其他处理逻辑）
    print("Received data:", data)
    # 返回一个响应
    return jsonify({"message": "Data received successfully!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)  # 添加 host 和 port 参数
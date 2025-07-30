# app.py
import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from config import DB  # 导入 DB 配置

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

@app.route('/')
def root_redirect():
    return send_from_directory('templates', 'name.html')

@app.route('/<page>.html')
def any_page(page):
    return send_from_directory('templates', f'{page}.html')

# 注册蓝图
from user_api import user_bp
from index01_api import index01_bp
app.register_blueprint(user_bp, url_prefix='')
app.register_blueprint(index01_bp, url_prefix='')

if __name__ == '__main__':
    app.run(debug=False)
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
from index02_api import index02_bp
from index03_api import index03_bp
from index04_api import index04_bp
from index05_api import index05_bp
from stats_api import stats_bp

app.register_blueprint(user_bp, url_prefix='')
app.register_blueprint(index01_bp, url_prefix='')
app.register_blueprint(index02_bp, url_prefix='')
app.register_blueprint(index03_bp, url_prefix='')
app.register_blueprint(index04_bp, url_prefix='')
app.register_blueprint(index05_bp, url_prefix='')
app.register_blueprint(stats_bp, url_prefix='')

print("[LOG]index01_bp registered:", index01_bp.name)
print("[LOG]index02_bp registered:", index02_bp.name)
print("[LOG]index03_bp registered:", index03_bp.name)
print("[LOG]index04_bp registered:", index04_bp.name)
print("[LOG]index05_bp registered:", index05_bp.name)
print("[LOG]stats_bp registered:", stats_bp.name)


if __name__ == '__main__':
    app.run(debug=False)
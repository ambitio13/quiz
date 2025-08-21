from flask import Blueprint, request, jsonify
from redis_client import get as redis_get, set as redis_set

key_bp = Blueprint('key', __name__)

def _get_session(sid):
    """获取会话数据"""
    return redis_get(f"session:{sid}")

def _save_session(sid, session_obj):
    """保存会话数据，设置1小时过期"""
    redis_set(f"session:{sid}", session_obj, ex=3600)

@key_bp.route('/get_key_collection', methods=['POST'])
def get_key_collection():
    """获取当前会话的钥匙收集状态"""
    data = request.json
    sid = data.get('sessionId')
    
    if not sid:
        return jsonify({"status": "error", "msg": "invalid sessionId"}), 400
    
    # 获取会话，不存在则初始化
    sess = _get_session(sid)
    if not sess:
        # 新会话初始化为空收集状态
        sess = {"key_collection": {
            "index01": False,
            "index02": False,
            "index03": False,
            "index04": False,
            "index05": False
        }}
        _save_session(sid, sess)
    
    return jsonify({
        "status": "success",
        "collection": sess.get("key_collection", {})
    })

@key_bp.route('/collect_key', methods=['POST'])
def collect_key():
    """处理钥匙收集请求"""
    data = request.json
    sid = data.get('sessionId')
    page = data.get('page')
    
    # 验证参数
    if not sid or not page or page not in [f"index0{i}" for i in range(1,6)]:
        return jsonify({"status": "error", "msg": "invalid data"}), 400
    
    # 获取会话
    sess = _get_session(sid)
    if not sess:
        return jsonify({"status": "error", "msg": "invalid session"}), 400
    
    # 更新钥匙收集状态
    sess.setdefault("key_collection", {})
    sess["key_collection"][page] = True
    _save_session(sid, sess)
    
    return jsonify({
        "status": "success",
        "collection": sess["key_collection"]
    })

@key_bp.route('/get_key_status', methods=['POST'])
def get_key_status():
    """获取单个页面的钥匙状态"""
    data = request.json
    sid = data.get('sessionId')
    page = data.get('page')
    
    if not sid or not page:
        return jsonify({"status": "error", "msg": "invalid data"}), 400
    
    sess = _get_session(sid)
    if not sess:
        return jsonify({"status": "error", "msg": "invalid session"}), 400
    
    return jsonify({
        "status": "success",
        "collected": sess.get("key_collection", {}).get(page, False)
    })
@key_bp.route('/clear_key_collection', methods=['POST'])
def clear_key_collection():
    """清除当前会话的钥匙收集状态"""
    data = request.json
    sid = data.get('sessionId')
    
    if not sid:
        return jsonify({"status": "error", "msg": "invalid sessionId"}), 400
    
    return jsonify({
        "status": "success",
        "msg": "collection cleared"
    })
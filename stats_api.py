import json
import codecs
import zipfile
from io import BytesIO
from flask import Blueprint, request, jsonify, make_response
import mysql.connector
import csv
from config import DB
from score_config import PAGE_OBJECTS

# 初始化蓝图
stats_bp = Blueprint('stats', __name__)

# ------------------------------
# 核心查询函数（保持不变）
# ------------------------------
def get_user_basic_info(user_id):
    """获取用户基本信息（姓名、年龄等）"""
    cnx = None
    cur = None
    try:
        cnx = mysql.connector.connect(**DB)
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT name, age, grade, gender, region FROM user_info WHERE id = %s", (user_id,))
        return cur.fetchone() or {}
    except Exception as e:
        print(f"获取用户基本信息错误: {str(e)}")
        return {}
    finally:
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_user_answers(user_id):
    """获取用户在所有地图的答题记录"""
    answers = {}
    cnx = None
    cur = None
    try:
        cnx = mysql.connector.connect(** DB)
        cur = cnx.cursor(dictionary=True)
        for page in PAGE_OBJECTS.keys():
            cur.execute(f"SELECT * FROM {page} WHERE id = %s", (user_id,))
            data = cur.fetchone()
            if not data:
                continue
            page_answers = {
                obj: data.get(f"{obj}_answers", "[]") 
                for obj in PAGE_OBJECTS[page]
            }
            answers[page] = page_answers
        return answers
    except Exception as e:
        print(f"获取答题记录错误: {str(e)}")
        return {}
    finally:
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def get_page_data(user_id, page):
    """获取单个地图的完整数据（含时长、点击次数）"""
    cnx = None
    cur = None
    try:
        cnx = mysql.connector.connect(**DB)
        cur = cnx.cursor(dictionary=True)
        cur.execute(f"SELECT duration, status_clicks FROM {page} WHERE id = %s", (user_id,))
        return cur.fetchone() or {"duration": 0, "status_clicks": 0}
    except Exception as e:
        print(f"获取地图{page}数据错误: {str(e)}")
        return {"duration": 0, "status_clicks": 0}
    finally:
        if cur:
            cur.close()
        if cnx:
            cnx.close()

def query_user_inner(user_id):
    """内部调用的用户数据查询（返回原始数据）"""
    # 1. 基本信息
    basic = get_user_basic_info(user_id)
    if not basic:
        return None

    # 2. 分数查询
    map_scores = {}
    total_scores = {}
    cnx = None
    cur = None
    try:
        cnx = mysql.connector.connect(** DB)
        cur = cnx.cursor(dictionary=True)
        # 各地图分数
        cur.execute("SELECT * FROM map_scores WHERE user_id = %s", (user_id,))
        map_scores = {row['map_id']: row for row in cur.fetchall()}
        # 总分
        cur.execute("SELECT * FROM user_total_scores WHERE user_id = %s", (user_id,))
        total_scores = cur.fetchone() or {}
    except Exception as e:
        print(f"查询分数错误: {str(e)}")
    finally:
        if cur:
            cur.close()
        if cnx:
            cnx.close()

    # 3. 答题记录
    answers = get_user_answers(user_id)

    return {
        "user_id": user_id,
        "basic_info": basic,
        "map_scores": map_scores,
        "total_scores": total_scores,
        "answers": answers
    }

# ------------------------------
# 接口：查询单个用户（保持不变）
# ------------------------------
@stats_bp.route('/query_user', methods=['POST'])
def query_user():
    try:
        user_id = request.json.get('user_id')
        if not user_id:
            return jsonify({"msg": "请输入用户ID"}), 400

        user_data = query_user_inner(user_id)
        if not user_data:
            return jsonify({"msg": "用户不存在"}), 404

        return jsonify(user_data)
    except Exception as e:
        print(f"query_user接口错误: {str(e)}")
        return jsonify({"msg": "服务器内部错误"}), 500

# ------------------------------
# 接口：导出单个用户数据
# 优先使用三种表的导出方式（每个用户一行），保留全列导出方式的代码（已注释）
# ------------------------------
@stats_bp.route('/export_user', methods=['POST'])
def export_user():
    try:
        user_id = request.json.get('user_id')
        if not user_id:
            return jsonify({"msg": "请输入用户ID"}), 400

        # 获取用户数据
        user_data = query_user_inner(user_id)
        if not user_data:
            return jsonify({"msg": "用户不存在"}), 404

        basic = user_data["basic_info"]
        
        # 创建内存中的ZIP文件
        zip_output = BytesIO()
        with zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # ==============================================
            # 第二种方式：输出三张表（优先使用，每个用户一行）
            # ==============================================
            
            # 1. 总得分表（四种得分的分别的总分）
            total_scores_csv = BytesIO()
            total_wrapper = codecs.getwriter("utf-8-sig")(total_scores_csv)
            total_writer = csv.writer(total_wrapper, dialect='excel')
            
            total_headers = ["user_id", "name", "gender", "age", "grade", "region",
                            "total_specific_score", "total_cognitive_score",
                            "total_diversity_score", "total_perceptual_score"]
            total_writer.writerow(total_headers)
            
            # 计算四种得分的总和
            total_specific = sum(map_score.get("specific_score", 0) for map_score in user_data["map_scores"].values())
            total_cognitive = sum(map_score.get("cognitive_score", 0) for map_score in user_data["map_scores"].values())
            total_diversity = sum(map_score.get("diversity_score", 0) for map_score in user_data["map_scores"].values())
            total_perceptual = sum(map_score.get("perceptual_score", 0) for map_score in user_data["map_scores"].values())
            
            total_row = [
                user_id,
                basic.get("name", ""),
                basic.get("gender", ""),
                basic.get("age", ""),
                basic.get("grade", ""),
                basic.get("region", ""),
                total_specific,
                total_cognitive,
                total_diversity,
                total_perceptual
            ]
            total_writer.writerow(total_row)
            
            total_scores_csv.seek(0)
            zipf.writestr(f"{user_id}_total_scores.csv", total_scores_csv.getvalue())

            # 2. 选项表（用户选了哪些选项 - 每个用户一行）
            options_csv = BytesIO()
            options_wrapper = codecs.getwriter("utf-8-sig")(options_csv)
            options_writer = csv.writer(options_wrapper, dialect='excel')
            
            # 构建选项表表头（基本信息 + 所有地图的所有对象）
            options_headers = ["user_id", "name", "gender", "age", "grade", "region"]
            for page in PAGE_OBJECTS.keys():
                for obj in PAGE_OBJECTS[page]:
                    options_headers.append(f"{page}_{obj}_selected_options")
            options_writer.writerow(options_headers)
            
            # 构建选项表数据行（一个用户一行）
            options_row = [
                user_id,
                basic.get("name", ""),
                basic.get("gender", ""),
                basic.get("age", ""),
                basic.get("grade", ""),
                basic.get("region", "")
            ]
            for page in PAGE_OBJECTS.keys():
                page_answers = user_data["answers"].get(page, {})
                for obj in PAGE_OBJECTS[page]:
                    ans_json = page_answers.get(obj, "[]")
                    try:
                        answers = json.loads(ans_json)
                    except json.JSONDecodeError:
                        answers = []
                    options_row.append(",".join(answers) if answers else "none")
            
            options_writer.writerow(options_row)
            options_csv.seek(0)
            zipf.writestr(f"{user_id}_options.csv", options_csv.getvalue())

            # 3. 详细得分表（用户在每张地图的四种得分的统计 - 每个用户一行）
            detailed_scores_csv = BytesIO()
            detailed_wrapper = codecs.getwriter("utf-8-sig")(detailed_scores_csv)
            detailed_writer = csv.writer(detailed_wrapper, dialect='excel')
            
            # 构建详细得分表表头（基本信息 + 所有地图的详细得分）
            detailed_headers = ["user_id", "name", "gender", "age", "grade", "region"]
            for page in PAGE_OBJECTS.keys():
                detailed_headers.extend([
                    f"{page}_duration_sec",
                    f"{page}_status_clicks",
                    f"{page}_specific_score",
                    f"{page}_cognitive_score",
                    f"{page}_diversity_score",
                    f"{page}_perceptual_score",
                    f"{page}_total_score"
                ])
            detailed_writer.writerow(detailed_headers)
            
            # 构建详细得分表数据行（一个用户一行）
            detailed_row = [
                user_id,
                basic.get("name", ""),
                basic.get("gender", ""),
                basic.get("age", ""),
                basic.get("grade", ""),
                basic.get("region", "")
            ]
            for page in PAGE_OBJECTS.keys():
                page_data = get_page_data(user_id, page)
                map_score = user_data["map_scores"].get(page, {})
                
                specific = map_score.get("specific_score", 0)
                cognitive = map_score.get("cognitive_score", 0)
                diversity = map_score.get("diversity_score", 0)
                perceptual = map_score.get("perceptual_score", 0)
                total = specific + cognitive + diversity + perceptual
                
                detailed_row.extend([
                    page_data["duration"],
                    page_data["status_clicks"],
                    specific,
                    cognitive,
                    diversity,
                    perceptual,
                    total
                ])
            
            detailed_writer.writerow(detailed_row)
            detailed_scores_csv.seek(0)
            zipf.writestr(f"{user_id}_detailed_scores.csv", detailed_scores_csv.getvalue())

            # ==============================================
            # 第一种方式：输出全部的列（已注释，需要时取消注释并注释上面的代码）
            # ==============================================
            """
            # 1. 总分表CSV
            total_csv = BytesIO()
            total_wrapper = codecs.getwriter("utf-8-sig")(total_csv)
            total_writer = csv.writer(total_wrapper, dialect='excel')
            
            total_headers = ["user_id", "name", "gender", "age", "grade", "region"]
            total_score_fields = [k for k in user_data["total_scores"].keys() if k != "user_id"]
            total_headers.extend(total_score_fields)
            total_writer.writerow(total_headers)
            
            total_row = [
                user_id,
                basic.get("name", ""),
                basic.get("gender", ""),
                basic.get("age", ""),
                basic.get("grade", ""),
                basic.get("region", "")
            ]
            total_row.extend([user_data["total_scores"].get(field, "") for field in total_score_fields])
            total_writer.writerow(total_row)
            
            total_csv.seek(0)
            zipf.writestr(f"{user_id}_total_scores.csv", total_csv.getvalue())

            # 2. 详细表CSV（全列）
            detail_csv = BytesIO()
            detail_wrapper = codecs.getwriter("utf-8-sig")(detail_csv)
            detail_writer = csv.writer(detail_wrapper, dialect='excel')
            
            detail_headers = ["user_id", "name", "gender", "age", "grade", "region"]
            for page in PAGE_OBJECTS.keys():
                detail_headers.extend([
                    f"{page}_duration_sec",
                    f"{page}_status_clicks",
                    f"{page}_specific_score",
                    f"{page}_cognitive_score",
                    f"{page}_diversity_score",
                    f"{page}_perceptual_score"
                ])
                for obj in PAGE_OBJECTS[page]:
                    detail_headers.append(f"{page}_{obj}_selected_options")
            detail_writer.writerow(detail_headers)
            
            detail_row = [
                user_id,
                basic.get("name", ""),
                basic.get("gender", ""),
                basic.get("age", ""),
                basic.get("grade", ""),
                basic.get("region", "")
            ]
            for page in PAGE_OBJECTS.keys():
                page_data = get_page_data(user_id, page)
                map_score = user_data["map_scores"].get(page, {})
                detail_row.extend([
                    page_data["duration"],
                    page_data["status_clicks"],
                    map_score.get("specific_score", 0),
                    map_score.get("cognitive_score", 0),
                    map_score.get("diversity_score", 0),
                    map_score.get("perceptual_score", 0)
                ])
                page_answers = user_data["answers"].get(page, {})
                for obj in PAGE_OBJECTS[page]:
                    ans_json = page_answers.get(obj, "[]")
                    try:
                        answers = json.loads(ans_json)
                    except json.JSONDecodeError:
                        answers = []
                    detail_row.append(",".join(answers) if answers else "none")
            detail_writer.writerow(detail_row)
            
            detail_csv.seek(0)
            zipf.writestr(f"{user_id}_details.csv", detail_csv.getvalue())
            """

        # 完成ZIP响应
        zip_output.seek(0)
        response = make_response(zip_output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={user_id}_data.zip"
        response.headers["Content-type"] = "application/zip"
        return response
    except Exception as e:
        print(f"export_user接口错误: {str(e)}")
        return jsonify({"msg": "服务器内部错误"}), 500

# ------------------------------
# 接口：查询所有用户（保持不变）
# ------------------------------
@stats_bp.route('/query_all', methods=['GET'])
def query_all():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit

        cnx = None
        cur = None
        try:
            cnx = mysql.connector.connect(**DB)
            cur = cnx.cursor()
            cur.execute("SELECT COUNT(*) FROM user_info")
            total = cur.fetchone()[0]
            cur.execute("SELECT id FROM user_info LIMIT %s OFFSET %s", (limit, offset))
            user_ids = [row[0] for row in cur.fetchall()]
        finally:
            if cur:
                cur.close()
            if cnx:
                cnx.close()

        result = []
        for user_id in user_ids:
            user_data = query_user_inner(user_id)
            if user_data:
                result.append(user_data)

        return jsonify({
            "total": total,
            "page": page,
            "limit": limit,
            "data": result
        })
    except Exception as e:
        print(f"query_all接口错误: {str(e)}")
        return jsonify({"msg": "服务器内部错误"}), 500

# ------------------------------
# 接口：导出所有用户数据
# 优先使用三种表的导出方式（每个用户一行），保留全列导出方式的代码（已注释）
# ------------------------------
@stats_bp.route('/export_all', methods=['GET'])
def export_all():
    try:
        # 获取所有用户ID
        cnx = None
        cur = None
        try:
            cnx = mysql.connector.connect(** DB)
            cur = cnx.cursor()
            cur.execute("SELECT id FROM user_info")
            user_ids = [row[0] for row in cur.fetchall()]
        finally:
            if cur:
                cur.close()
            if cnx:
                cnx.close()

        if not user_ids:
            return jsonify({"msg": "没有用户数据"}), 404

        # 预加载所有用户数据
        all_user_data = []
        for user_id in user_ids:
            user_data = query_user_inner(user_id)
            if user_data:
                all_user_data.append(user_data)

        # 创建内存中的ZIP文件
        zip_output = BytesIO()
        with zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # ==============================================
            # 第二种方式：输出三张表（优先使用，每个用户一行）
            # ==============================================
            
            # 1. 总得分表（四种得分的分别的总分）
            total_scores_csv = BytesIO()
            total_wrapper = codecs.getwriter("utf-8-sig")(total_scores_csv)
            total_writer = csv.writer(total_wrapper, dialect='excel')
            
            total_headers = ["user_id", "name", "gender", "age", "grade", "region",
                            "total_specific_score", "total_cognitive_score",
                            "total_diversity_score", "total_perceptual_score"]
            total_writer.writerow(total_headers)
            
            for user_data in all_user_data:
                user_id = user_data["user_id"]
                basic = user_data["basic_info"]
                
                # 计算四种得分的总和
                total_specific = sum(map_score.get("specific_score", 0) for map_score in user_data["map_scores"].values())
                total_cognitive = sum(map_score.get("cognitive_score", 0) for map_score in user_data["map_scores"].values())
                total_diversity = sum(map_score.get("diversity_score", 0) for map_score in user_data["map_scores"].values())
                total_perceptual = sum(map_score.get("perceptual_score", 0) for map_score in user_data["map_scores"].values())
                
                total_row = [
                    user_id,
                    basic.get("name", ""),
                    basic.get("gender", ""),
                    basic.get("age", ""),
                    basic.get("grade", ""),
                    basic.get("region", ""),
                    total_specific,
                    total_cognitive,
                    total_diversity,
                    total_perceptual
                ]
                total_writer.writerow(total_row)
            
            total_scores_csv.seek(0)
            zipf.writestr("all_users_total_scores.csv", total_scores_csv.getvalue())

            # 2. 选项表（用户选了哪些选项 - 每个用户一行）
            options_csv = BytesIO()
            options_wrapper = codecs.getwriter("utf-8-sig")(options_csv)
            options_writer = csv.writer(options_wrapper, dialect='excel')
            
            # 构建选项表表头（基本信息 + 所有地图的所有对象）
            options_headers = ["user_id", "name", "gender", "age", "grade", "region"]
            for page in PAGE_OBJECTS.keys():
                for obj in PAGE_OBJECTS[page]:
                    options_headers.append(f"{page}_{obj}_selected_options")
            options_writer.writerow(options_headers)
            
            # 为每个用户添加一行数据
            for user_data in all_user_data:
                user_id = user_data["user_id"]
                basic = user_data["basic_info"]
                
                options_row = [
                    user_id,
                    basic.get("name", ""),
                    basic.get("gender", ""),
                    basic.get("age", ""),
                    basic.get("grade", ""),
                    basic.get("region", "")
                ]
                
                for page in PAGE_OBJECTS.keys():
                    page_answers = user_data["answers"].get(page, {})
                    for obj in PAGE_OBJECTS[page]:
                        ans_json = page_answers.get(obj, "[]")
                        try:
                            answers = json.loads(ans_json)
                        except json.JSONDecodeError:
                            answers = []
                        options_row.append(",".join(answers) if answers else "none")
                
                options_writer.writerow(options_row)
            
            options_csv.seek(0)
            zipf.writestr("all_users_options.csv", options_csv.getvalue())

            # 3. 详细得分表（用户在每张地图的四种得分的统计 - 每个用户一行）
            detailed_scores_csv = BytesIO()
            detailed_wrapper = codecs.getwriter("utf-8-sig")(detailed_scores_csv)
            detailed_writer = csv.writer(detailed_wrapper, dialect='excel')
            
            # 构建详细得分表表头（基本信息 + 所有地图的详细得分）
            detailed_headers = ["user_id", "name", "gender", "age", "grade", "region"]
            for page in PAGE_OBJECTS.keys():
                detailed_headers.extend([
                    f"{page}_duration_sec",
                    f"{page}_status_clicks",
                    f"{page}_specific_score",
                    f"{page}_cognitive_score",
                    f"{page}_diversity_score",
                    f"{page}_perceptual_score",
                    f"{page}_total_score"
                ])
            detailed_writer.writerow(detailed_headers)
            
            # 为每个用户添加一行数据
            for user_data in all_user_data:
                user_id = user_data["user_id"]
                basic = user_data["basic_info"]
                
                detailed_row = [
                    user_id,
                    basic.get("name", ""),
                    basic.get("gender", ""),
                    basic.get("age", ""),
                    basic.get("grade", ""),
                    basic.get("region", "")
                ]
                
                for page in PAGE_OBJECTS.keys():
                    page_data = get_page_data(user_id, page)
                    map_score = user_data["map_scores"].get(page, {})
                    
                    specific = map_score.get("specific_score", 0)
                    cognitive = map_score.get("cognitive_score", 0)
                    diversity = map_score.get("diversity_score", 0)
                    perceptual = map_score.get("perceptual_score", 0)
                    total = specific + cognitive + diversity + perceptual
                    
                    detailed_row.extend([
                        page_data["duration"],
                        page_data["status_clicks"],
                        specific,
                        cognitive,
                        diversity,
                        perceptual,
                        total
                    ])
                
                detailed_writer.writerow(detailed_row)
            
            detailed_scores_csv.seek(0)
            zipf.writestr("all_users_detailed_scores.csv", detailed_scores_csv.getvalue())

            # ==============================================
            # 第一种方式：输出全部的列（已注释，需要时取消注释并注释上面的代码）
            # ==============================================
            """
            # 1. 生成所有用户总分表
            total_csv = BytesIO()
            total_wrapper = codecs.getwriter("utf-8-sig")(total_csv)
            total_writer = csv.writer(total_wrapper, dialect='excel')
            
            total_headers = ["user_id", "name", "gender", "age", "grade", "region"]
            total_score_fields = set()
            for user_data in all_user_data:
                for k in user_data["total_scores"].keys():
                    if k != "user_id":
                        total_score_fields.add(k)
            total_score_fields = sorted(total_score_fields)
            total_headers.extend(total_score_fields)
            total_writer.writerow(total_headers)
            
            for user_data in all_user_data:
                user_id = user_data["user_id"]
                basic = user_data["basic_info"]
                total_scores = user_data["total_scores"]
                total_row = [
                    user_id,
                    basic.get("name", ""),
                    basic.get("gender", ""),
                    basic.get("age", ""),
                    basic.get("grade", ""),
                    basic.get("region", "")
                ]
                total_row.extend([total_scores.get(field, "") for field in total_score_fields])
                total_writer.writerow(total_row)
            
            total_csv.seek(0)
            zipf.writestr("all_users_total_scores.csv", total_csv.getvalue())

            # 2. 生成所有用户详细表（全列）
            detail_csv = BytesIO()
            detail_wrapper = codecs.getwriter("utf-8-sig")(detail_csv)
            detail_writer = csv.writer(detail_wrapper, dialect='excel')
            
            detail_headers = ["user_id", "name", "gender", "age", "grade", "region"]
            for page in PAGE_OBJECTS.keys():
                detail_headers.extend([
                    f"{page}_duration_sec",
                    f"{page}_status_clicks",
                    f"{page}_specific_score",
                    f"{page}_cognitive_score",
                    f"{page}_diversity_score",
                    f"{page}_perceptual_score"
                ])
                for obj in PAGE_OBJECTS[page]:
                    detail_headers.append(f"{page}_{obj}_selected_options")
            detail_writer.writerow(detail_headers)
            
            for user_data in all_user_data:
                user_id = user_data["user_id"]
                basic = user_data["basic_info"]
                detail_row = [
                    user_id,
                    basic.get("name", ""),
                    basic.get("gender", ""),
                    basic.get("age", ""),
                    basic.get("grade", ""),
                    basic.get("region", "")
                ]
                for page in PAGE_OBJECTS.keys():
                    page_data = get_page_data(user_id, page)
                    map_score = user_data["map_scores"].get(page, {})
                    detail_row.extend([
                        page_data["duration"],
                        page_data["status_clicks"],
                        map_score.get("specific_score", 0),
                        map_score.get("cognitive_score", 0),
                        map_score.get("diversity_score", 0),
                        map_score.get("perceptual_score", 0)
                    ])
                    page_answers = user_data["answers"].get(page, {})
                    for obj in PAGE_OBJECTS[page]:
                        ans_json = page_answers.get(obj, "[]")
                        try:
                            answers = json.loads(ans_json)
                        except json.JSONDecodeError:
                            answers = []
                        detail_row.append(",".join(answers) if answers else "none")
                detail_writer.writerow(detail_row)
            
            detail_csv.seek(0)
            zipf.writestr("all_users_details.csv", detail_csv.getvalue())
            """

        # 完成ZIP响应
        zip_output.seek(0)
        response = make_response(zip_output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=all_users_data.zip"
        response.headers["Content-type"] = "application/zip"
        return response
    except Exception as e:
        print(f"export_all接口错误: {str(e)}")
        return jsonify({"msg": "服务器内部错误"}), 500

# score_utils.py
import json
import mysql.connector
from config import DB
from score_config import PAGE_OBJECTS, SPECIFIC_SCORE, COGNITIVE_SCORE, DIVERSITY_SCORE, PERCEPTUAL_MAX

def calculate_scores(page, sess):
    """计算单地图的四项分数"""
    scores = {
        "specific": 0,
        "cognitive": 0,
        "diversity": 0,
        "perceptual": 0
    }
    objects = PAGE_OBJECTS.get(page, [])
    interacted = set()  # 记录已交互的对象（去重）

    # 1. 特异性+认知性+多样性（基于用户答案）
    for obj in objects:
        answers = sess["answers"].get(obj, [])
        if not answers:
            continue
        interacted.add(obj)  # 标记为已交互

        # 计算该对象的特异性和认知性分数
        for ans in answers:
            if ans in ["A", "B", "C"]:
                scores["specific"] += SPECIFIC_SCORE[ans]
            elif ans == "D":
                scores["cognitive"] += COGNITIVE_SCORE
        # （2）新增：“我还想问”次数得分
        ask_count = sess["ask_counts"].get(obj, 0)
        scores["specific"] += ask_count * SPECIFIC_SCORE["ask"]
        
    # 2. 多样性分数（交互对象数量）
    scores["diversity"] = len(interacted) * DIVERSITY_SCORE

    # 3. 知觉性分数（模糊对象点击次数，最高3分）
    scores["perceptual"] = min(sess.get("status_clicks", 0), PERCEPTUAL_MAX)

    return scores

def update_score_tables(page, user_id, user_name, gender, scores):
    """更新得分表和总分表"""
    cnx = mysql.connector.connect(** DB)
    try:
        cursor = cnx.cursor()

        # 1. 更新单地图得分表（存在则更新，不存在则插入）
        map_sql = """
        INSERT INTO map_scores 
        (user_id, map_id, specific_score, cognitive_score, diversity_score, perceptual_score)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        specific_score = VALUES(specific_score),
        cognitive_score = VALUES(cognitive_score),
        diversity_score = VALUES(diversity_score),
        perceptual_score = VALUES(perceptual_score)
        """
        map_params = (user_id, page, scores["specific"], scores["cognitive"], scores["diversity"], scores["perceptual"])
        cursor.execute(map_sql, map_params)

        # 2. 计算用户在所有地图的总分
        total_sql = """
        SELECT 
            SUM(specific_score) AS sum_specific,
            SUM(cognitive_score) AS sum_cognitive,
            SUM(diversity_score) AS sum_diversity,
            SUM(perceptual_score) AS sum_perceptual
        FROM map_scores 
        WHERE user_id = %s
        """
        cursor.execute(total_sql, (user_id,))
        totals = cursor.fetchone()

        # 3. 更新用户总分表
        user_sql = """
        INSERT INTO user_total_scores 
        (user_id, user_name, user_gender, total_specific, total_cognitive, total_diversity, total_perceptual)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        user_name = VALUES(user_name),
        user_gender = VALUES(user_gender),
        total_specific = VALUES(total_specific),
        total_cognitive = VALUES(total_cognitive),
        total_diversity = VALUES(total_diversity),
        total_perceptual = VALUES(total_perceptual)
        """
        user_params = (
            user_id, user_name, gender,
            totals[0] or 0, totals[1] or 0, totals[2] or 0, totals[3] or 0
        )
        cursor.execute(user_sql, user_params)
        cnx.commit()
    except Exception as e:
        cnx.rollback()
        raise e
    finally:
        cursor.close()
        cnx.close()
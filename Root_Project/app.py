from flask import Flask, render_template, request, jsonify
import pandas as pd
from geopy.distance import geodesic
import os
import random

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHELTER_CSV_PATH = os.path.join(BASE_DIR, "shelters.csv")

def load_shelter_data():
    if not os.path.exists(SHELTER_CSV_PATH):
        raise FileNotFoundError(f"CSVファイルが見つかりません: {SHELTER_CSV_PATH}")
    try:
        df = pd.read_csv(SHELTER_CSV_PATH, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(SHELTER_CSV_PATH, encoding="cp932")
        except Exception as e:
            raise e
    df.columns = [c.strip() for c in df.columns]
    return df

@app.route("/")
def index():
    return render_template("map.html")

# --- 新・推薦アルゴリズム (不要物資回避ロジック対応版) ---
def calculate_recommendation_score(user_profile, shelter_features):
    """
    総合スコア (0-100) を計算する。
    """
    
    congestion_val = float(shelter_features["congestion"])
    
    # --- 1. 物資スコア計算 (ペナルティ方式導入) ---
    # プラス値: あれば加点 (欲しい)
    # マイナス値: あれば減点 (避ける / 他の人に譲る)
    PRIORITY_WEIGHTS = {
        "最高": 10, 
        "高": 6, 
        "中": 3, 
        "低": -5,   # あれば減点
        "最低": -20 # あれば大きく減点
    }
    
    total_weight = 0    # 期待する満点の分母（プラス要素のみ加算）
    acquired_weight = 0 # 実際の獲得スコア（マイナス要素は減算）
    
    for item in ["supply_a", "supply_b", "supply_c"]:
        priority = user_profile["needs"].get(item, "中")
        weight = PRIORITY_WEIGHTS.get(priority, 3)
        
        # 分母には「欲しいもの（プラス評価）」だけを足す
        if weight > 0:
            total_weight += weight
            
        item_stock = float(shelter_features[item])
        
        # 在庫がある場合、weightを加算（マイナスなら減点される）
        if item_stock >= 20:
            acquired_weight += weight
        elif item_stock > 0:
            # 在庫が少しある場合は効果を半分にする
            acquired_weight += (weight * 0.5)

    # 物資スコアの算出
    if total_weight > 0:
        # 通常パターン: (獲得点 / 満点) * 100
        # ※acquired_weightがマイナスになりすぎるとスコアが負になるが許容する
        supply_score = (acquired_weight / total_weight) * 100.0
    else:
        # 特例: 全て「低」か「最低」を選んだ場合
        # 「在庫がない」のが理想(100点)とし、在庫がある(ペナルティ)分だけ減点する
        # acquired_weight は 0 またはマイナスの値になっているはず
        supply_score = 100.0 + acquired_weight

    # スコアの上限は100点に抑える（下限はペナルティで大きく下がるのを許容）
    supply_score = min(100.0, supply_score)


    # --- 2. 総合スコア合成 ---
    people_count = user_profile["total_people"]
    
    if people_count >= 6:
        # [大人数] 混雑回避優先
        congestion_score = max(0, 100 - congestion_val)
        w_congestion = 7.0
        w_supply     = 3.0
    else:
        # [少人数] 物資合致＆混雑度合いが高い場所を優先
        congestion_score = congestion_val 
        w_congestion = 5.0
        w_supply     = 5.0
    
    total_score = (
        (congestion_score * w_congestion) + 
        (supply_score * w_supply)
    ) / (w_congestion + w_supply)
    
    return round(total_score, 1), round(supply_score, 1)

# 数値変換ヘルパー
def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

# 文字列取得ヘルパー
def safe_str(val, default="中"):
    if val is None or val == "":
        return default
    return str(val)

@app.route("/get_disaster_shelters", methods=["POST"])
def get_disaster_shelters():
    try:
        data = request.json
        user_loc = (data["lat"], data["lng"])
        
        adult = safe_int(data.get("adult_count"), 1)
        child = safe_int(data.get("child_count"), 0)
        total = max(1, adult + child)

        user_profile = {
            "needs": {
                "supply_a": safe_str(data.get("supply_a")),
                "supply_b": safe_str(data.get("supply_b")),
                "supply_c": safe_str(data.get("supply_c"))
            },
            "total_people": total
        }

        df = load_shelter_data()
        
        candidates = []
        for _, row in df.iterrows():
            dist = geodesic(user_loc, (row["lat"], row["lng"])).meters
            candidates.append({
                "name": row["name"], "lat": row["lat"], "lng": row["lng"], "distance": dist
            })
        nearest_5 = sorted(candidates, key=lambda x: x["distance"])[:5]
        
        results = []
        for cand in nearest_5:
            features = {
                "congestion": random.randint(0, 100),
                "supply_a": random.randint(0, 100),
                "supply_b": random.randint(0, 100),
                "supply_c": random.randint(0, 100)
            }
            total_score, supply_rate = calculate_recommendation_score(user_profile, features)
            
            results.append({
                "name": cand["name"],
                "lat": cand["lat"],
                "lng": cand["lng"],
                "distance": cand["distance"],
                "data": features,
                "match_score": total_score,
                "match_rate": supply_rate
            })
        
        sorted_res = sorted(results, key=lambda x: x["match_score"], reverse=True)
        return jsonify(sorted_res)

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/recalculate_shelters", methods=["POST"])
def recalculate_shelters():
    try:
        data = request.json
        shelter_list = data.get("shelter_list", [])
        
        adult = safe_int(data.get("adult_count"), 1)
        child = safe_int(data.get("child_count"), 0)
        total = max(1, adult + child)
        
        user_profile = {
            "needs": {
                "supply_a": safe_str(data.get("supply_a")),
                "supply_b": safe_str(data.get("supply_b")),
                "supply_c": safe_str(data.get("supply_c"))
            },
            "total_people": total
        }
        
        results = []
        for item in shelter_list:
            features = item["data"]
            total_score, supply_rate = calculate_recommendation_score(user_profile, features)
            
            item["match_score"] = total_score
            item["match_rate"] = supply_rate
            results.append(item)
            
        sorted_res = sorted(results, key=lambda x: x["match_score"], reverse=True)
        return jsonify(sorted_res)

    except Exception as e:
        print(f"[ERROR Recalc] {e}")
        return jsonify({"error": str(e)}), 500

# 既存エンドポイント
@app.route("/get_nearest_shelters", methods=["POST"])
def get_nearest_shelters():
    try:
        data = request.json
        user_loc = (data["lat"], data["lng"])
        df = load_shelter_data()
        shelters = []
        for _, row in df.iterrows():
            dist = geodesic(user_loc, (row["lat"], row["lng"])).meters
            shelters.append({"name": row["name"], "lat": row["lat"], "lng": row["lng"], "distance": dist})
        sorted_s = sorted(shelters, key=lambda x: x["distance"])
        if not sorted_s: return jsonify([])
        start_idx = 1 if len(sorted_s) >= 2 else 0
        end_idx = 4 if len(sorted_s) >= 4 else len(sorted_s)
        return jsonify(sorted_s[start_idx:end_idx])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_weather_disaster_info", methods=["POST"])
def get_weather_disaster_info():
    return jsonify([{
        "title": "気象警報", "type": "大雨", "updated": "Now", 
        "target_areas": ["京都市"], "headline": "警戒", "link": "#"
    }])

if __name__ == "__main__":
    app.run(debug=True)
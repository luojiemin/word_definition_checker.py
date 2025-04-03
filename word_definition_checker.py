# Web词汇释义比对系统（加强版：包含包含性判定 + 常用度计算）
# 安装依赖： pip install streamlit requests scikit-learn pandas openpyxl beautifulsoup4 lxml

import streamlit as st
import pandas as pd
import requests
import time
import io
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 获取有道词典网页释义
def get_youdao_web_definition(word):
    url = f"https://dict.youdao.com/w/{word}"
    try:
        res = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "lxml")
        trans_container = soup.find("div", id="phrsListTab")
        if not trans_container:
            return ""
        lis = trans_container.find_all("li")
        explanations = [li.get_text(strip=True) for li in lis if li.get_text(strip=True)]
        return "; ".join(explanations[:5])  # 保留前5项备用
    except Exception as e:
        st.warning(f"有道网页释义获取失败：{e}")
        return ""

# 判断释义是否被包含（完全包含规则）
def is_definition_contained(user_def, youdao_def):
    user_terms = [s.strip() for s in user_def.replace('；', ';').replace('，', ',').replace(';', ',').split(',') if s.strip()]
    yd_terms = [s.strip() for s in youdao_def.replace('；', ';').replace('，', ',').replace(';', ',').split(',') if s.strip()]
    return all(any(user in yd for yd in yd_terms) for user in user_terms)

# 文本相似度（备用）
def similarity(a, b):
    try:
        v = TfidfVectorizer().fit_transform([str(a), str(b)])
        return cosine_similarity(v[0:1], v[1:2])[0][0]
    except:
        return 0.0

# 常用度计算（越靠前越高）
def compute_commonness(user_def, youdao_def):
    user_terms = [s.strip() for s in user_def.replace('；', ';').replace('，', ',').replace(';', ',').split(',') if s.strip()]
    yd_terms = [s.strip() for s in youdao_def.replace('；', ';').replace('，', ',').replace(';', ',').split(',') if s.strip()]
    score = 0
    for term in user_terms:
        for i, yd_term in enumerate(yd_terms[:2]):  # 仅看前2项
            if term in yd_term:
                score += (2 - i) / 2  # 第1项得1，第2项得0.5
    return min(score / len(user_terms), 1.0) if user_terms else 0

# 相似度等级
def label_similarity(score):
    if score >= 0.8:
        return "高一致"
    elif score >= 0.6:
        return "可接受"
    else:
        return "需核查"

# Streamlit 页面
st.title("词汇释义比对系统（精确包含 + 常用度判断）")
st.markdown("系统使用有道网页中文释义，支持完整包含判定，相似度备用，并新增常用度评分。")

uploaded_file = st.file_uploader("上传词库Excel文件（含 单词 和 释义 两列）")

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        if "单词" in df.columns and "释义" in df.columns:
            with st.spinner("正在抓取释义并比对..."):
                df["有道释义"] = df["单词"].apply(lambda w: get_youdao_web_definition(str(w)))
                df["是否包含"] = df.apply(lambda row: is_definition_contained(row["释义"], row["有道释义"]), axis=1)
                df["相似度"] = df.apply(lambda row: 1.0 if row["是否包含"] else similarity(row["释义"], row["有道释义"]), axis=1)
                df["相似度等级"] = df["相似度"].apply(label_similarity)
                df["常用度"] = df.apply(lambda row: compute_commonness(row["释义"], row["有道释义"]), axis=1)
                df["需人工复查"] = df["相似度等级"] == "需核查"

            st.success("比对完成，以下是结果：")
            st.dataframe(df)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="全部结果")
                df[df["需人工复查"]].to_excel(writer, index=False, sheet_name="需人工复查")
                df[df["相似度等级"] == "高一致"].to_excel(writer, index=False, sheet_name="高一致")
            st.download_button("下载Excel报告", data=output.getvalue(), file_name="释义比对报告_精确版.xlsx")

        else:
            st.error("Excel中必须包含 '单词' 和 '释义' 两列")
    except Exception as e:
        st.error(f"处理过程中出现错误：{e}")
else:
    st.info("请上传文件")

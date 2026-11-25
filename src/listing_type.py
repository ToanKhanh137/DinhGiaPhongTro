"""Bài toán phụ (PHÂN LOẠI): xác định loại tin đăng
    R = phòng / căn riêng, một mức giá
    G = ở ghép, giá tính theo người / giường (homestay, KTX, sleepbox, slot...)
    N = tin nhiều phòng / khoảng giá ("từ 3tr", "3tr5 - 4tr5") -> giá đăng không đại diện cho 1 phòng cụ thể

Phân tích lỗi cho thấy G và N là nguồn sai số lớn nhất của mô hình giá (nhiễu nhãn).

Dữ liệu có nhãn: data/labels/listing_type_labels.csv (540 tin gán tay; rà soát lần 2 ngày 04/11 theo
docs/HUONG_DAN_GAN_NHAN.md, nhật ký thay đổi: data/labels/label_review_log.csv), cột `sample`:
  - theo_luat  (240 tin): 1/3 tin luật bắt là G, 1/3 luật bắt là N, 1/3 phần còn lại -> nhiều ví dụ G/N để HỌC
  - ngau_nhien (300 tin): chọn ngẫu nhiên hoàn toàn -> phản ánh phân bố thật, dùng để ĐÁNH GIÁ KHÁCH QUAN
    (điểm chấm trên mẫu theo_luat bị lạc quan cho luật regex vì chính luật đã chọn mẫu)

  1. So sánh: luật regex  vs  TF-IDF + {Logistic Regression, Naive Bayes, Linear SVM}  vs  kết hợp
     (Stratified 5-fold x 5 lần trên cả 540 tin; điểm báo cáo riêng cho 300 tin ngẫu nhiên, chọn mô hình theo điểm này)
  2. Gán nhãn toàn bộ dữ liệu bằng mô hình tốt nhất -> data/processed/listing_type.csv
  3. Ảnh hưởng tới mô hình giá: đánh giá trên tin loại R, huấn luyện trên (a) tất cả, (b) chỉ R

    python src/listing_type.py
"""
import re
import warnings

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold, RepeatedStratifiedKFold, cross_val_predict
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import make_pipeline, make_union
from sklearn.preprocessing import FunctionTransformer
from sklearn.svm import LinearSVC

from common import PROCESSED_DIR, REPORTS_DIR, ROOT
from features import FEATURE_COLS, add_features, strip_accents
from train import SEED, evaluate, models

warnings.filterwarnings("ignore")
LABELS = ["R", "G", "N"]
LABEL_FILE = ROOT / "data" / "labels" / "listing_type_labels.csv"
LABEL_FILE_V1 = ROOT / "data" / "labels" / "listing_type_labels_v1.csv"  # bản trước khi rà soát lần 2

# Luật (trên văn bản đã bỏ dấu, CHƯA che giá vì khoảng giá chính là tín hiệu ở đây)
SHARED_RE = (r"o ghep|tro ghep|phong ghep|tim (?:ban|nguoi) o (?:ghep|cung)|(?:nam|nu) ghep|\bslot\b|sleep ?box"
             r"|ky tuc xa|\bktx\b|homestay|home stay|\bdorm\b|giuong tang|pass (?:giuong|slot)")
RANGE_RE = (r"\d+(?:[.,]\d+)?\s*(?:tr|trieu|k)\w*\s*(?:-|–|den|~|toi)\s*\d+(?:[.,]\d+)?\s*(?:tr|trieu|k)"
            r"|(?:chi |gia )?tu\s+\d+(?:[.,]\d+)?\s*(?:tr|trieu)\w*\s*(?:-|–|den|toi)"
            r"|\d{1,3}(?:[.,]\d{3}){2}\s*d?\s*(?:-|–|den)\s*\d{1,3}(?:[.,]\d{3}){2}")


def rule_predict(texts: pd.Series) -> np.ndarray:
    shared = texts.str.contains(SHARED_RE)
    rng = texts.str.contains(RANGE_RE)
    return np.where(shared, "G", np.where(rng, "N", "R"))


# Luật v2 (thêm sau khi phân tích lỗi trên mẫu ngẫu nhiên: lớp N bị bỏ sót nhiều vì người đăng liệt kê nhiều mức
# giá theo đủ kiểu -- "3tr6 với 3tr8", "tầng 1: 3,5 triệu, tầng 2: 3 triệu", "3,8 - 4 - 4,1 triệu").
_PRICE_RE = re.compile(r"(?<![\d.,])(\d{1,2})(?:[.,](\d{1,3}))?\s*(?:tr|trieu|t\b|cu\b)(\d{0,3})"
                       r"|(?<![\d.,])(\d{1,2})[.,](\d{3})[.,]000(?![\d])")
_FROM_RE = re.compile(r"(?:gia|chi|thue)\s*(?:chi\s*)?tu\s*:?\s*\d")
# dãy số chỉ có đơn vị ở cuối: "3,8 - 4 - 4,1 triệu", "3 / 3,5tr", "2tr5 va 3tr"
_LIST_RE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:-|–|/|va|voi)\s*\d+(?:[.,]\d+)?\s*(?:tr|trieu)")


def room_prices(text: str) -> set:
    """Các mức giá phòng (triệu) nhắc trong mô tả đã bỏ dấu; bỏ giá điện nước (vài nghìn / trăm nghìn)."""
    found = set()
    for m in _PRICE_RE.finditer(text):
        if m.group(1):
            whole, dec, tail = m.group(1), m.group(2) or "", m.group(3) or ""
            frac = dec or tail                       # "3,5 tr" hoặc "3tr5" / "3tr450"
            value = float(f"{whole}.{frac}") if frac else float(whole)
        else:
            value = float(f"{m.group(4)}.{m.group(5)}")  # "3.500.000"
        if 0.8 <= value <= 30:
            found.add(round(value, 2))
    return found


def rule_v2_predict(texts: pd.Series) -> np.ndarray:
    base = rule_predict(texts)
    multi = texts.map(lambda t: len(room_prices(t)) >= 2 or bool(_FROM_RE.search(t))
                      or bool(_LIST_RE.search(t))).to_numpy()
    return np.where((base == "R") & multi, "N", base)


def price_features(texts):
    s = pd.Series(texts)
    n = s.map(lambda t: min(len(room_prices(t)), 4))
    return np.column_stack([n == 0, n == 1, n >= 2, s.str.contains(_FROM_RE),
                            s.str.contains(_LIST_RE)]).astype(float) * 3.0


def text_for_clf(df):
    # Văn bản bỏ dấu, GIỮ NGUYÊN chữ số (luật và đặc trưng mức giá cần đọc giá trị)
    return df["text"].fillna("").map(strip_accents)


def zero_digits(text):
    # Cho TF-IDF: gom mọi chữ số thành "0" để "3tr5-4tr" và "2tr-2tr5" thành cùng một token
    return re.sub(r"\d", "0", text)


def rule_onehot(texts):
    pred = rule_predict(pd.Series(texts))
    return np.column_stack([(pred == l).astype(float) for l in LABELS]) * 3.0  # nhân 3 để nổi bật so với TF-IDF


def rule_v2_onehot(texts):
    pred = rule_v2_predict(pd.Series(texts))
    return np.column_stack([(pred == l).astype(float) for l in LABELS]) * 3.0  # nhân 3 để nổi bật so với TF-IDF


class RuleClassifier:
    """Bọc luật regex thành "mô hình" có fit/predict để dùng chung quy trình."""
    def __init__(self, fn):
        self.fn = fn

    def fit(self, X, y):
        return self

    def predict(self, X):
        return self.fn(pd.Series(X))


RULES = {"Luật regex": rule_predict, "Luật regex v2 (+ đếm mức giá)": rule_v2_predict}


def classifiers():
    word = dict(ngram_range=(1, 2), min_df=2, sublinear_tf=True, preprocessor=zero_digits)
    char = dict(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, preprocessor=zero_digits)
    return {
        "TF-IDF từ + Logistic Regression": make_pipeline(TfidfVectorizer(**word), LogisticRegression(C=10, max_iter=2000, class_weight="balanced")),
        "TF-IDF từ + Naive Bayes": make_pipeline(TfidfVectorizer(**word), ComplementNB(alpha=0.3)),
        "TF-IDF từ + Linear SVM": make_pipeline(TfidfVectorizer(**word), LinearSVC(C=1, class_weight="balanced")),
        "TF-IDF ký tự + Linear SVM": make_pipeline(TfidfVectorizer(**char), LinearSVC(C=1, class_weight="balanced")),
        "Luật + TF-IDF từ + Logistic Regression": make_pipeline(
            make_union(TfidfVectorizer(**word), FunctionTransformer(rule_onehot)),
            LogisticRegression(C=10, max_iter=2000, class_weight="balanced")),
        "Luật v2 + đếm mức giá + TF-IDF từ + Logistic Regression": make_pipeline(
            make_union(TfidfVectorizer(**word), FunctionTransformer(rule_v2_onehot),
                       FunctionTransformer(price_features)),
            LogisticRegression(C=10, max_iter=2000, class_weight="balanced")),
    }


def main():
    lab = pd.read_csv(LABEL_FILE)
    rooms = pd.read_csv(PROCESSED_DIR / "rooms.csv")
    lab = lab[["id", "label", "sample"]].merge(rooms, on="id")
    X_txt, y = text_for_clf(lab), lab["label"]
    rnd = (lab["sample"] == "ngau_nhien").to_numpy()
    y_rnd = y[rnd]
    out = [f"# Phân loại loại tin đăng (R = phòng riêng, G = ở ghép, N = nhiều phòng / khoảng giá)\n",
           f"{len(lab)} tin có nhãn: {y.value_counts().to_dict()}; trong đó {int(rnd.sum())} tin chọn ngẫu nhiên "
           f"(phân bố thật: {y_rnd.value_counts().to_dict()}). Đánh giá: Stratified 5-fold lặp 5 lần trên cả "
           f"{len(lab)} tin; cột \"ngẫu nhiên\" chỉ chấm trên các tin chọn ngẫu nhiên (khách quan).\n"]

    # 1. So sánh phương pháp (dự đoán out-of-fold; luật không cần huấn luyện)
    rows, preds = [], {}
    for name, fn in RULES.items():
        rule = fn(X_txt)
        preds[name] = rule
        rows.append({"phương pháp": name, "macro-F1 (cả 540)": f1_score(y, rule, average="macro"),
                     "macro-F1 (ngẫu nhiên)": f1_score(y_rnd, rule[rnd], average="macro"),
                     "accuracy (ngẫu nhiên)": (rule[rnd] == y_rnd).mean(), "± macro-F1 (ngẫu nhiên)": 0.0})
    splits = list(RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=SEED).split(X_txt, y))
    for name, clf in classifiers().items():
        f1_all, f1_rnd, acc_rnd = [], [], []
        for rep in range(5):
            pred = cross_val_predict(clf, X_txt, y, cv=splits[rep * 5:(rep + 1) * 5])
            f1_all.append(f1_score(y, pred, average="macro"))
            f1_rnd.append(f1_score(y_rnd, pred[rnd], average="macro"))
            acc_rnd.append((pred[rnd] == y_rnd).mean())
            if rep == 0:
                preds[name] = pred
        rows.append({"phương pháp": name, "macro-F1 (cả 540)": np.mean(f1_all), "macro-F1 (ngẫu nhiên)": np.mean(f1_rnd),
                     "accuracy (ngẫu nhiên)": np.mean(acc_rnd), "± macro-F1 (ngẫu nhiên)": np.std(f1_rnd)})
    table = pd.DataFrame(rows).set_index("phương pháp").round(3)
    # Chọn phương pháp ĐƠN GIẢN NHẤT có macro-F1 (ngẫu nhiên) cách điểm cao nhất không quá TOLERANCE:
    # chênh lệch nhỏ hơn mức đó nằm trong dao động giữa các lần chia fold, nên ưu tiên luật (không cần huấn luyện,
    # dễ giải thích, giống cách web dùng) rồi mới đến mô hình học máy theo thứ tự trong bảng.
    TOLERANCE = 0.01
    score = table["macro-F1 (ngẫu nhiên)"]
    near_best = score[score >= score.max() - TOLERANCE]
    simple_first = [n for n in RULES if n in near_best.index] + [n for n in near_best.index if n not in RULES]
    best_name = simple_first[0]
    print(table.to_string(), f"\n-> cao nhất: {score.idxmax()} ({score.max():.3f}); chọn: {best_name} ({score[best_name]:.3f})")
    out.append("## So sánh phương pháp\n\n" + table.to_markdown() +
               f"\n\nCao nhất: {score.idxmax()} ({score.max():.3f}). Chọn phương pháp đơn giản nhất (luật trước, rồi "
               f"đến mô hình học máy) trong khoảng {TOLERANCE} so với điểm cao nhất: **{best_name}** "
               f"({score[best_name]:.3f}). Lưu ý: luật v2 và đặc trưng đếm mức giá được thêm SAU KHI xem lỗi trên mẫu "
               "ngẫu nhiên, nên điểm của chúng trên mẫu này hơi lạc quan.\n")

    for name in ["Luật regex"] + ([best_name] if best_name != "Luật regex" else []):
        pred = preds[name][rnd]
        cm = pd.DataFrame(confusion_matrix(y_rnd, pred, labels=LABELS),
                          index=[f"thật {l}" for l in LABELS], columns=[f"đoán {l}" for l in LABELS])
        out.append(f"## {name} — chấm trên {int(rnd.sum())} tin ngẫu nhiên\n\n"
                   f"```\n{classification_report(y_rnd, pred, labels=LABELS, digits=3)}```\n\n"
                   f"Ma trận nhầm lẫn:\n\n{cm.to_markdown()}\n")

    # 1b. Luật trên mẫu "theo luật" (240 tin) -- luật v2 thiết kế sau khi xem lỗi trên mẫu ngẫu nhiên, nên mẫu này là
    #     phép kiểm tra độc lập hơn cho phần cải tiến v1 -> v2 (dù mẫu được chọn theo luật v1)
    rule_rows = []
    for name, fn in RULES.items():
        pred = fn(X_txt)
        rule_rows.append({"phương pháp": name,
                          "macro-F1 (theo luật)": f1_score(y[~rnd], pred[~rnd], average="macro"),
                          "recall N (theo luật)": (pred[~rnd][y[~rnd] == "N"] == "N").mean(),
                          "macro-F1 (ngẫu nhiên)": f1_score(y_rnd, pred[rnd], average="macro"),
                          "recall N (ngẫu nhiên)": (pred[rnd][y_rnd == "N"] == "N").mean()})
    rule_tab = pd.DataFrame(rule_rows).set_index("phương pháp").round(3)
    print("\n", rule_tab.to_string())
    out.append("## Luật v1 và v2 trên từng mẫu\n\n" + rule_tab.to_markdown() + "\n")

    # 1c. Ảnh hưởng của rà soát nhãn lần 2: chấm cùng các phương pháp trên nhãn cũ (v1) và nhãn đã rà soát
    if LABEL_FILE_V1.exists():
        old = pd.read_csv(LABEL_FILE_V1)[["id", "label"]].rename(columns={"label": "label_v1"})
        y_old = lab[["id"]].merge(old, on="id", how="left")["label_v1"].fillna(y).to_numpy()
        changed = int((y_old != y.to_numpy()).sum())
        rows_v = []
        for name in table.index:
            pred = preds[name]
            rows_v.append({"phương pháp": name,
                           "macro-F1 ngẫu nhiên (nhãn cũ)": f1_score(y_old[rnd], pred[rnd], average="macro"),
                           "macro-F1 ngẫu nhiên (đã rà soát)": f1_score(y_rnd, pred[rnd], average="macro")})
        tab_v = pd.DataFrame(rows_v).set_index("phương pháp").round(3)
        print(f"\n rà soát nhãn: {changed} nhãn đổi\n", tab_v.to_string())
        out.append(f"## Ảnh hưởng của rà soát nhãn lần 2 ({changed}/{len(lab)} nhãn đổi)\n\n"
                   "Cùng dự đoán (lần lặp đầu của CV, mô hình học trên nhãn đã rà soát), chấm trên 300 tin ngẫu nhiên "
                   "với nhãn cũ và nhãn đã rà soát. Phân bố thật trong mẫu ngẫu nhiên trước rà soát: "
                   f"{pd.Series(y_old[rnd]).value_counts().to_dict()}.\n\n" + tab_v.to_markdown() + "\n")

    # 2. Gán nhãn toàn bộ dữ liệu
    clf = RuleClassifier(RULES[best_name]) if best_name in RULES else classifiers()[best_name].fit(X_txt, y)
    rooms["listing_type"] = clf.predict(text_for_clf(rooms))
    rooms[["id", "listing_type"]].to_csv(PROCESSED_DIR / "listing_type.csv", index=False)
    dist = rooms.groupby("listing_type")["price"].agg(["size", "median"])
    dist["median"] = (dist["median"] / 1e6).round(2)
    dist.columns = ["số tin", "giá trung vị (triệu)"]
    dist["% dự đoán"] = (dist["số tin"] / len(rooms) * 100).round(1)
    dist["% thật (mẫu ngẫu nhiên)"] = (y_rnd.value_counts(normalize=True) * 100).round(1)
    print("\n", dist.to_string())
    out.append(f"## Gán nhãn toàn bộ {len(rooms)} tin bằng `{best_name}`\n\n{dist.to_markdown()}\n")

    # 3. Ảnh hưởng tới mô hình giá: test luôn là tin loại R
    df = add_features(rooms)
    y_log, groups = np.log(df["price"]), df["group_id"]
    is_r = (df["listing_type"] == "R").to_numpy()
    res = []
    for train_on in ["tất cả các loại", "chỉ loại R"]:
        rows_ = []
        for tr, te in GroupKFold(n_splits=5).split(df, y_log, groups):
            te = te[is_r[te]]
            if train_on == "chỉ loại R":
                tr = tr[is_r[tr]]
            m = models()["Ridge + TF-IDF"].fit(df[FEATURE_COLS].iloc[tr], y_log.iloc[tr])
            pred, true = np.exp(m.predict(df[FEATURE_COLS].iloc[te])), df["price"].iloc[te]
            rows_.append({"MAE (triệu)": np.mean(np.abs(pred - true)) / 1e6,
                          "MAPE (%)": np.mean(np.abs(pred - true) / true) * 100,
                          "R2": 1 - np.sum((true - pred) ** 2) / np.sum((true - true.mean()) ** 2)})
        res.append({"huấn luyện trên": train_on, "số tin train": int(is_r.sum()) if train_on == "chỉ loại R" else len(df),
                    **pd.DataFrame(rows_).mean().round(3).to_dict()})
    res = pd.DataFrame(res).set_index("huấn luyện trên")
    print("\n", res.to_string())
    out.append("## Ảnh hưởng tới mô hình giá (Ridge + TF-IDF, GroupKFold 5-fold, chỉ chấm trên tin loại R)\n\n"
               + res.to_markdown() + "\n")

    (REPORTS_DIR / "listing_type.md").write_text("\n".join(out), encoding="utf-8")
    print("->", REPORTS_DIR / "listing_type.md")


if __name__ == "__main__":
    main()

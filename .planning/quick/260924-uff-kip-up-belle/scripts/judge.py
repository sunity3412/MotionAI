"""belle 판정지 1장 — 지금 사진 | 후보 사진 + 문장 3줄(지금 / 후보) + ○× 칸."""
import pathlib, textwrap
from PIL import Image, ImageDraw, ImageFont
H = pathlib.Path(__file__).parent
Q = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion/.planning/quick")
now = Image.open(Q / "260924-ig3-window-constant/kipup_fault_zoom_card_ig3.png").convert("RGB")
cand = Image.open(H / "cand_a.png").convert("RGB")
F = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
f_title = ImageFont.truetype(F, 34, index=6); f_h = ImageFont.truetype(F, 24, index=6); f_b = ImageFont.truetype(F, 23, index=0)
f_s = ImageFont.truetype(F, 20, index=0)
W = 1600; M = 36
BR = (255, 75, 51); GREY = (110, 110, 110); LINE = (225, 225, 225)
rows = [
    ("제목 (무엇이)", "왼쪽 어깨(겨드랑이) 각도가 킵업 기준 자세와 차이가 있어요",
     "돌기 시작해서 끝날 때까지 몸이 정은지 선수보다 낮게 떠 있어요"),
    ("설명 (왜)", "어깨가 처지거나 으쓱 올라가면 스윙 추진력이 새는 부분이에요",
     "손 높이는 같은데 몸이 손 아래로 처졌고, 왼팔이 몸통에서 더 벌어져 있어요"),
    ("교정 (어떻게)", "목표는 무릎을 편 채 양다리를 좌우로 크게 벌려 반동을 만드는 거예요. 어깨를 귀에서 멀리 눌러 고정한 채, 팔과 몸통 사이 각을 기준 자세에 겹쳐 맞춰보세요",
     "왼팔을 굽혀 옆구리에 붙인 채 돌아보세요"),
]
def wrap(d, text, font, width):
    out, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=font) > width:
            out.append(cur); cur = ch
        else:
            cur += ch
    if cur: out.append(cur)
    return out
# 사진 줄
nw = 520; now_s = now.resize((nw, round(now.height * nw / now.width)))
cw = W - 2 * M - nw - 30; cand_s = cand.resize((cw, round(cand.height * cw / cand.width)))
tmp = Image.new("RGB", (W, 10)); td = ImageDraw.Draw(tmp)
colw = [220, 560, 560, 120]
row_h = []
for _, a, b in rows:
    la = wrap(td, a, f_b, colw[1] - 24); lb = wrap(td, b, f_b, colw[2] - 24)
    row_h.append(max(len(la), len(lb)) * 34 + 30)
photo_h = max(now_s.height, cand_s.height)
Ht = M + 50 + 40 + photo_h + 40 + 50 + sum(row_h) + 30 + 90 + M
img = Image.new("RGB", (W, Ht), "white"); d = ImageDraw.Draw(img)
y = M
d.text((M, y), "킵업 실수 카드 — 후보 (앱에는 아직 안 걸었어요)", fill="black", font=f_title); y += 60
d.text((M, y), "지금 앱 사진", fill=GREY, font=f_h); d.text((M + nw + 30, y), "후보 사진 — 발·왼팔 동그라미, 각도 선 없음", fill=BR, font=f_h); y += 36
img.paste(now_s, (M, y)); img.paste(cand_s, (M + nw + 30, y))
d.rectangle([M + nw + 30 - 3, y - 3, M + nw + 30 + cw + 2, y + cand_s.height + 2], outline=BR, width=3)
# ○× 칸 (사진)
y += photo_h + 14
d.text((M + nw + 30, y), "사진   ○  ×      (동그라미 친 팔 = 폴 아래쪽을 잡은 팔이 말씀하신 왼팔 맞나요?)", fill="black", font=f_b); y += 50
# 표
x = M; heads = ("자리", "지금 앱", "후보", "○ / ×")
for i, h in enumerate(heads):
    d.text((x + 12, y), h, fill=(BR if i == 2 else GREY), font=f_h); x += colw[i]
y += 40; d.line([M, y, W - M, y], fill=LINE, width=2)
for (slot, a, b), rh in zip(rows, row_h):
    x = M + 12
    d.text((x, y + 14), slot, fill="black", font=f_h)
    for k, line in enumerate(wrap(d, a, f_b, colw[1] - 24)):
        d.text((M + colw[0] + 12, y + 14 + k * 34), line, fill=GREY, font=f_b)
    for k, line in enumerate(wrap(d, b, f_b, colw[2] - 24)):
        d.text((M + colw[0] + colw[1] + 12, y + 14 + k * 34), line, fill="black", font=f_b)
    d.text((M + colw[0] + colw[1] + colw[2] + 16, y + 14), "○  ×", fill="black", font=f_h)
    y += rh; d.line([M, y, W - M, y], fill=LINE, width=2)
y += 22
note = ["· 팔꿈치 굽힘은 정은지와 같게 재져서(60도 vs 59도) '팔꿈치'라고 쓰지 않았어요. 다른 건 왼팔이 몸통에서 벌어진 정도(겨드랑이 +34도)예요.",
        "· 사진 순간은 운영 짝이 고른 두 장이고, 높이 차가 영상 전체 차이와 같은 순간이에요(가장 큰 순간이 아님). 교정 문장은 동작 코칭이라 belle 말로 바꾸셔도 돼요."]
for t in note:
    d.text((M, y), t, fill=GREY, font=f_s); y += 32
img.save(Q / "260924-uff-kip-up-belle" / "judge_kipup_card.png")
print(img.size)

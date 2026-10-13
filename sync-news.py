# -*- coding: utf-8 -*-
"""AI资讯页数据烘焙 —— 拉取 codex-reset.com 公开接口，重写 news.html 的动态区块。

双链路分工（与商品价格同步同款思路）：
  前端：news.html 加载时浏览器直连 codex-reset.com 实时刷新（其接口 CORS 全开，实测
        Access-Control-Allow-Origin: *）；任何一步失败静默保留构建时快照。
  本脚本：负责「构建时快照」—— 前端拿不到数据（离线 / 被墙 / 接口抖动）时的兜底内容。
        任何接口失败 → 整体放弃、不写文件（宁可不更新，也不写半截）。

数据接口（全部为 codex-reset.com 公开接口，页面按 CC BY 4.0 注明来源复用）：
  /api/status    当前 OpenAI 服务状态（降级 / 事故）
  /api/timeline  重置事件账本（含 confirmed 确认标记 / banked 储备重置标记）
  /api/forecast  参考概率与高发窗口（实验性模型，非官方承诺）
  /api/feed      Tibo 推文流（含 reset_related 车道分类）

用法：
  python sync-news.py          # 抓取并写回 news.html（只动 4 个标记区块）
  python sync-news.py --check  # 只报告是否有变化，不写文件
"""
import io
import json
import re
import sys
import html as H
import urllib.request
from datetime import datetime, timezone, timedelta

BASE = "https://codex-reset.com"
PAGE = "news.html"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json",
}
BJ = timezone(timedelta(hours=8))


def get(path):
    req = urllib.request.Request(BASE + path, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def bj_time(iso):
    """ISO 时间 → 「今天 HH:MM」/「MM-DD HH:MM」（北京时间）"""
    if not iso:
        return "—"
    d = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(BJ)
    now = datetime.now(BJ)
    same = d.date() == now.date()
    return ("今天 " if same else d.strftime("%m-%d ")) + d.strftime("%H:%M")


def esc(s):
    return H.escape(str(s), quote=True)


def status_label(desc, indicator):
    if not desc:
        return "未知"
    if "Operational" in desc:
        return "运行正常"
    return {"minor": "部分降级", "major": "重大故障", "critical": "严重故障"}.get(indicator, desc)


# ── 三个区块的渲染（与 news.html 前端 JS 的同名渲染保持同构）─────────
def render_stat(st, fc, tl):
    cards = []
    conf = next((e for e in tl.get("events", [])
                 if e.get("confirmed") and e.get("type") == "reset"), None)
    if conf:
        cards.append(("最近一次全局重置", bj_time(conf.get("announced_at")),
                      "北京时间 · 已确认（归档）"))
    else:
        cards.append(("最近一次全局重置", "—", "归档中暂无已确认记录"))
    probs = fc.get("probabilities") or {}
    cards.append(("下一次重置 · 参考概率",
                  "24h %s%% · 48h %s%%" % (probs.get("model_24h", "—"), probs.get("model_48h", "—")),
                  "实验性统计模型 · 非官方承诺"))
    tw = fc.get("time_window")
    if tw:
        s, e = tw.get("start_hour"), tw.get("end_hour")
        cad = fc.get("cadence") or {}
        sub = "北京时间（UTC %s–%s 时）" % (s, e)
        if cad:
            sub += " · 近 %s 次中位间隔 %s 天" % (cad.get("recent_sample"), cad.get("recent_median_days"))
        cards.append(("重置高发窗口", "%02d:00–%02d:00" % ((s + 8) % 24, (e + 8) % 24), sub))
    inc = st.get("active_incident")
    cards.append(("OpenAI 服务状态", status_label(st.get("description"), st.get("indicator")),
                  ("%s · 已持续 %s 小时" % (inc.get("name"), inc.get("hours"))) if inc
                  else "All Systems Operational"))
    return "\n".join(
        '        <div class="nsc glass glow"><div class="nsc-lab">%s</div>'
        '<div class="nsc-val">%s</div><div class="nsc-sub">%s</div></div>'
        % (esc(a), esc(b), esc(c)) for a, b, c in cards)


def render_hist(tl):
    seen, rows = set(), []
    for e in tl.get("events", []):
        if not e.get("confirmed"):
            continue
        k = (e.get("date"), bool(e.get("banked_grant")))
        if k in seen:
            continue
        seen.add(k)
        rows.append(e)
    rows = rows[:10]
    out = []
    for e in rows:
        tag = ('<span class="nh-tag banked">储备重置发放</span>' if e.get("banked_grant")
               else '<span class="nh-tag">全局重置</span>')
        out.append(
            '        <div class="nh-row glass"><div class="nh-top">'
            '<span class="nh-date">%s</span>%s<span class="nh-ok">已确认</span>'
            '<a class="nh-link" href="%s" target="_blank" rel="noopener">原帖 ↗</a></div>'
            '<div class="nh-sum">%s</div></div>'
            % (esc((e.get("date") or "")[5:]), tag, esc(e.get("url", "")), esc(e.get("summary", ""))))
    return "\n".join(out)


def render_feed(fd):
    tw = [t for t in fd.get("tweets", []) if t.get("tibo_lane") == "reset_related"][:6]
    out = []
    for t in tw:
        likes = t.get("likes")
        heat = ("{:,} 赞".format(likes)) if isinstance(likes, int) else ""
        text = re.sub(r"\s*\n\s*", " ", str(t.get("text", "")))
        out.append(
            '        <div class="nf-item glass"><div class="nf-head">'
            '<span class="nf-time">%s · 北京时间</span><span class="nf-heat">%s</span>'
            '<a class="nh-link" href="%s" target="_blank" rel="noopener">原帖 ↗</a></div>'
            '<div class="nf-text">%s</div></div>'
            % (esc(bj_time(t.get("at"))), esc(heat), esc(t.get("url", "")), esc(text)))
    return "\n".join(out)


def replace_region(html, name, inner):
    pat = re.compile(r"(<!-- " + name + r":START -->).*?(<!-- " + name + r":END -->)", re.S)
    if not pat.search(html):
        raise SystemExit("news.html 里找不到标记区块：%s" % name)
    return pat.sub(lambda m: m.group(1) + "\n" + inner + "\n" + m.group(2), html, count=1)


def main():
    check = "--check" in sys.argv
    try:
        st = get("/api/status")
        tl = get("/api/timeline")
        fc = get("/api/forecast")
        fd = get("/api/feed")
    except Exception as e:  # noqa: BLE001 —— 任何一步失败都不写入，避免半截内容
        print("抓取失败，放弃本次同步：%r" % e)
        return 1

    now = datetime.now(BJ).strftime("%Y-%m-%d %H:%M")
    html = io.open(PAGE, encoding="utf-8").read()
    out = html
    out = replace_region(out, "NSTAMP", "构建快照：" + now + "（北京时间）")
    out = replace_region(out, "NSTAT", render_stat(st, fc, tl))
    out = replace_region(out, "NHIST", render_hist(tl))
    out = replace_region(out, "NFEED", render_feed(fd))

    n_conf = len([e for e in tl.get("events", []) if e.get("confirmed")])
    n_tw = len([t for t in fd.get("tweets", []) if t.get("tibo_lane") == "reset_related"])
    print("接口：status=%s · timeline=%d 事件(%d 已确认) · forecast 24h=%s%% · feed=%d 条"
          % (status_label(st.get("description"), st.get("indicator")),
             len(tl.get("events", [])), n_conf,
             (fc.get("probabilities") or {}).get("model_24h"), n_tw))

    if check:
        print("有变化，需要写盘" if out != html else "无变化")
        return 0
    if out != html:
        io.open(PAGE, "w", encoding="utf-8").write(out)
        print("已更新 news.html · 构建快照 %s" % now)
    else:
        print("内容无变化，未写盘")
    return 0


if __name__ == "__main__":
    sys.exit(main())

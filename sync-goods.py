"""同步两个店铺的在售商品到 index.html。

把 GOODS:START / GOODS:END 标记之间的区块按店铺接口的实时数据重新生成。
无变化时不写文件、不产生提交。

用法：
    python sync-goods.py            # 同步并写回 index.html
    python sync-goods.py --check    # 只检查，不写文件（有变化则退出码 1）

接口说明：
    链动小铺 wzyp.cn  —— POST /shopApi/Shop/goodsList   {"token","current","pageSize","goods_type"}
    16688           —— POST /shopApi/goods/list         {"shop_no","page","page_size"}
"""
import json
import re
import sys
import time
import urllib.request
from urllib.parse import urlsplit
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX = HERE / 'index.html'
START = '<!-- GOODS:START'
END = '<!-- GOODS:END -->'

WZYP_TOKEN = 'SEFBJWNM'
SHOP_16688 = 'S599099'

# 人工整理过的展示名与副标题（接口返回的原始名带营销 emoji 与长尾参数，不适合直接上屏）
# 新商品不在表里时走 clean_name() 兜底，等人工补齐这条即可
CURATED = {
    # 链动小铺
    'z7n6ts': ('Plus 官方卡冲 1 个月', '质保订阅 · 官方卡冲'),
    'loqcbj': ('Pro Standard（原 5X）官方卡冲 1 个月', '质保订阅 · 官方卡冲'),
    '2smf8k': ('Pro More（原 20X）官方卡冲 1 个月', '质保订阅 · 官方卡冲'),
    'oes7j0': ('Pro Max（25X）官方卡冲 1 个月', '质保订阅 · 顶级订阅档'),
    'b2seen': ('Codex 短效接码 · 5 秒极速换号', '不限次数 · 全自动系统'),
    'm70j2l': ('Codex 接码 · 长效 20-30 天', '美国实卡 · 可复绑'),
    '4n3idp': ('Codex CDK · 短效单次', '美国实卡 · 支持 API 对接'),
    'b1wb4x': ('Codex CDK · 10 次接码', '美国实卡 · 支持 API 对接'),
    '1tyvn1': ('Codex CDK · 50 次接码', '美国实卡 · 支持 API 对接'),
    'kqr3kd': ('Claude 接码 · 2-9 天', '美国实卡 · 可二次'),
    'hheojo': ('Claude 接码 · 10-20 天', '美国实卡 · 可二次'),
    'vqkl45': ('Claude 接码 · 21-30 天', '美国长效实卡 · 可二次'),
    # 16688
    'G64512440': ('GPT Plus 官方充值月卡', '直冲个人账号 · 质保 30 天'),
}


UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36')


def http_post(url, payload, timeout=30, tries=4):
    """带退避重试的 POST。

    请求头刻意伪装成普通浏览器：链动小铺前置了阿里云 ESA 风控，
    只带一个自造 UA 时会被返回「HTTP 200 + 空响应体」，JSON 解析随之失败。
    """
    body = json.dumps(payload).encode()
    origin = '{u.scheme}://{u.netloc}'.format(u=urlsplit(url))
    last = None
    for i in range(tries):
        req = urllib.request.Request(url, method='POST')
        req.add_header('Content-Type', 'application/json;charset=UTF-8')
        req.add_header('User-Agent', UA)
        req.add_header('Accept', 'application/json, text/plain, */*')
        req.add_header('Accept-Language', 'zh-CN,zh;q=0.9,en;q=0.8')
        req.add_header('Origin', origin)
        req.add_header('Referer', origin + '/')
        try:
            with urllib.request.urlopen(req, body, timeout=timeout) as r:
                raw = r.read()
                if not raw.strip():
                    raise ValueError('响应体为空（疑似被风控拦截，HTTP %s）' % r.status)
                return json.loads(raw.decode('utf-8', 'replace'))
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(2 * (i + 1))
    raise RuntimeError('请求失败 %s：%s' % (url, last))


def fmt_price(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f == int(f):
        return str(int(f))
    return ('%.2f' % f).rstrip('0').rstrip('.')


def clean_name(raw):
    """接口原始名的兜底清洗：去营销 emoji、去【】标注、吞掉多余分隔符。"""
    s = re.sub(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]', '', raw or '')
    s = re.sub(r'【[^】]*】', '', s)
    s = re.sub(r'-{2,}', ' · ', s)
    s = re.sub(r'\s+', ' ', s).strip(' -·')
    return s[:36] or (raw or '未命名商品')


def rank_of(name):
    """归类排序：订阅代充 → Codex → Claude。"""
    n = (name or '').lower()
    if 'claude' in n:
        return 3
    if 'codex' in n or 'cdk' in n:
        return 2
    return 1


def fetch_wzyp():
    d = http_post('https://wzyp.cn/shopApi/Shop/goodsList',
                  {'token': WZYP_TOKEN, 'current': 1, 'pageSize': 100, 'goods_type': 'card'})
    if d.get('code') != 1:
        raise RuntimeError('链动小铺接口返回异常：%s' % str(d)[:200])
    out = []
    for it in d['data']['list']:
        key = str(it.get('goods_key') or '').strip()
        if not key:
            continue
        out.append({
            'key': key,
            'raw_name': it.get('name') or '',
            'price': it.get('price'),
            'link': it.get('link') or ('https://wzyp.cn/item/' + key),
            'shop': '链动小铺',
            'shop_cls': 'gold',
            'shop_id': 'wzyp',
        })
    return out


def fetch_16688():
    d = http_post('https://www.16688.com.cn/shopApi/goods/list',
                  {'shop_no': SHOP_16688})
    if d.get('code') != 1:
        raise RuntimeError('16688 接口返回异常：%s' % str(d)[:200])
    out = []
    for it in d['data'].get('list', []):
        no = str(it.get('goods_no') or '').strip()
        if not no:
            continue
        out.append({
            'key': no,
            'raw_name': it.get('name') or '',
            'price': it.get('price'),
            'link': 'https://www.16688.com.cn/goods/' + no,
            'shop': '16688',
            'shop_cls': 'green',
            'shop_id': '16688',
        })
    return out


ARROW = ('<svg class="g-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
         '<path d="M7 17 17 7M9 7h8v8"/></svg>')


def render(items):
    blocks = []
    for it in items:
        name, meta = CURATED.get(it['key']) or (clean_name(it['raw_name']), '以商品页说明为准')
        blocks.append(
            '        <a class="g-item reveal" data-key="{key}" data-shop="{sid}" href="{link}" target="_blank" rel="noopener">\n'
            '          <span class="g-top"><span class="g-shop {cls}">{shop}</span>'
            '<span class="g-price">¥{price}</span></span>\n'
            '          <span class="g-name">{name}</span>\n'
            '          <span class="g-foot"><span class="g-meta">{meta}</span>\n'
            '            {arrow}\n'
            '          </span>\n'
            '        </a>'.format(key=it['key'], sid=it['shop_id'], link=it['link'],
                               cls=it['shop_cls'], shop=it['shop'],
                               price=fmt_price(it['price']),
                               name=escape(name), meta=escape(meta), arrow=ARROW))
    return '\n'.join(blocks)


def escape(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def build_block(items, stamp):
    n = len(items)
    return (
        '{start} —— 本区块由 sync-goods.py 自动生成，请勿手工修改区块内部 -->\n'
        '      <div class="goods-head reveal">\n'
        '        <span class="goods-count" id="goodsCount">共 {n} 件在售</span>\n'
        '        <span class="goods-hint" id="goodsHint">价格为 {stamp} 抓取的快照，实时价格与库存请以商品页显示为准</span>\n'
        '      </div>\n\n'
        '      <div class="goods" id="goodsGrid">\n'
        '{cards}\n'
        '      </div>\n'
        '      {end}'.format(start=START, n=n, stamp=stamp, cards=render(items), end=END)
    )


def main():
    check_only = '--check' in sys.argv

    html = INDEX.read_text(encoding='utf-8')
    if START not in html or END not in html:
        raise SystemExit('× index.html 里找不到 GOODS:START / GOODS:END 标记')

    items = fetch_wzyp() + fetch_16688()
    # 只保留表格里已整理的顺序感：先按归类，再按价格
    items.sort(key=lambda x: (rank_of(CURATED.get(x['key'], (x['raw_name'],))[0]), float(x['price'] or 0)))

    stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    block = build_block(items, stamp)

    head, rest = html.split(START, 1)
    _, tail = rest.split(END, 1)
    new_html = head.rstrip() + '\n      ' + block + tail

    changed = new_html != html
    n_wzyp = sum(1 for i in items if i['shop'] == '链动小铺')
    print('抓取到 %d 件商品（链动小铺 %d 件 / 16688 %d 件）'
          % (len(items), n_wzyp, len(items) - n_wzyp))
    for it in items:
        print('  %-9s ¥%-9s %s' % (it['shop'], fmt_price(it['price']),
                                   CURATED.get(it['key'], (clean_name(it['raw_name']),))[0]))

    if not changed:
        print('\n无变化，未修改 index.html')
        return 0
    if check_only:
        print('\n检测到变化（--check 模式，未写入）')
        return 1

    INDEX.write_text(new_html, encoding='utf-8')
    print('\n已更新 index.html')
    return 0


if __name__ == '__main__':
    sys.exit(main())

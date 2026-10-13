# HELIX-AI 渠道站

HELIX AI STUDIO 的店铺渠道引导页 —— 一个单文件、零外部依赖的静态站点。

## 这是什么

引导访客进入 HELIX-AI 的两个 AI 服务店铺并完成购买，本页不直接销售商品、不参与收款与发货。

| 店铺 | 链接 | 定位 |
|---|---|---|
| 链动小铺 · HELIX-AI 源头分销店 | https://wzyp.cn/shop/SEFBJWNM | 主店，品类全，源头分销价 |
| 16688 店铺 | https://www.16688.com.cn/shop/S599099 | 平台担保交易，适合首次购买 |

售后 QQ 群：**1127472110**
售后时间：10:00–13:00 / 13:30–18:30 / 20:00–23:00（北京时间）

## 技术说明

整站就是根目录的 `index.html` 一个文件：

- **零外部依赖** —— 没有 CDN、没有外部字体、没有图片外链；头像以 base64 内联在 CSS 变量 `--avatar` 里。断网也能完整打开。
- **可直接部署** —— 丢进任意静态托管（GitHub Pages / Netlify / 对象存储）就能跑，无需构建步骤。
- **深色视觉体系** —— 近黑底 `#0b0c0d` + 金属金渐变，参考 higgsfield.ai 的配色语言。

### 想改内容时

| 改什么 | 改哪里 |
|---|---|
| 换头像 | `:root` 里的 `--avatar` 一行（全站 6 处复用同一变量） |
| 改配色 | `:root` 的颜色变量；**金色文字必须用 `--gold-text`**，不要复用按钮的 `--gold-grad`（后者含暗端，用在小字号上会发浑） |
| 改商品清单 | 搜 `id="goods"` 区块，每个商品是一个 `<a class="g-item">`，改文案和 `href` 即可 |
| 改粒子效果 | 搜 `fx-particles`，粒子密度、透明度、连线强度都在该段 JS 里 |

### 商品价格是快照

页面上的商品与价格来自店铺接口抓取（最近一次：2026-10-13）。**商品上下架或调价后需要手动同步**，否则会与实际不符。

抓取接口（实测可用）：

```bash
# 链动小铺
curl -X POST https://wzyp.cn/shopApi/Shop/goodsList \
  -H "Content-Type: application/json" \
  -d '{"token":"SEFBJWNM","current":1,"pageSize":50,"goods_type":"card"}'

# 16688
curl -X POST https://www.16688.com.cn/shopApi/goods/list \
  -H "Content-Type: application/json" \
  -d '{"shop_no":"S599099","page":1,"page_size":100}'
```

## 免责

本站为店铺导航页，不直接销售任何商品，不参与收款与发货。所有交易、发货与售后均在对应的第三方店铺平台完成，请以店铺页面展示的实时价格、库存与规则为准。商品仅限正当合规用途。

---

© 2026 HELIX AI STUDIO

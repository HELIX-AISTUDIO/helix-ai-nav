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

### 商品价格自动同步

商品区（`id="goods"`）**不需要手动维护**，有两条自动链路：

**① 定时同步（主力，覆盖两个店铺）**

`.github/workflows/sync-goods.yml` 每 6 小时跑一次 `sync-goods.py`：抓两个店铺的在售商品与价格 →
重新生成 `index.html` 里 `GOODS:START` / `GOODS:END` 之间的区块 → 有变化才提交 → Pages 自动重新发布。

- 商品上下架、调价、新增都会自动跟上，最多滞后 6 小时
- 抓取失败时脚本报错退出，**不会写入半成品**，线上保持上一次的正确状态
- 想立刻同步：仓库 Actions 页面 → 「同步店铺商品」→ Run workflow

**② 前端实时同步（增强，只覆盖链动小铺）**

页面加载时会用浏览器直接拉链动小铺的接口，把价格刷新到最新，并标注已下架商品。
任何一步失败都静默跳过，页面保留①生成的快照，不会白屏或报错。

- 链动小铺接口对任意来源开放 CORS，所以前端拿得到
- 16688 只放行自身域名，浏览器拿不到 → 该店完全依赖①
- 同步成功时商品区左上角徽标会变绿并显示同步时间，一眼可辨

> 注：链动小铺前置了阿里云 ESA 风控，会拦截 `HeadlessChrome` 等无头 UA。
> 正常浏览器不受影响；用无头浏览器做验证时需要覆盖成普通 UA。

### 想手工改内容时

| 改什么 | 改哪里 |
|---|---|
| 换头像 | `:root` 里的 `--avatar` 一行（全站 6 处复用同一变量） |
| 改配色 | `:root` 的颜色变量；**金色文字必须用 `--gold-text`**，不要复用按钮的 `--gold-grad`（后者含暗端，用在小字号上会发浑） |
| 改商品**展示名** | `sync-goods.py` 里的 `CURATED` 表，按 goods_key 补一行即可（接口原始名带营销 emoji，不适合直接上屏） |
| 改商品区块结构 | 改 `sync-goods.py` 的 `render()`；**不要手改 `GOODS:START/END` 之间的 HTML**，下次同步会被覆盖 |
| 改粒子效果 | 搜 `fx-particles`，粒子密度、透明度、连线强度都在该段 JS 里 |

### 店铺接口（实测可用）

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

两个店铺都是 Vue SPA，页面 HTML 是空壳，取数据只能走接口。

## 免责

本站为店铺导航页，不直接销售任何商品，不参与收款与发货。所有交易、发货与售后均在对应的第三方店铺平台完成，请以店铺页面展示的实时价格、库存与规则为准。商品仅限正当合规用途。

---

© 2026 HELIX AI STUDIO

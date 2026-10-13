# HELIX-AI 渠道站

HELIX AI STUDIO 的店铺渠道引导页 + AI资讯页 —— 两个页面、零外部依赖的静态站点。

## 这是什么

引导访客进入 HELIX-AI 的两个 AI 服务店铺并完成购买，本页不直接销售商品、不参与收款与发货。

| 店铺 | 链接 | 定位 |
|---|---|---|
| 链动小铺 · HELIX-AI 源头分销店 | https://wzyp.cn/shop/SEFBJWNM | 主店，品类全，源头分销价 |
| 16688 店铺 | https://www.16688.com.cn/shop/S599099 | 平台担保交易，适合首次购买 |

售后 QQ 群：**1127472110**
售后时间：10:00–13:00 / 13:30–18:30 / 20:00–23:00（北京时间）

## 技术说明

整站由两个页面组成（构建产物本身零外部依赖，唯一例外是 AI资讯页的**实时数据刷新**——可降级，见下）：

| 页面 | 作用 |
|---|---|
| `index.html` | 渠道引导页：主营产品 / 在售商品 / 两个店铺入口 / 购买流程 / 售后支持 |
| `news.html` | AI资讯页「Codex 重置雷达」：重置动态 / 参考概率 / Tibo 动态 / OpenAI 服务状态 |

- **零外部依赖** —— 没有 CDN、没有外部字体、没有图片外链；头像以 base64 内联在 CSS 变量 `--avatar` 里。断网也能完整打开（AI资讯页显示构建时快照）。
- **可直接部署** —— 丢进任意静态托管（GitHub Pages / Netlify / 对象存储）就能跑，无需构建步骤。
- **深色视觉体系** —— 近黑底 `#0b0c0d` + 金属金渐变，参考 higgsfield.ai 的配色语言。

### 商品价格自动同步

商品区（`id="goods"`）**不需要手工维护**。因为两个平台的跨域与风控策略完全不同，
这里用了两条互补的链路，各自负责对方覆盖不了的那一半：

| | 链动小铺 | 16688 |
|---|---|---|
| 浏览器跨域直连 | ✅ 放行任意来源 | ❌ 只放行自身域名 |
| GitHub 出网 IP 抓取 | ❌ 被阿里云 ESA 拦（返回 HTML 挑战页） | ✅ 正常返回 JSON |
| **由谁负责** | **页面内前端同步** | **GitHub Actions 定时任务** |

**① 前端实时同步（链动小铺）**

页面加载时用浏览器直连接口（`https://wzyp.cn/shopApi/Shop/goodsList`），刷新价格、
把已下架商品降权并解除跳转、把新上架商品追加进列表。同步成功时商品区左上角徽标变绿并显示同步时间。

任何一步失败都静默跳过，页面保留构建时快照，不会白屏或报错。

**② 定时同步（覆盖 16688，并为链动小铺兜底）**

`.github/workflows/sync-goods.yml` 每 6 小时跑一次 `sync-goods.py`：抓两个店铺 →
重新生成 `GOODS:START` / `GOODS:END` 之间的区块 → 有变化才提交 → Pages 自动重新发布。

- 单个店铺抓取失败时**沿用页面里的旧快照**，不会把它那一片商品删掉，也不会让整个任务失败
- 两个店铺都拿不到数据时才会报错退出，此时不写入任何内容
- 想立刻同步：仓库 Actions 页面 →「同步店铺商品」→ Run workflow

**③ 本地手动同步（随时可用）**

```bash
python sync-goods.py          # 抓取并写回 index.html
python sync-goods.py --check  # 只检查有没有变化，不写文件
```

本机在国内，两个店铺都抓得到，所以想立刻同步 16688 时直接跑这条最快。

> **踩过的坑**：链动小铺前置了阿里云 ESA 风控。它会（a）拦截 `HeadlessChrome` 等无头 UA、
> （b）把境外机房 IP（含 GitHub Actions）的请求改成返回 HTML 挑战页、
> （c）对完全没有 UA 的请求直接 403。所以用无头浏览器验证时要覆盖成普通 UA，
> 而 CI 抓不到它是正常现象，不是 bug。

### AI资讯页数据同步（news.html）

AI资讯页展示的 Codex 重置动态来自 [codex-reset.com](https://codex-reset.com/zh/) 的四个公开接口
（`/api/status` `/api/timeline` `/api/forecast` `/api/feed`），接口放行任意来源跨域，页面按 **CC BY 4.0** 注明来源复用。

同样是两条互补链路：

| | 说明 |
|---|---|
| **页面内前端同步** | 加载时浏览器直连上述接口实时刷新；任何一步失败静默保留构建时快照 |
| **本地手动烘焙** | `python sync-news.py` 抓取接口 → 重写 `news.html` 里四个标记区块 |

- 构建时快照同时是「前端拿不到数据」时的兜底内容；四个接口任一失败，脚本整体放弃、不写文件
- 想立刻刷新快照：跑 `python sync-news.py`（本机在国内可直接访问 codex-reset.com）
- 不要手改 `NSTAMP / NSTAT / NHIST / NFEED` 四个 `:START/:END` 标记之间的 HTML，下次烘焙会被覆盖

> **注意**：codex-reset.com 站点设了 `X-Frame-Options: DENY`，**不能 iframe 嵌入**，只能像现在这样取数据自渲染。

### 想手工改内容时

| 改什么 | 改哪里 |
|---|---|
| 换头像 | `:root` 里的 `--avatar` 一行（全站 6 处复用同一变量） |
| 改配色 | `:root` 的颜色变量；**金色文字必须用 `--gold-text`**，不要复用按钮的 `--gold-grad`（后者含暗端，用在小字号上会发浑） |
| 改商品**展示名** | `sync-goods.py` 里的 `CURATED` 表，按 goods_key 补一行即可（接口原始名带营销 emoji，不适合直接上屏） |
| 改商品区块结构 | 改 `sync-goods.py` 的 `render()`；**不要手改 `GOODS:START/END` 之间的 HTML**，下次同步会被覆盖 |
| 改资讯页**动态数据** | 跑 `python sync-news.py`（或靠页面加载时的前端自动刷新）；四个标记区块不要手改 |
| 改资讯页**文案 / 版式** | 直接改 `news.html`（标记区块之外的部分）；页头、页脚、粒子与 index.html 同款 |
| 改粒子效果 | 搜 `fx-particles`，粒子密度、透明度、连线强度都在该段 JS 里（两个页面各有一份） |

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

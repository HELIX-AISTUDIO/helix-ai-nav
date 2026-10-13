"""把 HELIX-AI 渠道站发布到 GitHub Pages。

做四件事：建仓库 → 推送 → 开启 Pages → 打印访问地址。
凭据从本机 git 凭据管理器读取，不落盘、不打印明文。

用法：
    python 部署到GitHub.py
或直接双击同目录的「部署到GitHub.cmd」。
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OWNER = 'HELIX-AISTUDIO'
REPO = 'helix-ai-nav'
SITE_DIR = Path(__file__).resolve().parent
API = 'https://api.github.com'


def echo(msg):
    print(msg, flush=True)


def get_token():
    """从本机 git 凭据管理器取 GitHub token。"""
    p = subprocess.run(['git', 'credential', 'fill'],
                       input='protocol=https\nhost=github.com\n\n',
                       capture_output=True, text=True, timeout=25)
    for line in p.stdout.splitlines():
        if line.startswith('password='):
            return line.split('=', 1)[1].strip()
    raise SystemExit('× 没能从本机取到 GitHub 凭据，请先在本机登录 GitHub。')


def api(token, path, method='GET', body=None, tries=4):
    last = None
    for i in range(tries):
        req = urllib.request.Request(API + path, method=method)
        req.add_header('Authorization', 'token ' + token)
        req.add_header('Accept', 'application/vnd.github+json')
        req.add_header('User-Agent', 'helix-nav-deploy')
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req, data, timeout=30) as r:
                txt = r.read().decode()
                return r.status, (json.loads(txt) if txt else {})
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or '{}')
        except Exception as e:                      # 网络抖动，退避重试
            last = e
            time.sleep(1.5 * (i + 1))
    return 0, {'error': str(last)}


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=SITE_DIR, capture_output=True, text=True, **kw)


def main():
    echo('=' * 56)
    echo('  HELIX-AI 渠道站 → GitHub Pages 发布')
    echo('=' * 56)

    if not (SITE_DIR / 'index.html').exists():
        raise SystemExit('× 当前目录下找不到 index.html')

    echo('\n[1/5] 读取本机 GitHub 凭据…')
    token = get_token()
    st, me = api(token, '/user')
    if st != 200:
        raise SystemExit('× 凭据无效或网络不通：HTTP %s %s' % (st, str(me)[:200]))
    echo('   已登录：%s（%s）' % (me.get('login'), me.get('name')))
    if me.get('login', '').upper() != OWNER.upper():
        raise SystemExit('× 当前登录的是 %s，不是 %s，已停止以免推错账号。'
                         % (me.get('login'), OWNER))

    echo('\n[2/5] 检查 / 创建仓库 %s/%s…' % (OWNER, REPO))
    st, d = api(token, '/repos/%s/%s' % (OWNER, REPO))
    if st == 200:
        echo('   仓库已存在，直接使用。')
        repo_url = d['clone_url']
    elif st == 404:
        st2, d2 = api(token, '/user/repos', 'POST', {
            'name': REPO,
            'description': 'HELIX-AI 渠道站 · AI 服务店铺引导页（单文件静态站）',
            'homepage': '',
            'private': False,
            'has_issues': True,
            'has_wiki': False,
            'has_projects': False,
        })
        if st2 not in (200, 201):
            raise SystemExit('× 建仓库失败：HTTP %s %s' % (st2, str(d2)[:300]))
        echo('   已新建仓库。')
        repo_url = d2['clone_url']
    else:
        raise SystemExit('× 查询仓库失败：HTTP %s %s' % (st, str(d)[:300]))

    echo('\n[3/5] 提交并推送…')
    if not (SITE_DIR / '.git').exists():
        run(['git', 'init', '-b', 'main'])
    run(['git', 'add', '-A'])
    msg = 'feat: HELIX-AI 渠道站（深色金属金 · 粒子背景 · 商品直达）'
    c = run(['git', 'commit', '-m', msg])
    if c.returncode != 0 and 'nothing to commit' not in (c.stdout + c.stderr):
        echo('   （没有新变更，继续推送已有提交）')
    r = run(['git', 'remote', 'get-url', 'origin'])
    if r.returncode != 0:
        run(['git', 'remote', 'add', 'origin', repo_url])
    else:
        run(['git', 'remote', 'set-url', 'origin', repo_url])
    run(['git', 'branch', '-M', 'main'])
    p = run(['git', 'push', '-u', 'origin', 'main'])
    out = (p.stdout + p.stderr).strip()
    if p.returncode != 0:
        echo(out[-1500:])
        raise SystemExit('× 推送失败。常见原因：网络不通（代理掉线）或凭据失效。')
    echo('   推送完成。')

    echo('\n[4/5] 开启 GitHub Pages…')
    st, d = api(token, '/repos/%s/%s/pages' % (OWNER, REPO))
    if st == 200:
        echo('   Pages 已开启。')
    else:
        st2, d2 = api(token, '/repos/%s/%s/pages' % (OWNER, REPO), 'POST',
                      {'source': {'branch': 'main', 'path': '/'}})
        if st2 in (200, 201, 204):
            echo('   Pages 已开启。')
        elif st2 == 409:
            echo('   Pages 已存在。')
        else:
            echo('   ！自动开启失败（HTTP %s）：%s' % (st2, str(d2)[:200]))
            echo('   请手动到仓库 Settings → Pages 选择 main 分支 / root 目录。')

    echo('\n[5/5] 完成')
    echo('   仓库地址：https://github.com/%s/%s' % (OWNER, REPO))
    echo('   网站地址：https://%s.github.io/%s/' % (OWNER.lower(), REPO))
    echo('   （首次部署约需 1 分钟生效，之后每次 push 会自动重新发布）')


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        echo('\n× 出错：%s' % e)
        sys.exit(1)
    input('\n按回车键关闭…')

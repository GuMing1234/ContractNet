# GitHub 操作手册（第一次提交代码看这个）

---

## 一、建仓库（只有负责人做一次）

### 1. 建空仓库

打开 <https://github.com/new>，按下面填：

| 字段 | 填什么 |
|---|---|
| Repository name | `ContractNet` |
| Description | 契约驱动的多 Agent 协作调度框架 |
| **Public / Private** | **先选 Private**（W8 准备开源时再转 Public） |
| Add a README file | ❌ **不要勾**（我们本地已经有，勾了会冲突） |
| Add .gitignore | ❌ **不要勾**（本地已有） |
| Choose a license | ❌ 先不选（等决定开源再选 MIT） |

> ⚠️ **不要用 Fork**。Fork 别人的仓库会在你的项目页显示 "forked from xxx"，
> 看起来像你在改别人的东西。我们要建全新的空仓库。

### 2. 把本地代码推上去

```powershell
cd D:\PythonStudy\multi-agent\ContractNet

git remote add origin https://github.com/你的用户名/ContractNet.git
git push -u origin main
```

如果提示要登录：用 **Personal Access Token** 当密码。
（GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token，勾 `repo` 权限）

---

## 二、设置分支保护（负责人做，5 分钟，很重要）

仓库页 → **Settings** → 左侧 **Branches** → **Add branch protection rule**

| 选项 | 值 |
|---|---|
| Branch name pattern | `main` |
| Require a pull request before merging | ✅ 勾 |
| └ Require approvals | **1** |
| └ Dismiss stale pull request approvals | ✅ 勾 |
| Do not allow bypassing the above settings | ✅ 勾 |

> 这一步之后，**谁都不能直接 push main**，包括你自己。这能保住全组的代码。

---

## 三、加人进仓库（负责人做）

仓库页 → **Settings** → **Collaborators** → **Add people** → 输入他们的 GitHub 用户名

让他们接受邮件邀请。

> 如果免费额度限制协作人数，两个选择：
> ① 立刻转 Public（开源项目对简历更有利）
> ② 改用 Gitee（国内访问快，但生态弱）

---

## 四、每个人第一次提交（全员做）

```bash
# 1. 克隆（第一次）
git clone https://github.com/组织或用户名/ContractNet.git
cd ContractNet

# 2. 配置你的身份（只需一次）
git config user.name "你的名字"
git config user.email "你的邮箱"

# 3. 拉最新
git checkout main
git pull

# 4. 开分支
git checkout -b docs/add-你的名字

# 5. 改 docs/members.md，加上你那一行

# 6. 提交
git add docs/members.md
git commit -m "docs: add 你的名字 to members"

# 7. 推送
git push -u origin docs/add-你的名字

# 8. 打开终端里显示的链接，填 PR 描述，点 Create pull request
```

**负责人合并后，你就正式加入项目了。**

---

## 五、之后每天的标准动作

```bash
# 开工前
git checkout main && git pull
git checkout 你的分支
git merge main          # 把最新的合进来，避免最后大冲突

# 收工时
git add -A
git commit -m "feat(模块): 做了什么"
git push
```

---

## 六、常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| `push` 被拒绝 | main 被保护了 | 正常。改成推到自己的分支，然后开 PR |
| `rejected - non-fast-forward` | 你的分支落后了 | `git pull` 或 `git merge main` 后再推 |
| 看到 `<<<<<<< HEAD` | 冲突了 | 打开文件，删掉标记，留想要的内容 |
| 不小心把 `.env` 提交了 | 没配 gitignore | **立刻**换掉那个 API key，然后 `git rm --cached .env` |
| PR 显示几十个文件改动 | 分支从错误的地方分出来的 | 关掉 PR，重新从最新 main 建分支 |

---

## 七、提交前自检（贴在自己桌上）

```
[ ] git status 里没有 .env
[ ] 没有 __pycache__ 之类的垃圾
[ ] 改动只涉及我的模块（或已说明）
[ ] python -m pytest -q 全绿
[ ] PR 描述写了「怎么验证」
```

# 02 · 协作规范

> 本文是团队唯一的协作规范来源。违反标注为「驳回」的条目，PR 会被直接退回。

---

## 一、六条铁律

| #     | 铁律                                    | 理由                                                     |
| ----- | --------------------------------------- | -------------------------------------------------------- |
| **1** | 绝不直接 push `main`                    | 多人推同一分支会互相覆盖，且无法审查                     |
| **2** | 跨模块只传 Pydantic 对象，禁止传 `dict` | `dict` 的键拼错不报错，到别的模块才暴露                  |
| **3** | 禁止 `except: pass`                     | 吞掉异常后，只会看到「结果不对但无从定位」               |
| **4** | 改 `core/types.py` 之前先在群里声明     | 它是全组共用契约，单人改动会导致全组失效                 |
| **5** | 每个 PR 必须写明「怎么验证」            | 「做完了」是主观判断，「这条命令跑出这个结果」才是客观的 |
| **6** | 不得整段复制参考实现                    | 复制即失去学习价值，且无法说明实现理由                   |

---

## 二、日常流程

```bash
git checkout main && git pull          # 开工前
git checkout -b feat/模块-简述          # 建分支
# …… 编码 ……
git status && git diff                 # 自查
git add -A
git commit -m "feat(planner): 用 LLM 替换写死的分解模板"
git push -u origin feat/模块-简述
# 打开链接 → 填 PR 模板 → 提交 → 指定 Reviewers
# 等 approve（见 §六 6.1）→ 由副审点 Squash and merge → 删分支
git checkout main && git pull          # 收尾，同步回本地
git branch -d feat/模块-简述
```

### 救急命令

| 场景               | 命令                                                                   |
| ------------------ | ---------------------------------------------------------------------- |
| 撤销未提交改动     | `git restore .`                                                        |
| 撤销提交但保留改动 | `git reset --soft HEAD~1`                                              |
| 分支落后           | `git checkout main && git pull && git checkout 分支 && git merge main` |

### 三条禁令

```bash
git push -f            ❌ 会覆盖他人提交
git reset --hard       ❌ 改动不可恢复
直接在 main 上 commit   ❌ 违反铁律 1
```

---

## 三、提交信息规范

格式：`类型(模块): 做了什么`

| 类型       | 用途             |
| ---------- | ---------------- |
| `feat`     | 新功能           |
| `fix`      | 修复缺陷         |
| `docs`     | 仅文档           |
| `refactor` | 重构，不改变行为 |
| `test`     | 测试             |
| `chore`    | 配置、依赖等杂项 |

> **仓库是公开的，提交历史即工作记录。**
> 应避免 `update` / `fix` / `1` 这类信息；也避免在提交信息中书写「照搬某某实现」。
> 参考了某段做法时，记入 `docs/decisions/`，并在其中说明参考范围与自己的改动。

---

## 四、提交前 60 秒自检

```bash
git status                                             # 有无 .env、笔记、参考实现混入
git diff --stat                                        # 改动规模（超过 400 行考虑拆分）
git ls-files | grep -iE "env$|key|secret|token|reference"
```

---

## 五、禁止提交的内容

| 类型         | 示例                                | 后果                             |
| ------------ | ----------------------------------- | -------------------------------- |
| 密钥         | `.env`、`sk-...`、token             | 他人可消耗你的额度，账单由你承担 |
| 个人信息     | 学号、手机号、身份证                | 公开即永久公开                   |
| 参考实现代码 | `reference/`、`ContractNet-学长版/` | 涉及他人代码版权                 |
| 大文件       | 视频、数据集、压缩包                | 仓库体积永久增大                 |
| 运行产物     | `__pycache__/`、`.idea/`、`out.txt` | 降低仓库可读性                   |
| 内部笔记     | 评审意见、个人备注                  | 不应对外可见                     |

`.gitignore` 已覆盖大部分，但**无法阻止 `git add -f`**。

### 隐私设置（每人执行一次）

1. GitHub → Settings → Emails → 勾选 **Keep my email addresses private**
2. 本地执行：

```powershell
git config --global user.email "数字ID+GitHub用户名@users.noreply.github.com"
```

3. 验证：`git log -1 --format="%ae"` 应输出 noreply 地址

> 原因：提交中的邮箱永久公开，常见邮箱地址内含手机号。

---

## 六、PR 规矩

- **≤ 400 行、≤ 3 天**，超过则拆分
- 一个 PR 只做一件事
- 描述必须包含「怎么验证」，且作者本人已按其执行过

### 6.1 副审（Reviewer）

**现任副审：夏传祥（R4，`123xcx321`）**，持有仓库 **Write** 权限——审批与合并只需要 Write，**不需要 Admin**（个人仓库也无法给他人 Admin 角色）。

**为什么需要副审**：`main` 开了分支保护，但**仓库管理员默认可以绕过保护**。要让人相信「规则对负责人也生效」，唯一的办法是把合并的判断权交出去。

| 副审审什么                           | 副审不审什么                         |
| ------------------------------------ | ------------------------------------ |
| ① 这个 PR 是不是**只做了它说的事**   | 代码风格（交给 `ruff`）              |
| ② 「怎么验证」那一段是不是**真跑过** | 架构设计（那是 `04-design.md` 的事） |

**谁需要 approve**：

| 谁的 PR        | 需要谁 approve                       |
| -------------- | ------------------------------------ |
| 其余 7 人      | 负责人（宋旭涛）；负责人不在时副审可代批 |
| **负责人本人** | **只有副审（夏传祥）**               |
| **副审本人**   | **只有负责人（宋旭涛）**             |

> 负责人**不得自己点 Merge**。副审请假时，由负责人当次点名的临时副审执行，并在 PR 里写明原因。

**这条规则由机制保证，不靠自觉**——见 §6.4。只设 `Require approvals = 1` 是不够的：那是「任意一个有写权限的人批准即可」，A 的 PR 由 B 批准照样能合。必须叠加 Code Owners 才真正限定审批人。

### 6.2 合并方式

| 项       | 规定                                                        |
| -------- | ----------------------------------------------------------- |
| 合并按钮 | **Squash and merge**（保持 main 一条线，一个 PR 一个提交）  |
| 谁点合并 | 有 Approve 记录之后**由副审点**；负责人不点自己 PR 的 Merge |
| 合并后   | 删掉该分支（网页上 `Delete branch`），本地 `git branch -d`  |

### 6.3 `main` 的保护设置（用 Rulesets，不用 Branch protection）

**为什么用 Rulesets**：旧的 Branch protection 规则里，仓库管理员默认可以绕过；而 Rulesets 的 bypass 权限是**显式授予**的——**Bypass list 留空，连管理员也绕不过**。这是「规则对负责人也生效」唯一不依赖自觉的做法。

| 设置项 | 值 |
|---|---|
| 位置 | `Settings → Rulesets → New branch ruleset` |
| Enforcement | Active |
| Target | Include default branch |
| **Bypass list** | **留空**（一个都不要加，含 Repository admin） |
| Require a pull request before merging | ✅ Required approvals = **1** |
| Dismiss stale pull request approvals | ✅（推送新提交后旧 approve 失效） |
| Block force pushes / Restrict deletions | ✅ |

**生效后必然的结果**：负责人也不能直接 `git push` 到 `main`（报 `GH006`）；且 GitHub 不允许 approve 自己的 PR，所以负责人的 PR **必然**要等副审。

> **设置完必须实测**：在 `main` 上改一行直接 push，**被拒绝才算生效**。
> Rulesets 的拒绝码是 **GH013**（`Repository rule violations found` + 「Changes must be made through a pull request」）；旧的 Branch protection 才是 GH006。看到哪个都不算错，关键是**推不上去**。
>
> ⚠️ **撤销测试提交时务必小心**：
> - **测试前先确认 `git status` 没有输出**。工作区有改动时，`git add -A` 会把真实改动一起塞进测试提交。
> - 撤销用 `git reset --soft HEAD~1` + `git checkout HEAD -- README.md`，**不要用 `git reset --hard`**——它会把混进来的真实改动一起删掉（本项目已踩过一次，改动一度全部丢失）。
>
> ```bash
> git checkout main && git pull
> echo "test" >> README.md
> git add README.md && git commit -m "test: 验证保护"
> git push                                   # 预期被拒：GH013
> git reset --soft HEAD~1                    # 撤销提交，改动留在暂存区
> git checkout HEAD -- README.md             # 只还原被测文件
> git status                                 # 应只剩你本来要提交的改动
> ```

### 6.4 只让「指定审批人」的 approve 生效（Code Owners）

**为什么还要这一步**：`Require approvals = 1` 只保证「**不是自己批的**」，不保证「**是副审批的**」。8 个人都有 Write 权限，A 的 PR 由 B 批准，规则同样满足——**副审制度会形同虚设**。

**解法**：`.github/CODEOWNERS` + Rulesets 里勾 **Require review from Code Owners**。

仓库里的 [`CODEOWNERS`](../.github/CODEOWNERS) 内容：

```
*                       @GuMing1234 @123xcx321
/.github/CODEOWNERS      @GuMing1234 @123xcx321
```

| 行 | 作用 |
|---|---|
| 第一行 | 全仓库的 code owner = 负责人 + 副审 |
| 第二行 | **CODEOWNERS 自身也归这两人**，防止有人改本文件放宽审批 |

**开启位置**：`Rulesets → 编辑 main 规则 → Require a pull request before merging → Additional settings → ✅ Require review from Code Owners`

**生效后的结果**：

| 谁的 PR | 谁的 approve 才算数 |
|---|---|
| 其余 7 人 | 负责人，或副审代批 |
| **负责人本人** | **只有副审**（批不了自己） |
| **副审本人** | **只有负责人**（批不了自己） |

> 其余成员的 approve **不计数**：PR 会停在 `Waiting for code owners review`，合并按钮保持灰色。他们仍然可以评论、提修改意见。
> 官方说明：code owner 必须对该仓库有 **write** 权限，否则该行不生效。
> **CODEOWNERS 必须在 `main` 上存在才起作用**——所以顺序是：先合并本文件，再去开规则。

---

## 七、泄露应急处理

> **顺序不可颠倒：先吊销，再删除。** 历史一旦公开，删除文件无法收回已被抓取的内容。

**密钥泄露**：① 到服务商后台吊销/重置该 Key ② 查账单 ③ 删除文件并提交 ④ 群内通报 ⑤ 将教训记入 `docs/decisions/`

**个人信息泄露**：① 立即修改文件 ② 仅最新一次提交时用 `git commit --amend` ③ 位于历史深处时需用 `git filter-repo` 重写历史（联系负责人协助）④ 涉及手机号等敏感信息时，可先将仓库转私有

**误提交他人代码**：① 立即改为自行实现 ② 在 `docs/decisions/` 补充说明 ③ 群内说明，不得隐瞒

---

## 八、卡住怎么办

> 自行尝试 30 分钟仍无进展，应立即求助。阻塞 3 小时的代价高于打断他人。

提问必须三段式：

```
【我想做什么】
【我试了什么】1. … 2. …
【现在什么情况】完整报错（文字，不要截图）
```

---

## 九、代码风格

交给工具，不做争论：
ruff是一个代码检查和格式化工具，主要用来把代码弄整齐

```bash
python -m ruff format .
python -m ruff check --fix .
```

人工只需遵守五条：

1. 函数超过 50 行时考虑拆分
2. 命名表意：`get_ready_tasks()` 优于 `grt()`
3. 提前返回，减少嵌套
4. 注释解释**为什么**，不解释**是什么**
5. 日志需可检索，避免 `print("ok")`

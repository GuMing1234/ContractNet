# 02 · 协作规范

> 本文是团队唯一的协作规范来源。违反标注为「驳回」的条目，PR 会被直接退回。

---

## 一、六条铁律

| # | 铁律 | 理由 |
|---|---|---|
| **1** | 绝不直接 push `main` | 多人推同一分支会互相覆盖，且无法审查 |
| **2** | 跨模块只传 Pydantic 对象，禁止传 `dict` | `dict` 的键拼错不报错，到别的模块才暴露 |
| **3** | 禁止 `except: pass` | 吞掉异常后，只会看到「结果不对但无从定位」 |
| **4** | 改 `core/types.py` 之前先在群里声明 | 它是全组共用契约，单人改动会导致全组失效 |
| **5** | 每个 PR 必须写明「怎么验证」 | 「做完了」是主观判断，「这条命令跑出这个结果」才是客观的 |
| **6** | 不得整段复制参考实现 | 复制即失去学习价值，且无法说明实现理由 |

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
# 打开链接 → 填 PR 模板 → 提交
```

### 救急命令

| 场景 | 命令 |
|---|---|
| 撤销未提交改动 | `git restore .` |
| 撤销提交但保留改动 | `git reset --soft HEAD~1` |
| 分支落后 | `git checkout main && git pull && git checkout 分支 && git merge main` |

### 三条禁令

```bash
git push -f            ❌ 会覆盖他人提交
git reset --hard       ❌ 改动不可恢复
直接在 main 上 commit   ❌ 违反铁律 1
```

---

## 三、提交信息规范

格式：`类型(模块): 做了什么`

| 类型 | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修复缺陷 |
| `docs` | 仅文档 |
| `refactor` | 重构，不改变行为 |
| `test` | 测试 |
| `chore` | 配置、依赖等杂项 |

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

| 类型 | 示例 | 后果 |
|---|---|---|
| 密钥 | `.env`、`sk-...`、token | 他人可消耗你的额度，账单由你承担 |
| 个人信息 | 学号、手机号、身份证 | 公开即永久公开 |
| 参考实现代码 | `reference/`、`ContractNet-学长版/` | 涉及他人代码版权 |
| 大文件 | 视频、数据集、压缩包 | 仓库体积永久增大 |
| 运行产物 | `__pycache__/`、`.idea/`、`out.txt` | 降低仓库可读性 |
| 内部笔记 | 评审意见、个人备注 | 不应对外可见 |

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

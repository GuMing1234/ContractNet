# 01 · 环境与协作流程

> 本文覆盖三件事：本地环境、GitHub 仓库设置、每人第一次提交。

---

## 一、本地环境（30 分钟）

```powershell
# 1. 克隆
git clone https://github.com/GuMing1234/ContractNet.git
cd ContractNet

# 2. 装依赖（-e 表示可编辑安装，改代码立即生效）
pip install -e ".[dev]"

# 3. 跑测试
python -m pytest -q

# 4. 跑最小示例（不调大模型，零成本）
python -X utf8 examples/quickstart.py
```

**成功标志**：测试全绿；示例输出 4 个成果物，且「Implement the core functionality」由 **Coder** 执行。

> **Windows 必读**：项目含中文与符号字符，不加 `-X utf8` 会抛 `UnicodeEncodeError`。
> 另外 `PYTHONIOENCODING=utf-8 python x.py` 是 bash 写法，**在 PowerShell 中会报错**，请统一用 `python -X utf8 x.py`。

**配置模型（可选）**：把 `.env.example` 复制为 `.env` 并填入**你自己的** API Key。不配也能跑测试与示例。

---

## 二、仓库设置（仅负责人执行一次）

### 1. 设置分支保护

仓库页 → **Settings** → **Branches** → **Add branch protection rule**

| 选项 | 值 |
|---|---|
| Branch name pattern | `main` |
| Require a pull request before merging | ✅ |
| Require approvals | **1** |
| Do not allow bypassing the above settings | ✅ |

### 2. 邀请成员

**Settings** → **Collaborators** → **Add people**，输入 GitHub 用户名。

> **公开仓库仍需要邀请。** 公开只意味着任何人可读、可 fork；
> 要能建分支并推送，必须是 collaborator。否则只能走 fork + PR，多两步操作。

### 3. 确认 PR 模板生效

`.github/pull_request_template.md` 已就位，开 PR 时会自动填充。

---

## 三、每人第一次提交（3 分钟）

```bash
# 1. 配置身份（只需一次）
git config user.name "你的名字"
git config user.email "你的GitHub用户名@users.noreply.github.com"

# 2. 同步主分支
git checkout main
git pull

# 3. 建分支  这后面 “docs/add-你的名字” 是一个分支名，用来区分不同人的
git checkout -b docs/add-你的名字

# 4. 编辑 docs/06-members.md，加上你自己那一行

# 5. 提交与推送
git add docs/06-members.md
git commit -m "docs(members): 添加 <你的名字>"
git push -u origin docs/add-你的名字

# 6. 打开终端输出的链接，填写 PR 描述并提交
```

> 第一个 PR **只改文档**，目的是在零风险的情况下走通全流程。

---

## 四、每日标准动作

```bash
# 开工前（必做）
git checkout main && git pull
git checkout 你的分支
git merge main

# 收工时
git add -A
git commit -m "feat(模块): 做了什么"
git push
```

---

## 五、常见故障

| 现象                            | 原因               | 处理                                                       |
| ----------------------------- | ---------------- | -------------------------------------------------------- |
| `push` 被拒绝                    | `main` 受保护       | 正常。改推自己的分支后开 PR                                          |
| `rejected - non-fast-forward` | 分支落后             | `git merge main` 后再推                                     |
| 出现 `<<<<<<< HEAD`             | 冲突               | 打开文件删除标记行，保留目标内容                                         |
| PR 显示几十个文件改动                  | 分支基点过旧           | 关闭 PR，从最新 `main` 重新建分支                                   |
| `UnicodeEncodeError`          | 缺少 `-X utf8`     | 加参数重跑                                                    |
| 误提交 `.env`                    | 使用了 `git add -f` | **立即吊销该 API Key**，流程见 [02 协作规范](02-collaboration.md) 第七节 |

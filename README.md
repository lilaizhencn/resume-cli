# resume-cli

一个面向面试演示的同步 Python CLI：读取本地 PDF 简历，自动处理文本型或扫描型页面，调用 OpenAI 提取结构化信息，并根据岗位描述（JD）生成可校验的匹配评分。

> 匹配分数仅用于辅助人工评估，不应作为自动录用或淘汰决定。

## 技术选型

- Python 3.11+
- Typer：CLI 与帮助信息
- pypdf：PDF 文本层提取
- PyMuPDF + PaddleOCR：扫描页本地 OCR（可选安装）
- OpenAI Python SDK + Structured Outputs：结构化模型输出
- Pydantic v2：本地 JSON Schema 校验
- pytest：不消耗 Token 的离线测试

项目保持同步执行。单次命令只处理一份简历；PDF/OCR 与 AI 客户端通过接口隔离，未来如需批量处理，可分别为网络请求增加有界异步并发、为 OCR 增加进程池。

## 项目结构

```text
src/resume_cli/
├── cli.py          # Typer 命令与错误边界
├── services.py     # parse / extract / score 用例编排
├── pdf_parser.py   # PDF 校验、文本提取和 OCR 自动检测
├── ocr.py          # 延迟加载的 PaddleOCR 适配器
├── ai.py           # OpenAI 与 Mock AI 客户端
├── prompts.py      # 版本化可信 Prompt
├── schemas.py      # Pydantic 输出模型和固定评分公式
├── config.py       # 环境变量配置
├── output.py       # JSON 输出文件
└── errors.py       # 用户错误和 CLI 退出码
```

## 安装

推荐 Python 3.11 或 3.12，尤其是需要安装本地 OCR 时。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

开发依赖：

```bash
python -m pip install -e '.[dev]'
```

### OCR 安装

普通文本 PDF 不需要 OCR 依赖。扫描页会被自动检测；如需支持扫描件：

```bash
python -m pip install -e '.[ocr]'
```

PaddleOCR 3.x 使用本地推理，首次识别可能下载模型文件。不同操作系统、CPU/GPU 对 PaddlePaddle 的安装方式可能不同；如果上述命令失败，请按照 PaddlePaddle 对应平台的安装说明先安装推理引擎。

## 环境变量

复制示例文件：

```bash
cp .env.example .env
```

配置：

```dotenv
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-5.6-sol
```

也可以直接使用终端环境变量：

```bash
export OPENAI_API_KEY="sk-your-key"
export OPENAI_MODEL="gpt-5.6-sol"
```

`.env` 已被 Git 忽略。真实 API Key 不得写入代码、README、测试或 Git 历史。`parse` 和 `--mock` 不需要 API Key。

## CLI 命令

查看帮助：

```bash
resume-cli --help
resume-cli parse --help
resume-cli extract --help
resume-cli score --help
```

顶层及各子命令的帮助文案同时提供中文和英文版本，参数名称在两种语言下保持一致。

### 解析 PDF

```bash
resume-cli parse ./resume.pdf
```

程序先读取每页文本层。文本不足且页面包含图像时，只对该页自动执行 OCR，然后按照原页序合并结果。代码中的 `OCR_MIN_PAGE_CHARS` 是有名称、可测试的检测阈值。

### 提取结构化信息

真实模型：

```bash
resume-cli extract ./resume.pdf
```

离线演示：

```bash
resume-cli extract ./resume.pdf --mock
```

示例输出：

```json
{
  "name": "李明",
  "phone": "13800138000",
  "email": "liming@example.com",
  "city": "上海",
  "education": [
    {
      "school": "示例大学",
      "major": "计算机科学与技术",
      "degree": "本科",
      "graduation_time": "2022-06"
    }
  ],
  "skills": ["Python", "TypeScript", "Docker", "OpenAI API"]
}
```

### JD 匹配评分

```bash
resume-cli score ./resume.pdf --jd ./examples/jd.txt
resume-cli score ./resume.pdf --jd ./examples/jd.txt --mock
```

固定权重为技能 40%、经历 40%、教育 20%。AI 只返回三个维度的分数；`overall_score` 由程序按权重计算并使用整数四舍五入。如果 JD 没有明确教育要求，`education_score` 按 100 处理，使其不产生惩罚。

```json
{
  "overall_score": 82,
  "skill_score": 88,
  "experience_score": 80,
  "education_score": 75,
  "comment": "候选人具备较好的全栈开发基础，主要技能与岗位匹配，但仍需确认大模型项目的实际负责范围。",
  "interview_questions": [
    "请介绍一个你主导过的全栈项目，以及你负责的关键决策。",
    "请说明你调用大模型 API 时如何处理结构化输出和失败重试。"
  ]
}
```

### 保存 JSON

```bash
resume-cli extract ./resume.pdf --mock --output result.json
resume-cli score ./resume.pdf --jd ./examples/jd.txt --mock --output score.json
```

默认不覆盖已有文件；需要明确传入 `--force`。JSON 始终输出到 stdout，保存提示输出到 stderr，便于管道处理。

## AI 约束与安全

- 简历和 JD 始终作为不可信数据传入，不会拼接到系统 Prompt。
- 模型不具备文件、Shell、网络或其他外部工具权限。
- 使用 Structured Outputs，并再次通过本地 Pydantic 模型校验。
- 未提及的字段必须为 `null` 或空数组，禁止推断和虚构经历。
- 总分由程序计算，不接受模型自行生成的总分。
- 评分前会尽可能脱敏姓名标签、邮箱和常见电话号码。
- 日志和错误中不输出简历正文、JD、原始模型响应或 API Key。

真实 `extract` 和 `score` 会将完成任务所需的简历/JD 文本发送到配置的 OpenAI API。使用真实候选人资料前，应取得适当授权并确认组织的数据处理要求。PDF 解析、OCR 和 `--mock` 均在本地完成。

## 测试

默认测试不访问网络、不读取 API Key、不消耗 Token：

```bash
make test
make lint
```

测试覆盖正常 PDF、输入错误、扫描页自动 OCR（Fake OCR）、空 JD、Mock 命令、结构化输出失败、分数范围和固定总分公式。

## 已实现功能

- `parse`、`extract`、`score` 和各级 `--help`
- PDF 文件、扩展名、文件头、损坏/加密/空文本错误处理
- 混合 PDF 的逐页文本提取与自动 OCR 降级
- OpenAI Structured Outputs 与 Pydantic 二次校验
- Prompt Injection 能力隔离
- 固定评分规则与面试问题
- `--mock` 离线演示
- `--output` 和 `--force`
- UTF-8 中文 JSON 输出
- Makefile 与离线测试

## 已知问题

- OCR 精度受扫描分辨率、旋转、复杂双栏排版和手写内容影响。
- OCR 可选依赖体积较大，且不同平台的推理引擎安装方式存在差异。
- 当前一次处理一份简历，不包含批量任务、缓存或异步队列。
- 超长简历/JD 当前会明确拒绝，尚未实现分块合并。
- 基于标签和格式的脱敏无法保证识别所有姓名或国际电话号码。
- AI 输出和评分可能随模型变化而变化；重要招聘决定必须由人工复核。

## Makefile

```bash
make install       # 安装基础功能
make install-ocr   # 安装 OCR 扩展
make install-dev   # 安装开发/测试工具
make lint          # Ruff 检查
make test          # 离线测试
make help          # 查看 CLI 帮助
```

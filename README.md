# 📖 Phonics Tracker - 丽声自然拼读打卡程序

基于艾宾浩斯遗忘曲线的间隔重复学习系统，专为《丽声我的第一套自然拼读故事书》（Reading Garden Phonics）设计。

## ✨ 功能特色

- 📈 **今日任务**：每天自动推荐：新课 + 复习 + 薄弱点加强
- 🎯 **薄弱点追踪**：自动识别笼音混淆点，针对性加强
- 📊 **可视化分析**：学习进度、薄弱点数据一目了然
- ⚙️ **自定义进度**：支持设置已学完到第几课
- 📤 **数据备份**：导出/导入 JSON 备份，换设备不丢失

## 🚀 快速部署（Streamlit Cloud）

### 第一步：注册 GitHub 账号

1. 打开 [github.com](https://github.com)
2. 点击 "Sign up"
3. 输入邮箱、密码，按提示完成验证（约 1 分钟）

### 第二步：创建代码仓库

1. 登录 GitHub 后，点击右上角 "+" → "New repository"
2. Repository name 填写：`phonics-tracker`
3. 选择 "Public"（免费版要求公开仓库）
4. 点击 "Create repository"

### 第三步：上传文件

在刚创建的仓库页面：

1. 点击 "uploading an existing file" 链接
2. 点击 "choose your files"
3. 选择以下文件上传：
   - `app.py`
   - `curriculum_data.py`
   - `requirements.txt`
4. 点击 "Commit changes"

### 第四步：部署到 Streamlit Cloud

1. 打开 [share.streamlit.io](https://share.streamlit.io)
2. 点击 "Sign in with GitHub"
3. 点击 "New app"
4. 选择刚创建的 `phonics-tracker` 仓库
5. 点击 "Deploy"
6. 等待约 2 分钟，部署完成后会显示网址

## 📝 使用指南

### 首次使用

1. 打开部署好的网址
2. 点击**设置**页面
3. 调整**已学完到第几课**滑块，匹配你的实际进度
4. 点击"保存设置"
5. 点击**今日任务**，开始学习！

### 每日流程

1. 打开程序 → 查看**今日任务**
2. 按顺序学习：新课 → 复习 → 薄弱点加强
3. 学完后点击**打卡**，记录表现
4. 查看**学习进度**，了解整体情况

### 数据备份

由于云端部署数据会定期清理，建议：
- 每天学完后，在**设置**页面点击"下载数据备份"
- 保存备份文件到电脑/手机
- 下次使用时，上传备份文件即可恢复进度

## 📑 技术标签

- Python 3.8+
- Streamlit
- Plotly 可视化
- JSON 数据存储

## 📋 项目文件说明

| 文件 | 说明 |
|------|------|
| `app.py` | 主程序：界面和业务逻辑 |
| `curriculum_data.py` | 课程数据：27个拼读任务 |
| `requirements.txt` | Python 依赖包列表 |
| `data/` | 数据存储目录（运行时自动生成） |
| `.streamlit/config.toml` | Streamlit 配置 |
# 版本标记: v2.1 多用户隔离

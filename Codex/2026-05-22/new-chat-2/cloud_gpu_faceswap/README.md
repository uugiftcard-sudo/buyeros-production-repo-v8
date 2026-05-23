# 🎭 Cloud GPU Face Swap — 完整使用指南

将任意人物的脸替换到目标视频中，全程使用免费 GPU，无需本地 NVIDIA 显卡。

---

## 目录

- [项目概述](#项目概述)
- [完整流程概览](#完整流程概览)
- [第一步：在 Mac 本地准备上传包](#第一步在-mac-本地准备上传包)
- [第二步：在云端 GPU 运行](#第二步在云端-gpu-运行)
- [免费 GPU 资源对比](#免费-gpu-资源对比)
- [时间预估](#时间预估)
- [常见错误与解决方案](#常见错误与解决方案)
- [如何提升换脸质量](#如何提升换脸质量)
- [完整视频转换](#完整视频转换)

---

## 项目概述

本项目基于 [deepfakes/faceswap](https://github.com/deepfakes/faceswap)，提供两种免费云端 GPU 运行方式：

| 平台 | 优点 | 缺点 |
|------|------|------|
| **Google Colab** | 上传文件方便，免费 T4 | 约90分钟超时，需保持活跃 |
| **Kaggle** | 稳定 T4 x2，更长运行时间 | 需要手动上传数据集 |

### 素材要求

- **源图片（Source）**：15–30 张高清正面照片，建议表情丰富、光线充足
- **目标视频（Target）**：人物面部清晰的 MP4 视频，建议 1080p 以内

> 源图片放入 Mac 本地 `source_faces/` 目录，目标视频放入 `input/` 目录（`target_test_5s.mp4` 和 `target_normalized.mp4`）。

---

## 完整流程概览

```
Mac 本地准备（一次性）
  ├── 准备源图片 → source_faces/
  ├── 准备目标视频 → input/
  └── 运行 scripts/00_make_upload_package.sh
                                    ↓
                              cloud_gpu_faceswap_upload.tar.gz
                                    ↓
          ┌────────────────────────┴────────────────────────┐
          ↓                                                     ↓
   Google Colab                                        Kaggle Notebooks
  ├── Step 1: 上传压缩包                                   ├── Step 1: 添加数据集
  ├── Step 2: 安装 faceswap (10-20min)                   ├── Step 2: 安装 faceswap
  ├── Step 3: 提取人脸 (5-15min)                         ├── Step 3: 提取人脸
  ├── Step 4: 检查人脸（人工）                            ├── Step 4: 检查人脸（人工）
  ├── Step 5: 训练模型 (30-90min)                         ├── Step 5: 训练模型
  └── Step 6: 转换 + 下载视频                              └── Step 6: 转换 + 下载视频
```

---

## 第一步：在 Mac 本地准备上传包

### 1.1 准备源图片

```bash
# 在项目目录创建源图片目录
mkdir -p ../source_faces

# 放入 15-30 张源人物照片（支持 jpg/png/webp）
# 建议：正面照、表情丰富、多种角度、高清
```

### 1.2 准备目标视频

将视频文件放入 `cloud_gpu_faceswap/input/` 目录：
- `target_test_5s.mp4` — 5秒测试片段（默认使用）
- `target_normalized.mp4` — 完整视频（Step 6 使用）

### 1.3 生成上传压缩包

```bash
cd cloud_gpu_faceswap
bash scripts/00_make_upload_package.sh
```

输出的文件路径会打印在终端，记住该路径。

---

## 第二步：在云端 GPU 运行

### 方法 A — Google Colab（推荐新手）

**详细教程：** 阅读 `COLAB_FREE_README.md`

**快速步骤：**
1. 打开 [Google Colab](https://colab.research.google.com/)
2. 上传 `faceswap_free_colab.ipynb`
3. `Runtime → Change runtime type → T4 GPU`
4. 上传 `cloud_gpu_faceswap_upload.tar.gz`
5. 从上到下运行所有单元格

### 方法 B — Kaggle Notebooks（更稳定）

**详细教程：** 阅读 `KAGGLE_README.md`

**快速步骤：**
1. 打开 [Kaggle](https://www.kaggle.com/notebooks)
2. 新建 Notebook → `Settings → Accelerator → GPU T4 x2`
3. `Settings → Internet → Internet on`
4. `Add input → Dataset →` 上传 `cloud_gpu_faceswap_upload.tar.gz`
5. 导入 `faceswap_kaggle.ipynb`
6. 运行所有单元格

---

## 免费 GPU 资源对比

| 特性 | Google Colab（免费） | Kaggle（免费） |
|------|---------------------|----------------|
| GPU 型号 | 通常 T4（偶有 P100） | T4 x2 或 P100 |
| 显存 | ~15 GB | ~16 GB（双卡） |
| 运行时间限制 | ~90 分钟无活动断开 | ~9 小时 |
| 文件上传 | 直接上传（本地文件） | 需要先作为 Dataset 上传 |
| Internet | 默认开启 | 需手动开启 |
| 数据持久化 | 需要挂载 Google Drive | 无（临时存储） |
| 适合人群 | 新手、快速测试 | 需要长时训练 |

---

## 时间预估

| 步骤 | 说明 | Colab 耗时 | Kaggle 耗时 |
|------|------|-----------|-------------|
| Step 1 上传 | 上传 tar.gz 包 | 1–5 分钟 | 1–3 分钟 |
| Step 2 安装 | 安装 faceswap 依赖 | 10–20 分钟 | 10–20 分钟 |
| Step 3 提取 | 人脸检测与裁剪 | 5–15 分钟 | 5–15 分钟 |
| Step 4 检查 | 人工检查（不含运行时间） | — | — |
| Step 5 训练（1k次） | 快速测试 | 15–30 分钟 | 15–30 分钟 |
| Step 5 训练（3k次） | 推荐质量 | 45–90 分钟 | 45–90 分钟 |
| Step 5 训练（5k次） | 高质量 | 90–180 分钟 | 90–180 分钟 |
| Step 6 转换 | 换脸 + 合成视频 | 3–10 分钟 | 3–10 分钟 |
| **合计（3k次）** | **完整流程** | **约 1.5–2.5 小时** | **约 1.5–2.5 小时** |

---

## 常见错误与解决方案

### ❌ GitHub 克隆失败（国内网络）

**症状：** `Failed to connect to github.com`

**解决：**
```bash
# 在安装单元格中替换镜像
git clone https://github.com.cnpmjs.org/deepfakes/faceswap.git tools/faceswap
```

### ❌ GPU 显存不足（OOM）

**症状：** `CUDA out of memory`

**解决：** 降低 batch size，编辑 `scripts/04_train_preview.sh`：
```bash
# 找到 -bs 8，改为：
-bs 4
```

### ❌ Colab 断开连接

**症状：** 训练中途 Colab 报错退出

**解决：**
1. 挂载 Google Drive，将 `workspace/model` 同步到云端
2. 分多次训练，每次训练后保存 checkpoint
3. 使用 Kaggle（运行时间更长）

### ❌ 找不到 cloud_gpu_faceswap_upload.tar.gz

**症状：** Kaggle 报 `FileNotFoundError`

**解决：** 确认已将文件作为 **Dataset**（而非 Code）添加到 Notebook：
`Add input → Datasets →` 上传压缩包

### ❌ 人脸提取结果为空

**症状：** `source_faces_extract/` 目录为空

**可能原因：**
- 源图片质量太差（模糊/遮挡）
- 图片中没有检测到人脸

**解决：** 使用高清、正面、光线充足的照片，建议 512px 以上分辨率

### ❌ Internet 访问被禁用（Kaggle）

**症状：** pip install 报 `Connection refused`

**解决：** `Settings → Internet → Internet on`（新建 Notebook 默认关闭）

---

## 如何提升换脸质量

1. **增加源图片数量**：15–30 张正面照片效果最佳
2. **提高图片质量**：高清、光线充足、无遮挡
3. **增加训练迭代**：3000 → 5000 → 10000 次迭代
4. **多样化表情**：源图片包含不同表情（微笑、严肃、侧脸）
5. **选择合适的目标视频**：目标人物面部清晰、光线稳定

---

## 完整视频转换

在确认测试视频（`faceswap_test.mp4`）效果满意后，可对完整视频进行转换：

```bash
# 在 Colab/Kaggle Notebook 中运行
bash scripts/06_convert_full_if_approved.sh
```

该脚本使用 `input/target_normalized.mp4`（完整目标视频）进行转换，输出为 `output/faceswap_full.mp4`。

> ⚠️ 完整视频转换时间取决于视频长度，建议先用 5 秒测试视频验证效果。

---

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `00_make_upload_package.sh` | Mac 本地执行：生成 tar.gz 上传包 |
| `01_setup_faceswap.sh` | Ubuntu VM 执行：安装系统依赖和 faceswap |
| `02_prepare_workspace.sh` | 复制源图片 + 拆解目标视频为帧 |
| `03_extract_faces.sh` | 人脸检测与裁剪（使用 s3fd 模型） |
| `04_train_preview.sh` | 训练模型（可通过 `ITERATIONS` 环境变量控制） |
| `05_convert_test.sh` | 用训练好的模型换脸，生成测试 MP4 |
| `06_convert_full_if_approved.sh` | 用完整视频换脸，生成正式 MP4 |

---

*基于 [deepfakes/faceswap](https://github.com/deepfakes/faceswap) 构建*

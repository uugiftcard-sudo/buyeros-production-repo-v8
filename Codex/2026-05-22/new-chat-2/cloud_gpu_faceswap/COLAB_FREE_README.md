# Google Colab 免费版教程

使用 Google Colab 的免费 T4 GPU 进行 Face Swap，全程无需付费。

---

## 准备工作（本地 Mac）

### 1. 准备源图片

将源人物的照片放入 `../source_faces/` 目录（项目目录的上一级）。

```bash
# 示例：创建目录并放入图片
mkdir -p ../source_faces
# 将 15-30 张源人物照片复制到此目录
```

**图片要求：**
- 高清、正面、光线充足
- 多种表情和角度
- 建议分辨率 512px 以上
- 支持格式：jpg、png、webp

### 2. 准备目标视频

将视频文件放入 `input/` 目录：

| 文件 | 用途 |
|------|------|
| `input/target_test_5s.mp4` | 5秒测试片段（默认使用） |
| `input/target_normalized.mp4` | 完整视频（Step 6 使用） |

**视频要求：**
- MP4 格式，H.264 编码
- 建议 1080p 以内
- 人物面部清晰可见

### 3. 生成上传包

```bash
cd cloud_gpu_faceswap
bash scripts/00_make_upload_package.sh
```

终端会输出打包后的文件路径，记住这个路径。

---

## Colab 运行步骤

### 步骤 1 — 打开 Colab

访问 [Google Colab](https://colab.research.google.com/)，新建笔记本。

### 步骤 2 — 上传笔记本

上传本项目中的 `faceswap_free_colab.ipynb` 文件。

### 步骤 3 — 启用 GPU

`Runtime → Change runtime type → Hardware accelerator → T4 GPU → Save`

### 步骤 4 — 上传压缩包

运行到 `Step 1 — 上传打包文件` 单元格时，上传之前生成的 `cloud_gpu_faceswap_upload.tar.gz`。

### 步骤 5 — 按顺序运行

按从上到下的顺序运行所有单元格（每个 Step 一个代码块）。

---

## 时间估算（Colab 免费版）

| 步骤 | 预计时间 |
|------|---------|
| 上传压缩包 | 1–5 分钟 |
| 安装 faceswap | 10–20 分钟 |
| 提取人脸 | 5–15 分钟 |
| 训练 1000 次 | 15–30 分钟 |
| 训练 3000 次 | 45–90 分钟 |
| 转换并下载 | 3–10 分钟 |

**总时间（3000次迭代）：约 1.5–2.5 小时**

---

## Colab 特有注意事项

### 1. 保持活跃（防止断连）

Colab 免费版约 90 分钟无活动会自动断开。可在训练期间：
- 每 60 分钟运行一次空单元格保持活跃
- 或使用 Colab Pro（更长超时）

### 2. 挂载 Google Drive（推荐）

如果需要保存训练模型，在安装步骤前添加：

```python
from google.colab import drive
drive.mount('/content/drive')
```

然后在训练前将 `workspace/model` 目录复制到 Google Drive：

```bash
cp -r /content/faceswap_work/cloud_gpu_faceswap/workspace/model \
   /content/drive/MyDrive/faceswap_model/
```

### 3. Colab Pro vs 免费版

| 特性 | Colab 免费 | Colab Pro |
|------|-----------|-----------|
| GPU | T4（共享） | V100 / A100 |
| 内存 | ~12 GB | ~25 GB |
| 运行时间 | ~90 分钟 | ~12 小时 |
| 稳定性 | 中等 | 高 |

---

## 故障排除

### GitHub 克隆失败

在安装单元格中替换为镜像地址：

```bash
git clone https://github.com.cnpmjs.org/deepfakes/faceswap.git tools/faceswap
```

### 显存不足（OOM）

降低 batch size，编辑 `scripts/04_train_preview.sh` 中的 `-bs 8` 为 `-bs 4`。

### 下载中断

如果文件较大导致下载失败，可以分步下载：

```python
# 先复制到 Google Drive
import shutil
shutil.copy(
    '/content/faceswap_work/cloud_gpu_faceswap/output/faceswap_test.mp4',
    '/content/drive/MyDrive/faceswap_test.mp4'
)
```

---

## 下一步

测试视频效果满意后：

1. **提高质量**：增加 `ITERATIONS=5000` 或更多
2. **完整视频**：`bash scripts/06_convert_full_if_approved.sh`
3. **分享结果**：从 Colab 下载 `faceswap_test.mp4`

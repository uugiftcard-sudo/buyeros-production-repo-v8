# Kaggle 免费版教程

使用 Kaggle Notebooks 的免费 GPU（T4 x2 或 P100）进行 Face Swap，稳定性比 Colab 更好。

---

## 准备工作（本地 Mac）

### 1. 准备源图片

将源人物的照片放入 `../source_faces/` 目录。

```bash
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

### 3. 生成上传包

```bash
cd cloud_gpu_faceswap
bash scripts/00_make_upload_package.sh
```

---

## Kaggle 设置步骤

### 步骤 1 — 创建新 Notebook

访问 [Kaggle](https://www.kaggle.com/notebooks)，点击 `New Notebook`。

### 步骤 2 — 启用 GPU

右上角 `Settings → Accelerator → GPU T4 x2`（或 `GPU P100`）

### 步骤 3 — 开启网络访问

右上角 `Settings → Internet → Internet on`

> ⚠️ 新建 Notebook 时默认关闭，必须手动开启。

### 步骤 4 — 上传数据集

1. 右上角 `Add input`
2. 选择 `Datasets` → `Upload`
3. 上传 `cloud_gpu_faceswap_upload.tar.gz`（约 100MB–几 GB）
4. 等待上传完成（约 1–5 分钟）

> ⚠️ 上传时请勿关闭浏览器标签页。上传完成后，数据集会挂载到 `/kaggle/input/`。

### 步骤 5 — 导入笔记本

将 `faceswap_kaggle.ipynb` 中的代码复制到 Kaggle Notebook，或通过 `File → Import notebook` 导入。

---

## Kaggle 运行步骤

按从上到下的顺序运行所有单元格（6个 Step）：

| Step | 说明 | 预计时间 |
|------|------|---------|
| Step 0 | 检查 GPU | 几秒 |
| Step 1 | 解压上传的数据包 | 1–3 分钟 |
| Step 2 | 安装 faceswap | 10–20 分钟 |
| Step 3 | 提取人脸 | 5–15 分钟 |
| Step 4 | 检查人脸（人工） | 不限 |
| Step 5 | 训练模型 | 45–90 分钟 |
| Step 6 | 转换并下载 | 3–10 分钟 |

**总时间（3000次迭代）：约 1.5–2.5 小时**

---

## 下载结果

Kaggle 工作区文件为临时存储，**会话结束后消失**。务必在结束前下载：

### 方式 1 — Output 面板（推荐）

点击右侧 `Output` 面板，找到 `faceswap_output/faceswap_test.mp4`，点击下载。

### 方式 2 — 代码单元格下载

运行笔记本最后一个代码单元格，生成下载链接，点击链接下载。

---

## Kaggle 特有注意事项

### 1. 工作区是临时的

`/kaggle/working` 的所有文件在会话结束后被清除。如果需要保存：
- 每次运行结束后下载 `faceswap_test.mp4`
- 将训练模型同步到 Kaggle Dataset（需要手动创建）

### 2. 安装中断怎么办

如果安装步骤因超时中断：
1. 点击 `Restart & clear cell outputs`
2. 从 Step 2（安装）重新开始
3. 已克隆的 `tools/faceswap` 目录会被跳过

### 3. GPU 显存

Kaggle T4 x2 提供约 16 GB 显存，默认 batch size (`bs=8`) 足够。

如果遇到 OOM：
```bash
# 编辑 scripts/04_train_preview.sh
# 将 -bs 8 改为 -bs 4
```

### 4. Session 持续时间

Kaggle 免费 GPU 每次最长约 9 小时（连续运行），比 Colab 更长，更适合长时训练。

---

## 故障排除

### 找不到 dataset

**错误：** `FileNotFoundError: 找不到 cloud_gpu_faceswap_upload.tar.gz`

**原因：** 文件未作为 Dataset 上传

**解决：**
1. 确认上传位置是 `Datasets`（不是 `Code`）
2. 检查 Dataset 名称和路径
3. 重新上传或更换 Dataset

### Internet 关闭

**错误：** pip install 报 `Connection refused`

**解决：** `Settings → Internet → Internet on` → `Restart & clear cell outputs` → 从 Step 2 重新开始

### GitHub 克隆失败

在安装单元格中使用镜像：
```bash
git clone https://github.com.cnpmjs.org/deepfakes/faceswap.git tools/faceswap
```

---

## 下一步

测试视频效果满意后：

1. **提高质量**：增加 `ITERATIONS=5000` 或更多
2. **完整视频**：`bash scripts/06_convert_full_if_approved.sh`
3. **长期保存**：将结果下载到本地

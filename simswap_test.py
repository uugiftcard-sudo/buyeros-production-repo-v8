import sys
sys.path.insert(0, '/workspace/simswap_proj')

import cv2
import torch
import numpy as np
from models.fs_model import FaceSwapModel

print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
print("Loading model...")

model = FaceSwapModel()
model.setup()
print("Model loaded OK")

# Load source and target
src_img = cv2.imread('/workspace/source_new2.png')
cap = cv2.VideoCapture('/workspace/target_new2.mp4')
ret, tgt_frame = cap.read()
cap.release()

if src_img is None:
    print("ERROR: source image not found")
    sys.exit(1)
if tgt_frame is None:
    print("ERROR: target video empty")
    sys.exit(1)

print("Source shape:", src_img.shape)
print("Target frame shape:", tgt_frame.shape)

# Run face swap
print("Running face swap...")
result = model.swap(src_img, tgt_frame)

cv2.imwrite('/workspace/simswap_result.png', result)
print("Done! Result saved to /workspace/simswap_result.png")

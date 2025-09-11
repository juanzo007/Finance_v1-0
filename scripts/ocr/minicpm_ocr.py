# scripts/ocr/minicpm_ocr.py

from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
import torch

processor = AutoProcessor.from_pretrained("openbmb/MiniCPM-V-2")
model = AutoModelForCausalLM.from_pretrained(
    "openbmb/MiniCPM-V-2", torch_dtype=torch.float16, device_map="auto"
)


def run_ocr(img_path: str) -> str:
    image = Image.open(img_path).convert("RGB")
    prompt = "What is written in the image?"
    inputs = processor(prompt, image, return_tensors="pt").to(
        model.device, torch.float16
    )
    ids = model.generate(**inputs, max_new_tokens=512)
    return processor.decode(ids[0], skip_special_tokens=True)

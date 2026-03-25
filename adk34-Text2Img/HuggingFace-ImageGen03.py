import os
import re
from PIL import Image
from diffusers import StableDiffusionImg2ImgPipeline
import torch

# Output folder
output_folder = "output-image2image"
os.makedirs(output_folder, exist_ok=True)
print(f"📂 All images will be saved in '{output_folder}/'\n")

# Filename sanitizer
def sanitize_filename(text, max_length=50):
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    text = text.replace(" ", "_")
    return text[:max_length]

# Load model locally
print("🤖 Loading Stable Diffusion Img2Img model locally...")
device = "cuda" if torch.cuda.is_available() else "cpu"
pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
    "runwayml/stable-diffusion-img2img", torch_dtype=torch.float16 if device=="cuda" else torch.float32
).to(device)

print("💬 Model loaded! You can now edit images interactively.\n")

while True:
    prompt = input("Enter your prompt: ").strip()
    if prompt.lower() in ["exit", "quit"]:
        print("👋 Goodbye!")
        break

    if not prompt:
        print("⚠️ Enter a valid prompt.")
        continue

    image_path = input("Enter the path to your input image: ").strip()
    if not os.path.exists(image_path):
        print("⚠️ File not found!\n")
        continue

    try:
        init_image = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"❌ Could not open image: {e}\n")
        continue

    print(f"🎨 Generating an edited image for: '{prompt}' ...")
    try:
        result = pipe(prompt=prompt, image=init_image, strength=0.7, guidance_scale=7.5)
        result_image = result.images[0]

        safe_filename = sanitize_filename(prompt) + ".png"
        filepath = os.path.join(output_folder, safe_filename)
        result_image.save(filepath)
        print(f"✅ Edited image saved as {filepath}\n")

    except Exception as e:
        print(f"❌ Oops! Something went wrong: {e}\n")
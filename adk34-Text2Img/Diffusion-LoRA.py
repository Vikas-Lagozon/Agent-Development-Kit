# diffusion_lora.py
import torch
import os
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

# -----------------------------
# CONFIG
# -----------------------------
model_id = "runwayml/stable-diffusion-v1-5"
lora_path = "lora_output/my_lora.safetensors"
output_folder = "gen-images"

torch.set_num_threads(os.cpu_count())
os.makedirs(output_folder, exist_ok=True)

# -----------------------------
# LOAD PIPELINE (CPU-optimized)
# -----------------------------
print("⏳ Loading model...")
pipe = StableDiffusionPipeline.from_pretrained(
    model_id,
    torch_dtype=torch.float32,
    safety_checker=None,
    requires_safety_checker=False,
)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe.enable_attention_slicing()
pipe.enable_vae_slicing()

if os.path.exists(lora_path):
    pipe.load_lora_weights(lora_path)
    print(f"✅ LoRA weights loaded from: {lora_path}")
else:
    print(f"⚠️  No LoRA weights found at '{lora_path}', using base model.")

print("✅ Model ready.\n")

# -----------------------------
# FUNCTIONS
# -----------------------------

def generate_images(prompt, n_images=1):
    images = pipe(
        prompt,
        num_inference_steps=20,
        guidance_scale=7.5,
        num_images_per_prompt=n_images,
    ).images
    return images

def save_images(images, prompt):
    saved_paths = []
    safe_prompt = "".join(c for c in prompt if c.isalnum() or c == " ").strip()[:50]
    for i, img in enumerate(images):
        filepath = os.path.join(output_folder, f"{safe_prompt}_{i}.png")
        img.save(filepath)
        saved_paths.append(filepath)
    return saved_paths

# -----------------------------
# MAIN LOOP
# -----------------------------
print("🎨 LoRA Image Generator")
print(f"⚡ CPU threads: {os.cpu_count()} | Scheduler: DPMSolver (20 steps)")
print("Type 'exit' to quit\n")

while True:
    prompt = input("🧑 Prompt: ").strip()
    if prompt.lower() in ["exit", "quit"]:
        print("👋 Exiting...")
        break

    try:
        n_images = int(input("🧑 How many images to generate? (1-4): ").strip())
        n_images = max(1, min(4, n_images))  # clamp between 1 and 4
    except ValueError:
        print("⚠️  Invalid number, defaulting to 1.")
        n_images = 1

    print(f"⏳ Generating {n_images} image(s)...")
    images = generate_images(prompt, n_images=n_images)
    saved_paths = save_images(images, prompt)

    print("✅ Images saved:")
    for path in saved_paths:
        print("   📁", path)
    images[0].show()

    print("\n-----------------------------\n")

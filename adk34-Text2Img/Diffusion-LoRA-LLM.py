# diffusion_chatbot.py
import torch
import os
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

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

# -----------------------------
# LOAD LLM (Ollama)
# -----------------------------
chat_llm = ChatOllama(model="llama3.2:3b", temperature=0.5)

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

def llm_decide(user_prompt):
    """
    LLM decides:
      - Is this an image generation request → IMAGE
      - Or just a chat message → CHAT
    Returns: "image" | "chat"
    """
    system = SystemMessage(content="""You are a routing assistant for an AI image generation chatbot.

Given the user message, reply with EXACTLY one of:
- IMAGE  → user is asking to generate, draw, or create an image/picture/photo
- CHAT   → user is just having a conversation

Reply with only the label. No explanation.""")
    human = HumanMessage(content=f"User message: \"{user_prompt}\"")
    response = chat_llm.invoke([system, human])
    result = response.content.strip().upper()
    return "image" if "IMAGE" in result else "chat"

def chat_response(message):
    system = SystemMessage(content="You are a helpful and friendly AI assistant.")
    response = chat_llm.invoke([system, HumanMessage(content=message)])
    return response.content

# -----------------------------
# MAIN LOOP
# -----------------------------
print("\n🎨 AI Diffusion Chatbot (Text + Image)")
print(f"⚡ CPU threads: {os.cpu_count()} | Scheduler: DPMSolver (20 steps)")
print("Type 'exit' to quit\n")

while True:
    user_input = input("🧑 You: ").strip()
    if user_input.lower() in ["exit", "quit"]:
        print("👋 Exiting...")
        break

    intent = llm_decide(user_input)

    if intent == "image":
        n_images = int(input("🧑 How many images to generate? (1-4): "))
        print("⏳ Generating...")
        images = generate_images(user_input, n_images=n_images)
        saved_paths = save_images(images, user_input)
        print("✅ Images saved:")
        for path in saved_paths:
            print("   📁", path)
        images[0].show()
    else:
        response = chat_response(user_input)
        print("🤖 AI:", response)

    print("\n-----------------------------\n")

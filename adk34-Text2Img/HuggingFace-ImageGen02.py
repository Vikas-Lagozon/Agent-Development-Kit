import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv, find_dotenv

# Step 1: Load environment variables
print("🔑 Loading environment variables...")
load_dotenv(find_dotenv())

# Step 2: Initialize the Hugging Face Inference client
print("🤖 Initializing Hugging Face Inference client...")
client = InferenceClient(
    provider="nscale",
    api_key=os.environ["HF_TOKEN"],
)

# Step 3: Ensure output folder exists
output_folder = "output-text2image"
os.makedirs(output_folder, exist_ok=True)
print(f"📂 All images will be saved in '{output_folder}/' folder.\n")

print("💬 Welcome! Type a prompt to generate an image.")
print("Type 'exit' or 'quit' to stop the program.\n")

# Step 4: Interactive loop
while True:
    prompt = input("Enter your prompt: ").strip()
    
    if prompt.lower() in ["exit", "quit"]:
        print("👋 Goodbye! Thanks for generating images.")
        break

    if not prompt:
        print("⚠️ Please enter a valid prompt.")
        continue

    print(f"🎨 Generating an image for: '{prompt}' ...")
    try:
        image = client.text_to_image(
            prompt,
            model="black-forest-labs/FLUX.1-schnell",
        )
        # Safe filename
        safe_filename = prompt.replace(" ", "_")[:50] + ".png"
        filepath = os.path.join(output_folder, safe_filename)
        image.save(filepath)
        print(f"✅ Image saved as {filepath}\n")
    except Exception as e:
        print(f"❌ Oops! Something went wrong: {e}\n")


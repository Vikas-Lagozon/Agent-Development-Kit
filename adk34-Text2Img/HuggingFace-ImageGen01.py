import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Initialize Hugging Face Inference client
client = InferenceClient(
    provider="nscale",
    api_key=os.environ["HF_TOKEN"],
)

# Generate image from prompt
prompt = "Fight between Ironman vs Batman"
image = client.text_to_image(
    prompt,
    model="black-forest-labs/FLUX.1-schnell",
)

# Save image directly
image.save("IronBat.png")
print("Image saved as IronBat.png")

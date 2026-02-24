"""
agent.py

Dynamic Brand-Aware Advertisement Generator
Compatible with google-adk==1.22.0

Run with:

    adk web

Folder name must be a valid identifier:
    image_gen
"""

import os
from datetime import datetime

from google import genai
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from google.adk.tools.google_search_tool import google_search
from google.adk.tools.tool_context import ToolContext
import google.genai.types as types

from config import config


# ============================================================
# CONFIG
# ============================================================

os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

TEXT_MODEL = "gemini-2.0-flash"
IMAGE_MODEL = "gemini-2.5-flash-image"


# ============================================================
# IMAGE GENERATION TOOL
# ============================================================

import re

async def generate_image_tool(prompt: str, tool_context: ToolContext) -> dict:
    client = genai.Client()

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[prompt],
    )

    # --------------------------------------------------
    # Extract Brand Name From Prompt
    # --------------------------------------------------
    brand_name_match = re.search(r"(?i)brand name[:\- ]+([A-Za-z0-9 &]+)", prompt)

    if brand_name_match:
        brand_name = brand_name_match.group(1).strip()
    else:
        # fallback if pattern not found
        brand_name = "brand"

    # sanitize filename (remove spaces & special chars)
    brand_name_clean = re.sub(r'[^A-Za-z0-9]+', '_', brand_name)

    filename = f"{brand_name_clean}_ad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    image_bytes = None

    for part in response.parts:
        if part.inline_data:
            image = part.as_image()
            image.save(filename)

            with open(filename, "rb") as f:
                image_bytes = f.read()

    if image_bytes:
        artifact_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png"
        )

        await tool_context.save_artifact(
            filename=filename,
            artifact=artifact_part
        )

    return {
        "status": "success",
        "message": f"Image generated and saved as {filename}"
    }

# async def generate_image_tool(prompt: str, tool_context: ToolContext) -> dict:
#     client = genai.Client()

#     response = client.models.generate_content(
#         model=IMAGE_MODEL,
#         contents=[prompt],
#     )

#     filename = f"brand_ad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
#     image_bytes = None

#     for part in response.parts:
#         if part.inline_data:
#             image = part.as_image()
#             image.save(filename)

#             with open(filename, "rb") as f:
#                 image_bytes = f.read()

#     if image_bytes:
#         artifact_part = types.Part.from_bytes(
#             data=image_bytes,
#             mime_type="image/png"
#         )

#         await tool_context.save_artifact(
#             filename=filename,
#             artifact=artifact_part
#         )

#     return {
#         "status": "success",
#         "message": f"Image generated and saved as {filename}"
#     }

generate_image = FunctionTool(func=generate_image_tool)


# ============================================================
# AGENT 1 — BRAND RESEARCH AGENT
# ============================================================

brand_research_agent = LlmAgent(
    name="brand_research_agent",
    model=TEXT_MODEL,
    instruction="""
You are an expert brand intelligence strategist.

GOAL:
Create a premium advertisement for the company mentioned by the user.

You must dynamically decide search queries using Google Search tool.

Extract:

- Official Brand Name
- Tagline
- Core Product or Service
- Target audience
- Emotional positioning
- Brand color hints (if available)
- Logo description (if available)

Then generate structured output in this exact format:

BRAND_NAME:
...

TAGLINE:
...

AD_HEADLINE:
...

AD_COPY:
...

VISUAL_DIRECTION:
- Brand name placement
- Logo placement suggestion
- Typography style
- Color palette
- Scene concept
""",
    tools=[google_search],
)


# ============================================================
# AGENT 2 — IMAGE CREATIVE DIRECTOR
# ============================================================

image_director_agent = LlmAgent(
    name="image_director_agent",
    model=TEXT_MODEL,
    instruction="""
You are a cinematic AI creative director.

From the previous structured output:

1. Extract BRAND_NAME and VISUAL_DIRECTION.
2. Create a highly detailed image generation prompt.
3. Ensure the brand name is clearly visible in the image.
4. Mention logo placement area.
5. Mention typography style and color palette.
6. Make it look like a premium healthcare advertisement.

IMPORTANT:

After creating the final image prompt,
you MUST call the generate_image tool.

After the tool call,
inform the user that the image is generated and visible above.
""",
    tools=[generate_image],
)


# ============================================================
# ROOT PIPELINE AGENT
# ============================================================

root_agent = SequentialAgent(
    name="dynamic_brand_ad_pipeline",
    sub_agents=[brand_research_agent, image_director_agent],
)


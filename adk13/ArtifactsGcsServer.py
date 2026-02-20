import asyncio
from google.adk.artifacts import GcsArtifactService
import google.genai.types as types
from config import config


async def main():
    # Initialize Artifact Service
    artifact_service = GcsArtifactService(
        bucket_name=config.BUCKET_NAME
    )

    # Identifiers
    app_name = "demo_app"
    user_id = "user_1"
    session_id = "session_1"

    # Content to save
    content = "Hello from GCS Artifact Service!"

    artifact_part = types.Part.from_bytes(
        data=content.encode("utf-8"),
        mime_type="text/plain"
    )

    # ------------------------
    # SAVE ARTIFACT
    # ------------------------
    version = await artifact_service.save_artifact(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        filename="sample.txt",
        artifact=artifact_part
    )

    print("Saved version:", version)

    # ------------------------
    # LOAD ARTIFACT
    # ------------------------
    loaded = await artifact_service.load_artifact(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        filename="sample.txt"
    )

    content_loaded = loaded.inline_data.data.decode("utf-8")
    print("Loaded content:", content_loaded)


# ------------------------
# Execution Block
# ------------------------

# await main() # Jupyter-Lab

if __name__ == "__main__":
    asyncio.run(main())


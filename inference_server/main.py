"""
Inference server - runs on your rented GPU instance, NOT on the Django
host. Django's episodes/services.py calls this over HTTP
(settings.GPU_WORKER_URL) so the heavy model work is fully decoupled
from the orchestration logic.

Two modes:
  --mock   loads no models at all, returns a placeholder image/audio
           instantly. Use this to test the full Django <-> worker
           contract for free, before you've rented any GPU time.
  (default) loads FLUX.2 and Chatterbox for real. Only run this mode on
           a machine with a real GPU - see README for setup.

Run:
    pip install -r requirements.txt
    python main.py --mock              # free, instant, for testing
    python main.py                     # real models, needs a GPU
"""

import argparse
import io
import os

from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import Response
from typing import List, Optional

app = FastAPI(title="AI Video Studio - Inference Server")

def is_mock_mode() -> bool:
    return os.environ.get("INFERENCE_MOCK", "0") == "1"

# ---------------------------------------------------------------------
# Model loading - only happens once, at startup, and only in real mode.
# Kept lazy/guarded so --mock never needs torch/diffusers installed.
# ---------------------------------------------------------------------
_image_pipeline = None
_voice_model = None


def get_image_pipeline():
    global _image_pipeline
    if _image_pipeline is None:
        import torch
        from diffusers import FluxPipeline

        # FLUX.2 (Apache-2.0 licensed open weights). Swap the model id for
        # whichever FLUX.2 variant/checkpoint you settle on.
        _image_pipeline = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.2-dev",
            torch_dtype=torch.bfloat16,
        ).to("cuda")
    return _image_pipeline


def get_voice_model():
    global _voice_model
    if _voice_model is None:
        from chatterbox.tts import ChatterboxTTS

        _voice_model = ChatterboxTTS.from_pretrained(device="cuda")
    return _voice_model


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------

@app.post("/generate-image")
async def generate_image(
    prompt: str = Form(...),
    reference_images: Optional[List[UploadFile]] = File(None),
):
    if is_mock_mode():
        return Response(content=_mock_png_bytes(prompt), media_type="image/png")

    pipeline = get_image_pipeline()
    ref_imgs = []
    if reference_images:
        from PIL import Image
        for uf in reference_images:
            ref_imgs.append(Image.open(io.BytesIO(await uf.read())))

    # FLUX.2 supports multi-reference conditioning for character/scene
    # consistency - check the current diffusers docs for the exact
    # parameter name/signature for your installed version, this is the
    # general shape of the call.
    result = pipeline(
        prompt=prompt,
        reference_images=ref_imgs if ref_imgs else None,
        height=720,
        width=1280,
        num_inference_steps=28,
    )
    image = result.images[0]

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


@app.post("/generate-voice")
async def generate_voice(payload: dict):
    text = payload["text"]
    provider_voice_id = payload.get("provider_voice_id")

    if is_mock_mode():
        return Response(content=_mock_audio_bytes(text), media_type="audio/mpeg")

    model = get_voice_model()
    # provider_voice_id maps to a stored reference audio sample for that
    # preset/cloned voice - see inference_server/voice_presets/ and adapt
    # this lookup to however you end up storing preset samples.
    audio_prompt_path = f"voice_presets/{provider_voice_id}.wav"
    wav = model.generate(text, audio_prompt_path=audio_prompt_path)

    buf = io.BytesIO()
    import torchaudio
    torchaudio.save(buf, wav, model.sr, format="mp3")
    return Response(content=buf.getvalue(), media_type="audio/mpeg")


# ---------------------------------------------------------------------
# Mock helpers - no ML dependencies required.
# ---------------------------------------------------------------------

def _mock_png_bytes(prompt: str) -> bytes:
    from PIL import Image, ImageDraw
    import hashlib

    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:6], 16)
    color = (seed % 200 + 20, (seed // 200) % 200 + 20, (seed // 40000) % 200 + 20)
    img = Image.new("RGB", (1280, 720), color)
    draw = ImageDraw.Draw(img)
    draw.text((40, 40), f"[MOCK IMAGE]\n{prompt[:200]}", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _mock_audio_bytes(text: str) -> bytes:
    import subprocess
    import tempfile

    duration = max(0.8, min(len(text) / 15, 8.0))  # rough words-per-second guess
    with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=300:duration={duration}",
             "-ar", "22050", f.name],
            capture_output=True, check=True,
        )
        f.seek(0)
        return f.read()


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    if args.mock:
        os.environ["INFERENCE_MOCK"] = "1"

    uvicorn.run(app, host="0.0.0.0", port=args.port)

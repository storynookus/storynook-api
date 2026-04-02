import base64
import concurrent.futures
import json
import os
import re
import time
import traceback
from typing import Any

import google.auth
import google.auth.transport.requests
import requests as http_requests
import vertexai
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from vertexai.generative_models import GenerativeModel, Part
from app.api.deps import require_api_token

router = APIRouter(prefix="/template", tags=["Template"])

router = APIRouter(tags=["Story"])

GCP_PROJECT = os.environ.get("GCP_PROJECT", "storynook-491620")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-east1")
IMAGEN_LOCATION = os.environ.get("IMAGEN_LOCATION", "us-central1")
IMAGE_GENERATION_DELAY_SECONDS = float(os.environ.get("IMAGE_GENERATION_DELAY_SECONDS", "3"))
IMAGE_WORKERS = int(os.environ.get("IMAGE_WORKERS", "1"))

MORAL_LESSONS = {
    "sharing": "learning that sharing with others makes everyone happier",
    "kindness": "discovering that small acts of kindness change the world",
    "brushing_teeth": "learning that taking care of yourself keeps you strong and healthy",
    "collaboration": "finding out that working together achieves more than working alone",
    "courage": "discovering that being brave means doing things even when you are scared",
    "honesty": "learning that telling the truth always leads to better outcomes",
    "patience": "discovering that good things come to those who wait and persist",
}

_MODEL: GenerativeModel | None = None


class KidData(BaseModel):
    name: str | None = None
    photo: str | None = None


class GenerateStoryRequest(BaseModel):
    childName: str = "Alex"
    childAge: str = "7"
    interests: str = "adventure"
    moral: str = "kindness"
    customPrompt: str = ""
    language: str = "English"
    photoBase64: str | None = None
    pageCount: int = Field(default=7, ge=1, le=30)
    kidsData: list[KidData] = Field(default_factory=list)


class ContinueStoryRequest(BaseModel):
    currentPage: int = 3
    currentText: str = ""
    kidInput: str = ""
    childName: str = "Alex"
    moral: str = "kindness"


def _get_model() -> GenerativeModel:
    global _MODEL
    if _MODEL is None:
        vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
        _MODEL = GenerativeModel("gemini-2.5-flash")
    return _MODEL


def _strip_data_uri_prefix(value: str) -> str:
    if "," in value and value.lower().startswith("data:"):
        return value.split(",", 1)[1]
    return value


def get_access_token() -> str:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


def generate_image_with_imagen(prompt: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            token = get_access_token()
            url = (
                "https://"
                f"{IMAGEN_LOCATION}-aiplatform.googleapis.com/v1/projects/{GCP_PROJECT}/locations/"
                f"{IMAGEN_LOCATION}/publishers/google/models/imagen-4.0-generate-001:predict"
            )
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "4:3",
                    "safetySetting": "block_some",
                    "personGeneration": "allow_all",
                },
            }
            response = http_requests.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            if "predictions" in result and len(result["predictions"]) > 0:
                b64 = result["predictions"][0].get("bytesBase64Encoded")
                if b64:
                    return b64
            print(f"Empty prediction attempt {attempt + 1}: {result}", flush=True)
        except Exception as exc:
            print(f"Imagen attempt {attempt + 1} failed: {exc}", flush=True)
        time.sleep(5)
    return None


def get_character_description(photo_base64: str) -> str:
    try:
        cleaned = _strip_data_uri_prefix(photo_base64)
        prompt = (
            "Look at this child photo very carefully. Describe this specific child to recreate them as a cartoon character. "
            "Include: (1) exact skin tone, (2) exact hair color, (3) exact hair length and texture (curly/straight/wavy/coily), "
            "(4) approximate age, (5) any distinctive features. "
            "Write ONE illustration prompt in this exact format: "
            '"a [age]-year-old child cartoon character with [exact skin tone] skin, [exact hair description], [eye color] eyes, Pixar animation style, consistent character design". '
            "Be very specific about hair. This MUST look like the child in the photo. Only output the illustration prompt."
        )
        parts = [prompt, Part.from_data(data=base64.b64decode(cleaned), mime_type="image/jpeg")]
        response = _get_model().generate_content(parts)
        desc = response.text.strip()
        print(f"Character desc: {desc}", flush=True)
        return desc
    except Exception as exc:
        print(f"Appearance extraction failed: {exc}", flush=True)
        return "a young child cartoon character in Pixar animation style"


def build_story_structure(page_count: int, names: str, moral_description: str) -> str:
    intro_end = 1
    rising_end = max(2, round(page_count * 0.35))
    climax_page = round(page_count * 0.55)
    resolve_end = round(page_count * 0.85)
    ending_page = page_count

    structure = f"Page 1: Introduction - meet {names} and their magical world\n"
    if rising_end > intro_end:
        structure += f"Pages 2-{rising_end}: Rising action - exciting adventure begins\n"
    structure += f"Page {climax_page}: Climax - the biggest challenge moment\n"
    if resolve_end > climax_page:
        structure += (
            f"Pages {climax_page + 1}-{resolve_end}: Resolution - solving it and learning "
            f"{moral_description}\n"
        )
    structure += f"Page {ending_page}: Happy ending - celebration and reflection\n"
    return structure


def _extract_json_array(raw_text: str) -> list[dict[str, Any]]:
    raw = raw_text.strip()
    raw = re.sub(r"```json\n?", "", raw)
    raw = re.sub(r"```\n?", "", raw)
    raw = raw.strip()
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise json.JSONDecodeError("Model did not return a JSON array", raw, 0)
    return parsed


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    raw = raw_text.strip()
    raw = re.sub(r"```json\n?|```\n?", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    raw = raw[start:end]
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("Model did not return a JSON object", raw, 0)
    return parsed


@router.get("/health", status_code=status.HTTP_200_OK, dependencies=[Depends(require_api_token)])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "StoryNook API", "project": GCP_PROJECT}

@router.get("/endpoints", status_code=status.HTTP_200_OK, dependencies=[Depends(require_api_token)])
def get_endpoints() -> dict[str, str]:
    return {
        'generate_story': '/api/v1/story/generate-story',
        'continue_story': '/api/v1/story/continue-story',
    }

@router.post("/generate-story", status_code=status.HTTP_200_OK, dependencies=[Depends(require_api_token)])
def generate_story(payload: GenerateStoryRequest) -> dict[str, Any]:
    try:
        print(f"Received story generation request: {payload}", flush=True)
        child_name = payload.childName
        child_age = payload.childAge
        interests = payload.interests
        moral_key = payload.moral
        custom_prompt = payload.customPrompt
        language = payload.language
        photo_base64 = payload.photoBase64
        page_count = payload.pageCount
        kids_data = payload.kidsData
        is_multi = len(kids_data) > 1

        moral_description = MORAL_LESSONS.get(moral_key, moral_key)

        if is_multi:
            names = " & ".join(k.name or f"Child {i + 1}" for i, k in enumerate(kids_data))
            character_descs: list[str] = []
            for i, kid in enumerate(kids_data):
                kid_name = kid.name or f"Child {i + 1}"
                if kid.photo:
                    desc = get_character_description(kid.photo)
                    character_descs.append(f"{kid_name}: {desc}")
                else:
                    character_descs.append(f"{kid_name}: a cute Pixar animated cartoon child")

            characters_instruction = (
                f"MULTIPLE CHARACTERS: This story features {len(kids_data)} children as the main heroes:\n"
                f"{chr(10).join(character_descs)}\n"
                "Each character must appear in at least half the illustrations. "
                "They should appear together in most scenes. Each must look exactly as described above."
            )
        else:
            names = child_name
            if photo_base64:
                character_desc = get_character_description(photo_base64)
            else:
                character_desc = (
                    "a cute Pixar animated cartoon child character with big expressive eyes and a warm smile"
                )
            characters_instruction = (
                f"MAIN CHARACTER: {character_desc} named {child_name}. "
                "This EXACT character must appear in EVERY scene."
            )

        print(f"Generating {page_count} pages for: {names}", flush=True)
        story_structure = build_story_structure(page_count, names, moral_description)

        system_prompt = f"""You are StoryNook, a magical AI storyteller.

Generate a {page_count}-page storybook JSON for {names}, age {child_age}.
Topic: {interests}
Moral: {moral_description}
{f"Notes: {custom_prompt}" if custom_prompt else ""}
Language: {language}

Return ONLY a JSON array. No markdown. No explanation. Just the array.

Each object must have exactly these keys:
- "page": number 1 to {page_count}
- "text": 3-5 vivid engaging sentences written beautifully for a {child_age}-year-old. Use descriptive language, emotion, and wonder.
- "image_prompt": Pixar-style cartoon illustration. {characters_instruction} Scene: [describe what is happening on this page in vivid detail]. Colorful warm golden lighting, whimsical storybook style, safe for children, highly detailed. Characters must look identical across all pages. IMPORTANT: single scene only, no text overlays, no captions, no character name labels, no split panels, one unified illustration. Style must be Pixar 3D animated cartoon, NOT realistic, NOT photographic, NOT a real person, cartoon characters only.

Story structure to follow:
{story_structure}

Return ONLY the JSON array."""

        response = _get_model().generate_content(system_prompt)
        pages = _extract_json_array(response.text)

        def generate_page_image(page_data: dict[str, Any]) -> dict[str, Any]:
            time.sleep(IMAGE_GENERATION_DELAY_SECONDS)
            image_b64 = generate_image_with_imagen(str(page_data.get("image_prompt", "")))
            return {
                "page": page_data["page"],
                "text": page_data["text"],
                "image_prompt": page_data.get("image_prompt", ""),
                "image_base64": image_b64,
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, IMAGE_WORKERS)) as executor:
            story_with_images = list(executor.map(generate_page_image, pages))

        story_with_images.sort(key=lambda x: x["page"])

        return {
            "success": True,
            "story": story_with_images,
            "childName": names,
            "moral": moral_key,
            "language": language,
        }

    except json.JSONDecodeError as exc:
        print(f"JSON parse error: {exc}", flush=True)
        return {"success": False, "error": "Story generation failed - invalid format"}
    except Exception as exc:
        print(f"Error: {exc}", flush=True)
        print(traceback.format_exc(), flush=True)
        return {"success": False, "error": str(exc)}


@router.post("/continue-story", status_code=status.HTTP_200_OK, dependencies=[Depends(require_api_token)])
def continue_story(payload: ContinueStoryRequest) -> dict[str, Any]:
    try:
        print(f"Received story generation request: {payload}", flush=True)
        current_page = payload.currentPage
        current_text = payload.currentText
        kid_input = payload.kidInput
        child_name = payload.childName
        moral_key = payload.moral
        moral_description = MORAL_LESSONS.get(moral_key, moral_key)

        prompt = (
            f'Continue this childrens story for {child_name}. '
            f'Page {current_page}: "{current_text}" '
            f'Child idea: "{kid_input}" '
            f'Moral: {moral_description} '
            'Return ONLY JSON: {"text": "3-4 sentences", "image_prompt": '
            '"Pixar cartoon illustration, colorful, warm lighting, storybook style, cartoon characters only, NOT realistic"}'
        )

        response = _get_model().generate_content(prompt)
        page_data = _extract_json_object(response.text)
        image_b64 = generate_image_with_imagen(str(page_data.get("image_prompt", "")))

        return {
            "success": True,
            "text": page_data.get("text", ""),
            "image_base64": image_b64,
        }

    except Exception as exc:
        print(traceback.format_exc(), flush=True)
        return {"success": False, "error": str(exc)}
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import re
from typing import Optional, Callable, Dict, Any

import dotenv

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

LLM_BACKEND = os.environ.get("LLM_BACKEND", "auto").lower()

_gemini_utils = None
_openai_utils = None
_pdf_utils = None


def _import_gemini():
    global _gemini_utils
    if _gemini_utils is None:
        import utils.gemini_utils as _m
        _gemini_utils = _m
    return _gemini_utils


def _import_openai():
    global _openai_utils
    if _openai_utils is None:
        import utils.openai_utils as _m
        _openai_utils = _m
    return _openai_utils


def _import_pdf():
    global _pdf_utils
    if _pdf_utils is None:
        import utils.pdf_utils as _m
        _pdf_utils = _m
    return _pdf_utils


def _is_openai_backend(model_name: str) -> bool:
    if LLM_BACKEND == "openai_compatible":
        return True
    if LLM_BACKEND == "gemini":
        return False
    # auto: fall back to model-name heuristic
    return any(k in model_name.lower() for k in ("gpt", "o1", "o3"))


def identity_parse(response: str):
    return response


def parse_latex_results(response: str) -> str:
    """Extract LaTeX code from LLM response (generic, works with any backend)."""
    match = re.search(r"```latex\s*(.*?)\s*```", response.strip(), re.DOTALL)
    if match:
        return match.group(1)
    return response


def parse_json_latex_response(response_text: str) -> str:
    """Extract JSON worklog and LaTeX code from LLM response (generic)."""
    result = {"json": None, "latex": None}
    json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    if json_match:
        try:
            result["json"] = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            result["json"] = {"error": "Invalid JSON format returned"}
    latex_match = re.search(r"```latex\s*(.*?)\s*```", response_text, re.DOTALL)
    if latex_match:
        result["latex"] = latex_match.group(1)
    return json.dumps(result)


def get_llm_parser(model_name: str, return_json: bool = True) -> Callable:
    if not return_json:
        return identity_parse

    if _is_openai_backend(model_name):
        return _import_openai().parse_openai_json_results
    else:
        return _import_gemini().parse_gemini_json_results


def call_llm_with_text_prompt(
    prompt: str,
    model_name: str,
    generation_configs: Optional[Dict[str, Any]] = None,
    check_parsed_response_not_none: bool = True,
    return_json: bool = True,
    result_parsing_func: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Unified function to call either Gemini or OpenAI models based on the model_name.
    """
    parser = (
        result_parsing_func
        if result_parsing_func is not None
        else get_llm_parser(model_name, return_json)
    )

    if generation_configs is None:
        generation_configs = {}

    if _is_openai_backend(model_name):
        system_prompt = None
        configs_for_openai = dict(generation_configs) if generation_configs else {}
        if "system_instruction" in configs_for_openai:
            system_prompt = configs_for_openai.pop("system_instruction")
        if "temperature" in configs_for_openai:
            configs_for_openai.pop("temperature")

        response_dict = _import_openai().call_openai_models_with_text_prompt(
            prompt=prompt,
            model_name=model_name,
            generation_configs=configs_for_openai,
            result_parsing_func=parser,
            check_parsed_response_not_none=check_parsed_response_not_none,
            system_prompt=system_prompt,
        )
        return response_dict
    else:
        response_dict = _import_gemini().call_gemini_with_text_prompt(
            prompt=prompt,
            model_name=model_name,
            generation_configs=generation_configs,
            result_parsing_func=parser,
            check_parsed_response_not_none=check_parsed_response_not_none,
        )
        return response_dict


def call_llm_with_images(
    prompt: str,
    images: list[str],
    model_name: str,
    generation_configs: Optional[Dict[str, Any]] = None,
    check_parsed_response_not_none: bool = True,
    return_json: bool = True,
    result_parsing_func: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Unified function to call either Gemini or OpenAI models with images based on the model_name.
    """
    parser = (
        result_parsing_func
        if result_parsing_func is not None
        else get_llm_parser(model_name, return_json)
    )

    if generation_configs is None:
        generation_configs = {}

    if _is_openai_backend(model_name):
        system_prompt = None
        configs_for_openai = dict(generation_configs) if generation_configs else {}
        if "system_instruction" in configs_for_openai:
            system_prompt = configs_for_openai.pop("system_instruction")
        if "temperature" in configs_for_openai:
            configs_for_openai.pop("temperature")

        content = [{"type": "text", "text": prompt}]
        for image_path in images:
            content.extend(_import_openai().get_openai_image_part_from_path(image_path))

        response_dict = _import_openai().call_openai_models_with_content(
            content=content,
            model_name=model_name,
            generation_configs=configs_for_openai,
            result_parsing_func=parser,
            check_parsed_response_not_none=check_parsed_response_not_none,
            system_prompt=system_prompt,
        )
        return response_dict
    else:
        response_dict = _import_gemini().call_gemini_with_images(
            prompt=prompt,
            images=images,
            model_name=model_name,
            generation_configs=generation_configs,
            result_parsing_func=parser,
            check_parsed_response_not_none=check_parsed_response_not_none,
        )
        return response_dict


def call_llm_with_pdf(
    pdf_path: str,
    prompt: str,
    model_name: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.7,
    check_parsed_response_not_none: bool = True,
    return_json: bool = True,
    result_parsing_func: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Unified function to evaluate a PDF.
    Passes raw PDF bytes to Gemini, and extracted text to OpenAI.
    """
    parser = (
        result_parsing_func
        if result_parsing_func is not None
        else get_llm_parser(model_name, return_json)
    )

    if _is_openai_backend(model_name):
        paper_text = _import_pdf().load_paper(pdf_path, min_size=100)
        full_prompt = f"Paper Content:\n{paper_text}\n\nTask:\n{prompt}"

        generation_configs = {}
        response_dict = _import_openai().call_openai_models_with_text_prompt(
            prompt=full_prompt,
            model_name=model_name,
            generation_configs=generation_configs,
            result_parsing_func=parser,
            check_parsed_response_not_none=check_parsed_response_not_none,
            system_prompt=system_instruction,
        )
        return response_dict
    else:
        from google.genai import types

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        contents = [
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            types.Part.from_text(text=prompt),
        ]

        generation_configs = {"temperature": temperature}
        if system_instruction is not None:
            generation_configs["system_instruction"] = system_instruction

        response_dict = _import_gemini().call_gemini_with_contents(
            contents=contents,
            model_name=model_name,
            generation_configs=generation_configs,
            result_parsing_func=parser,
            check_parsed_response_not_none=check_parsed_response_not_none,
        )
        return response_dict

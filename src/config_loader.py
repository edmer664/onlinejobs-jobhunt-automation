"""
Configuration Loader Module for Job Hunt Open-Source Platform.
Decouples candidate credentials, role categories, skill dictionaries, and logistics
from core engine files. Supports YAML and JSON with automatic fallback to profile.example.json.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("config_loader")

_CACHED_PROFILE: Optional[Dict[str, Any]] = None


def get_project_root() -> str:
    """Returns absolute path to the project root directory."""
    # This file is in src/, so project root is one level up
    src_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(src_dir)
    return root_dir


def get_config_dir() -> str:
    """Returns absolute path to the config/ directory."""
    return os.path.join(get_project_root(), "config")


def find_profile_file(explicit_path: Optional[str] = None) -> Tuple[str, bool]:
    """
    Locates the active candidate profile configuration file.
    
    Search order:
    1. Explicit path parameter (if given)
    2. config/profile.yaml
    3. config/profile.yml
    4. config/profile.json
    5. Fallback: config/profile.example.yaml
    6. Fallback: config/profile.example.json

    Returns:
        Tuple[str, bool]: (resolved_filepath, is_fallback_boolean)
    """
    if explicit_path:
        if os.path.exists(explicit_path):
            return os.path.abspath(explicit_path), False
        else:
            raise FileNotFoundError(f"Specified profile configuration not found: {explicit_path}")

    cfg_dir = get_config_dir()
    primary_candidates = [
        os.path.join(cfg_dir, "profile.yaml"),
        os.path.join(cfg_dir, "profile.yml"),
        os.path.join(cfg_dir, "profile.json"),
    ]

    for path in primary_candidates:
        if os.path.exists(path):
            return os.path.abspath(path), False

    fallback_candidates = [
        os.path.join(cfg_dir, "profile.example.yaml"),
        os.path.join(cfg_dir, "profile.example.json"),
    ]

    for path in fallback_candidates:
        if os.path.exists(path):
            return os.path.abspath(path), True

    raise FileNotFoundError(
        f"No profile configuration found in {cfg_dir}. Expected profile.yaml, profile.json, "
        f"or profile.example.json."
    )


def _load_raw_config(file_path: str) -> Dict[str, Any]:
    """Reads and parses YAML or JSON file into a Python dict."""
    ext = os.path.splitext(file_path)[1].lower()

    with open(file_path, "r", encoding="utf-8") as f:
        if ext in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    return data
            except ImportError:
                logger.warning("PyYAML is not installed. Attempting JSON parsing or fallback.")
            except Exception as e:
                logger.error(f"Error parsing YAML config at {file_path}: {e}")

        # If JSON or YAML failed/fallback
        f.seek(0)
        try:
            return json.load(f)
        except Exception as e:
            logger.error(f"Error parsing configuration file as JSON at {file_path}: {e}")
            raise


def load_profile(config_path: Optional[str] = None, force_reload: bool = False) -> Dict[str, Any]:
    """
    Loads candidate profile data. Caches in memory unless force_reload=True.
    Emits a helpful warning banner if falling back to profile.example.*
    """
    global _CACHED_PROFILE

    if _CACHED_PROFILE is not None and not force_reload and config_path is None:
        return _CACHED_PROFILE

    path, is_fallback = find_profile_file(config_path)

    if is_fallback:
        logger.warning(
            "\n" + "=" * 70 + "\n"
            f"[NOTICE] Running with default template profile: {os.path.basename(path)}\n"
            "To personalize matching, copy config/profile.example.yaml to config/profile.yaml\n"
            "and edit your candidate facts and target roles.\n"
            + "=" * 70 + "\n"
        )

    raw_data = _load_raw_config(path)
    _CACHED_PROFILE = raw_data
    return _CACHED_PROFILE


def get_candidate_profile(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns complete candidate profile and system settings conforming to
    config/profile.schema.json.
    """
    return load_profile(config_path)


def get_role_categories(config_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Returns role categories mapping for evaluator.py.
    Format:
    {
        "Category Name": {
            "title_keywords": [r"..."],
            "base_fit": 48,
            "selling_point": "..."
        }
    }
    """
    profile = load_profile(config_path)
    return profile.get("role_categories", {})


def get_candidate_skills(config_path: Optional[str] = None) -> List[Tuple[str, List[str], int]]:
    """
    Returns candidate skills normalized as:
    List of (label, [patterns], weight) for evaluator.py matching loop.
    """
    profile = load_profile(config_path)
    raw_skills = profile.get("candidate_skills", [])
    normalized: List[Tuple[str, List[str], int]] = []

    for item in raw_skills:
        if isinstance(item, dict):
            label = item.get("name") or item.get("label", "General Skill")
            patterns = item.get("patterns", [])
            weight = int(item.get("weight", 4))
            normalized.append((label, patterns, weight))
        elif isinstance(item, (list, tuple)) and len(item) >= 3:
            normalized.append((str(item[0]), list(item[1]), int(item[2])))

    return normalized


def get_potential_gaps(config_path: Optional[str] = None) -> List[Tuple[str, List[str]]]:
    """
    Returns potential gaps normalized as:
    List of (label, [patterns]) for evaluator.py gap detection.
    """
    profile = load_profile(config_path)
    raw_gaps = profile.get("potential_gaps", [])
    normalized: List[Tuple[str, List[str]]] = []

    for item in raw_gaps:
        if isinstance(item, dict):
            label = item.get("name") or item.get("label", "Tool Gap")
            patterns = item.get("patterns", [])
            normalized.append((label, patterns))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            normalized.append((str(item[0]), list(item[1])))

    return normalized


def get_hard_mismatches(config_path: Optional[str] = None) -> List[str]:
    """Returns list of regex patterns for hard mismatch dealbreakers."""
    profile = load_profile(config_path)
    return profile.get("hard_mismatches", [])


def get_red_flags(config_path: Optional[str] = None) -> List[Tuple[str, List[str]]]:
    """
    Returns red flag patterns normalized as:
    List of (label, [patterns]) for evaluator.py red flag detection.
    """
    profile = load_profile(config_path)
    raw_flags = profile.get("red_flags", [])
    normalized: List[Tuple[str, List[str]]] = []

    for item in raw_flags:
        if isinstance(item, dict):
            label = item.get("name") or item.get("label", "Red Flag")
            patterns = item.get("patterns", [])
            normalized.append((label, patterns))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            normalized.append((str(item[0]), list(item[1])))

    return normalized

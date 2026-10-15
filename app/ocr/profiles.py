from typing import Dict, Any

OCR_PROFILES: Dict[str, Dict[str, Any]] = {
    "default": {
        "text_threshold": 0.6,
        "link_threshold": 0.4,
        "low_text": 0.4,
        "canvas_size": 2560,
        "mag_ratio": 1.0,
        "contrast_ths": 0.1,
        "adjust_contrast": 0.5,
    },
    "small_text": {
        "text_threshold": 0.4,
        "link_threshold": 0.3,
        "low_text": 0.3,
        "canvas_size": 3200,
        "mag_ratio": 2.0,
        "contrast_ths": 0.05,
        "adjust_contrast": 0.7,
    },
    "low_contrast": {
        "text_threshold": 0.45,
        "link_threshold": 0.35,
        "low_text": 0.35,
        "canvas_size": 2560,
        "mag_ratio": 1.5,
        "contrast_ths": 0.02,
        "adjust_contrast": 0.9,
    },
    "blurred": {
        "text_threshold": 0.35,
        "link_threshold": 0.3,
        "low_text": 0.25,
        "canvas_size": 2800,
        "mag_ratio": 1.7,
        "contrast_ths": 0.08,
        "adjust_contrast": 0.8,
    },
    "field_crop_numeric": {
        "text_threshold": 0.4,
        "link_threshold": 0.3,
        "low_text": 0.3,
        "canvas_size": 1800,
        "mag_ratio": 2.0,
        "allowlist": "0123456789.,/-: ",
        "adjust_contrast": 0.7,
    },
    "field_crop_alpha": {
        "text_threshold": 0.4,
        "link_threshold": 0.3,
        "low_text": 0.3,
        "canvas_size": 1800,
        "mag_ratio": 2.0,
        "allowlist": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,'-",
        "adjust_contrast": 0.7,
    }
}

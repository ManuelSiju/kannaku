import cv2
import numpy as np
import pytest

from app.providers import ocr


def png_bytes(width=400, height=120) -> bytes:
    img = np.full((height, width, 3), 255, np.uint8)
    cv2.putText(img, "Premium 50000", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


@pytest.fixture(autouse=True)
def clear_lang_cache():
    ocr.available_langs.cache_clear()
    yield
    ocr.available_langs.cache_clear()


def test_preprocess_upscales_and_binarises():
    out = ocr.preprocess(png_bytes())
    assert out.shape[1] == ocr.MIN_WIDTH
    assert set(np.unique(out)) <= {0, 255}


def test_preprocess_rejects_garbage():
    with pytest.raises(ValueError):
        ocr.preprocess(b"not an image")


def test_mal_missing_falls_back_to_eng(monkeypatch, caplog):
    monkeypatch.setattr(ocr.pytesseract, "get_languages", lambda config="": ["eng", "osd"])
    assert ocr.resolve_langs("eng+mal") == "eng"
    assert "mal" in caplog.text


def test_tesseract_missing_raises_clear_error(monkeypatch):
    def boom(config=""):
        raise ocr.pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(ocr.pytesseract, "get_languages", boom)
    with pytest.raises(ocr.OcrUnavailable, match="apt install"):
        ocr.resolve_langs("eng")


def test_ocr_image_with_mocked_tesseract(monkeypatch, settings):
    monkeypatch.setattr(ocr.pytesseract, "get_languages", lambda config="": ["eng", "mal"])
    monkeypatch.setattr(
        ocr.pytesseract,
        "image_to_data",
        lambda img, lang, output_type: {"text": ["Premium", "50000", ""], "conf": [90, 80, -1]},
    )
    monkeypatch.setattr(ocr.pytesseract, "image_to_string", lambda img, lang: "Premium 50000\n")
    r = ocr.ocr_image(png_bytes(), settings)
    assert r.text == "Premium 50000"
    assert r.mean_confidence == 85.0
    assert r.langs == "eng+mal"
    assert [w.text for w in r.words] == ["Premium", "50000"]

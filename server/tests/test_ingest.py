import io

import docx

from app.config import SERVER_ROOT
from app.pipeline.ingest import Upload, ingest
from tests.fakes import FakeSTT


async def test_pdf_text_layer_pages():
    pdf = (SERVER_ROOT / "demo_assets" / "kanakavalli_brochure.pdf").read_bytes()
    ing = await ingest(
        text="Is this good?", audio=None, files=[Upload(filename="b.pdf", data=pdf, mime="application/pdf")], stt=None
    )
    assert [p.source for p in ing.pages] == ["page_1", "page_2", "page_3"]
    assert "Bonus rates are not guaranteed" in ing.pages[2].text and ing.pages[0].image is None
    assert ing.transcript == "Is this good?"


async def test_docx_and_text_and_audio():
    d = docx.Document()
    d.add_paragraph("Loan amount: Rs. 1,00,000")
    buf = io.BytesIO()
    d.save(buf)
    ing = await ingest(
        text="typed part",
        audio=Upload(filename="a.wav", data=b"x", mime="audio/wav"),
        files=[
            Upload(filename="o.docx", data=buf.getvalue(), mime=""),
            Upload(filename="t.txt", data=b"hello", mime="text/plain"),
        ],
        stt=FakeSTT("spoken part"),
    )
    assert ing.transcript == "spoken part typed part"
    assert [p.kind for p in ing.pages] == ["docx", "text"] and "1,00,000" in ing.pages[0].text


async def test_stt_failure_is_reported_not_raised():
    class Broken(FakeSTT):
        async def transcribe(self, audio_bytes, mime):
            raise RuntimeError("mic")

    ing = await ingest(text=None, audio=Upload(filename="a", data=b"", mime="audio/wav"), files=[], stt=Broken(""))
    assert ing.problems and "stt" in ing.problems[0]

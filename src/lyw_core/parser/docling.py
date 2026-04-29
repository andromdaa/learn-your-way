from pathlib import Path

from docling.datamodel.accelerator_options import (
    AcceleratorDevice,
    AcceleratorOptions,
)
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.document import DocItem

from lyw_core.parser.models import ParsedBlock, ParsedDocument
from lyw_core.settings import Settings


def accelerator_from_settings(settings: Settings) -> AcceleratorOptions:
    return AcceleratorOptions(device=settings.docling_device)


class DoclingParser:
    def __init__(
        self,
        accelerator_options: AcceleratorOptions | None = None,
    ) -> None:
        opts = accelerator_options or AcceleratorOptions(device=AcceleratorDevice.AUTO)
        pdf_options = PdfPipelineOptions(accelerator_options=opts)
        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            },
        )

    def parse(self, path: Path) -> ParsedDocument:
        result = self._converter.convert(str(path))
        doc = result.document

        text_parts: list[str] = []
        blocks: list[ParsedBlock] = []
        cursor = 0

        for item, _level in doc.iterate_items():
            if not isinstance(item, DocItem):
                continue
            text: str = getattr(item, "text", None) or ""
            if not text:
                continue

            page_number = 1
            prov = getattr(item, "prov", None)
            if prov:
                page_number = prov[0].page_no

            block_type = str(item.label)
            block_id = str(item.self_ref)

            char_start = cursor
            char_end = cursor + len(text)

            blocks.append(
                ParsedBlock(
                    block_id=block_id,
                    page_number=page_number,
                    block_type=block_type,
                    text=text,
                    char_start=char_start,
                    char_end=char_end,
                )
            )
            text_parts.append(text)
            cursor = char_end + 1  # +1 for the \n separator

        full_text = "\n".join(text_parts)
        page_count = len(doc.pages)
        if not page_count and blocks:
            page_count = max(b.page_number for b in blocks)

        return ParsedDocument(
            source_path=str(path),
            text=full_text,
            blocks=blocks,
            page_count=max(page_count, 1),
        )

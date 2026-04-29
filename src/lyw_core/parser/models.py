from pydantic import BaseModel


class ParsedBlock(BaseModel):
    block_id: str
    page_number: int
    block_type: str
    text: str
    char_start: int
    char_end: int


class ParsedDocument(BaseModel):
    source_path: str
    text: str
    blocks: list[ParsedBlock]
    page_count: int

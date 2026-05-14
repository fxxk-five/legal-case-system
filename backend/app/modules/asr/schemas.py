from pydantic import BaseModel


class ASRTranscriptionRead(BaseModel):
    text: str

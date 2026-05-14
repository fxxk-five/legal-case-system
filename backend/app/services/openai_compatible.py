"""Compatibility exports for the LLM provider adapter."""

from app.integrations.llm.service import OpenAICompatibleProvider, ProviderReply

__all__ = ["OpenAICompatibleProvider", "ProviderReply"]

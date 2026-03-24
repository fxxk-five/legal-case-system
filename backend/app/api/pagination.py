from __future__ import annotations

from dataclasses import dataclass

from fastapi import status

from app.core.errors import AppError, ErrorCode


@dataclass(frozen=True)
class PaginationParams:
    page: int
    page_size: int
    skip: int
    limit: int
    source: str


def resolve_pagination_params(
    *,
    page: int | None,
    page_size: int | None,
    skip: int | None,
    limit: int | None,
    default_page: int = 1,
    default_page_size: int = 20,
) -> PaginationParams:
    has_standard = page is not None or page_size is not None
    has_legacy = skip is not None or limit is not None

    resolved_page = page if page is not None else default_page
    resolved_page_size = page_size if page_size is not None else default_page_size
    resolved_skip = skip if skip is not None else 0
    resolved_limit = limit if limit is not None else default_page_size

    if has_standard and has_legacy:
        expected_skip = (resolved_page - 1) * resolved_page_size
        expected_limit = resolved_page_size
        if resolved_skip != expected_skip or resolved_limit != expected_limit:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.VALIDATION_ERROR,
                message="Conflicting pagination parameters. Use either page/page_size or skip/limit.",
                detail={
                    "page": resolved_page,
                    "page_size": resolved_page_size,
                    "skip": resolved_skip,
                    "limit": resolved_limit,
                    "expected_skip": expected_skip,
                    "expected_limit": expected_limit,
                },
            )
        source = "mixed"
        return PaginationParams(
            page=resolved_page,
            page_size=resolved_page_size,
            skip=resolved_skip,
            limit=resolved_limit,
            source=source,
        )

    if has_standard:
        return PaginationParams(
            page=resolved_page,
            page_size=resolved_page_size,
            skip=(resolved_page - 1) * resolved_page_size,
            limit=resolved_page_size,
            source="standard",
        )

    if has_legacy:
        derived_page = (resolved_skip // resolved_limit) + 1
        return PaginationParams(
            page=derived_page,
            page_size=resolved_limit,
            skip=resolved_skip,
            limit=resolved_limit,
            source="legacy",
        )

    return PaginationParams(
        page=default_page,
        page_size=default_page_size,
        skip=(default_page - 1) * default_page_size,
        limit=default_page_size,
        source="default",
    )

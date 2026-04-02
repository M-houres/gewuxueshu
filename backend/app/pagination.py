from math import ceil


def paginate(total: int, page: int, page_size: int) -> dict:
    pages = ceil(total / page_size) if total > 0 else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
    }

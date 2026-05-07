"""Pexels 图片搜索服务（替代/补充 Unsplash）"""

import logging
from dataclasses import dataclass

import httpx

from app.config import PEXELS_API_KEY
from app.services.unsplash_service import _search_queries

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageCandidate:
    url: str
    thumb_url: str
    raw_url: str
    author: str
    likes: int


async def _search_photos(query: str, per_page: int = 5) -> list[dict]:
    """执行 Pexels 搜索，返回结果列表。"""
    if not PEXELS_API_KEY:
        return []

    url = "https://api.pexels.com/v1/search"
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "landscape",
    }
    headers = {
        "Authorization": PEXELS_API_KEY,
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get("photos", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.error("Pexels API 已达速率限制")
            else:
                logger.warning("Pexels HTTP %s for %r: %s",
                               e.response.status_code, query, e)
            return []
        except httpx.RequestError as e:
            logger.warning("Pexels 请求失败 %r: %s", query, e)
            return []


def _pick_best(results: list[dict]) -> dict | None:
    """从多个候选中选第一个（Pexels 按相关度排序返回）。"""
    if not results:
        return None
    return results[0]


async def fetch_question_image(query: str) -> str | None:
    """根据题目内容搜索 Pexels，取最相关的一张。"""
    for search_query in _search_queries(query):
        results = await _search_photos(search_query, per_page=5)
        best = _pick_best(results)
        if best:
            return best["src"]["large"]
    return None


async def fetch_option_images(options: list[str]) -> list[str | None]:
    """为每个选项搜索图片，各取最相关的一张。"""
    if not PEXELS_API_KEY:
        return [None] * len(options)

    import asyncio

    async def _fetch_one(opt: str) -> str | None:
        for search_query in _search_queries(opt):
            results = await _search_photos(search_query, per_page=5)
            best = _pick_best(results)
            if best:
                return best["src"]["medium"]
        return None

    tasks = [_fetch_one(opt) for opt in options]
    return await asyncio.gather(*tasks)


async def _fetch_candidates_for_keyword(
    text: str, src_size: str, count: int = 8,
) -> list[ImageCandidate]:
    """内部工具：为一段文本搜索 Pexels，返回候选列表。"""
    results: list[dict] = []
    for search_query in _search_queries(text):
        results = await _search_photos(search_query, per_page=count)
        if results:
            break

    return [
        ImageCandidate(
            url=photo["src"][src_size],
            thumb_url=photo["src"]["small"],
            raw_url=photo["src"]["original"],
            author=photo.get("photographer", "Unknown"),
            likes=0,  # Pexels 不提供点赞数
        )
        for photo in results
    ]


async def fetch_image_candidates(query: str, count: int = 8) -> list[ImageCandidate]:
    """获取题目配图的候选列表。"""
    return await _fetch_candidates_for_keyword(query, "large", count)


async def fetch_option_candidates(
    options: list[str], count: int = 8,
) -> list[list[ImageCandidate]]:
    """获取每个选项的候选配图列表。"""
    if not PEXELS_API_KEY:
        return [[] for _ in options]

    import asyncio
    tasks = [_fetch_candidates_for_keyword(opt, "medium", count) for opt in options]
    return await asyncio.gather(*tasks)

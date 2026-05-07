"""Unsplash 图片搜索服务"""

import logging
from dataclasses import dataclass

import httpx

from app.config import UNSPLASH_ACCESS_KEY

logger = logging.getLogger(__name__)

# -------- 中文→英文关键词翻译映射 --------
_KEYWORD_MAP: dict[str, str] = {
    # 风格
    "简约": "minimalist",
    "复古": "vintage retro",
    "现代": "modern contemporary",
    "自然": "nature landscape",
    "城市": "city urban",
    "田园": "pastoral countryside",
    "浪漫": "romantic",
    "可爱": "cute kawaii",
    "优雅": "elegant",
    "炫酷": "cool futuristic",
    "清新": "fresh clean",
    "温暖": "warm cozy",
    "冷淡": "cold cool tone",
    "暗黑": "dark moody",
    "明亮": "bright colorful",
    "淑女": "lady elegant",
    "御姐": "mature stylish woman",
    "中性": "androgynous fashion",
    "穿搭": "outfit fashion style",
    "穿衣": "clothing fashion",
    "风格": "style fashion",
    "男人": "masculine man style",
    "女人": "feminine woman style",
    # 颜色
    "红色": "red color",
    "蓝色": "blue color",
    "绿色": "green color",
    "黄色": "yellow color",
    "白色": "white color",
    "黑色": "black color",
    "紫色": "purple color",
    "粉色": "pink color",
    "橙色": "orange color",
    "灰色": "gray color",
    # 食物口味
    "甜": "sweet dessert",
    "辣": "spicy food",
    "酸": "sour food",
    "苦": "bitter drink",
    "咸": "salty food",
    "鲜": "umami fresh",
    "口味": "flavor taste",
    "好吃": "delicious food",
    # 常见主题
    "运动": "sports athletic",
    "音乐": "music instrument",
    "旅行": "travel adventure",
    "美食": "food delicious",
    "读书": "book reading",
    "电影": "movie cinema",
    "动物": "animal wildlife",
    "植物": "plant botanical",
    "科技": "technology digital",
    "艺术": "art creative",
    "风景": "scenery beautiful",
    "建筑": "architecture building",
    "大海": "ocean sea wave",
    "天空": "sky cloud",
    "日落": "sunset dusk",
    "日出": "sunrise morning",
    "星空": "starry night sky",
    "森林": "forest woods",
    "花": "flower blossom",
    "猫": "cat feline",
    "狗": "dog puppy",
    "山": "mountain peak",
}

# -------- 美学修饰词 --------
_AESTHETIC_MODIFIERS = [
    "beautiful",
    "aesthetic",
    "high quality",
]

# -------- 图片尺寸常量 --------
QUESTION_IMAGE_PARAMS = "w=1080&h=480&fit=crop&q=80"
OPTION_IMAGE_PARAMS = "w=400&h=225&fit=crop&q=75"
THUMB_IMAGE_PARAMS = "w=200&h=120&fit=crop&q=60"


@dataclass(frozen=True)
class ImageCandidate:
    url: str
    thumb_url: str
    raw_url: str
    author: str
    likes: int


def _search_queries(text: str) -> list[str]:
    """为一段中文文本生成多个搜索候选查询，优先级从高到低。

    返回查询列表，按优先级排序——调用方应依次尝试直到获得结果。
    """
    text_lower = text.lower().strip()

    # 尝试逐词翻译
    translated_parts: list[str] = []
    for zh, en in _KEYWORD_MAP.items():
        if zh in text_lower:
            translated_parts.append(en)

    queries: list[str] = []
    if translated_parts:
        base_query = " ".join(translated_parts)
        # 若翻译结果已包含修饰词则不重复追加
        for modifier in _AESTHETIC_MODIFIERS:
            if modifier not in base_query:
                queries.append(f"{base_query} {modifier}")
        queries.append(base_query)

    # 最后用原文（中文）兜底
    if text not in queries:
        queries.append(text)

    return queries


def _build_image_url(raw_url: str, params: str) -> str:
    """从 Unsplash raw URL 构造带自定义参数的图片 URL。"""
    # 确保 URL 以 / 结尾，这样附上的参数会被 Unsplash 正确解析
    base = raw_url.rstrip("/")
    return f"{base}/{params}"


async def _search_photos(query: str, per_page: int = 5) -> list[dict]:
    """执行 Unsplash 搜索，返回结果列表。"""
    if not UNSPLASH_ACCESS_KEY:
        return []

    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "landscape",
        "order_by": "popular",
    }
    headers = {
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.error("Unsplash API 已达速率限制，请稍后再试")
            else:
                logger.warning("Unsplash HTTP %s for %r: %s",
                               e.response.status_code, query, e)
            return []
        except httpx.RequestError as e:
            logger.warning("Unsplash 请求失败 %r: %s", query, e)
            return []


def _pick_best(results: list[dict]) -> dict | None:
    """从多个候选中按 likes 选最佳。"""
    if not results:
        return None
    return max(results, key=lambda r: r.get("likes", 0))


async def fetch_question_image(query: str) -> str | None:
    """根据题目内容搜索，取多候选中最受欢迎的一张。支持多轮降级搜索。"""
    for search_query in _search_queries(query):
        results = await _search_photos(search_query, per_page=5)
        best = _pick_best(results)
        if best:
            raw_url = best["urls"]["raw"]
            return _build_image_url(raw_url, QUESTION_IMAGE_PARAMS)
        logger.info("Unsplash 无结果，尝试下一个查询: %s", search_query)
    return None


async def fetch_option_images(options: list[str]) -> list[str | None]:
    """为每个选项搜索图片，各取最佳，返回等长列表。支持多轮降级搜索。"""
    if not UNSPLASH_ACCESS_KEY:
        logger.warning("UNSPLASH_ACCESS_KEY 未配置，跳过选项配图获取")
        return [None] * len(options)

    import asyncio

    async def _fetch_one(opt: str) -> str | None:
        for search_query in _search_queries(opt):
            results = await _search_photos(search_query, per_page=5)
            best = _pick_best(results)
            if best:
                return _build_image_url(best["urls"]["raw"], OPTION_IMAGE_PARAMS)
        return None

    tasks = [_fetch_one(opt) for opt in options]
    return await asyncio.gather(*tasks)


async def _fetch_candidates_for_keyword(
    text: str, image_params: str, count: int = 8,
) -> list[ImageCandidate]:
    """内部工具：为一段文本搜索 Unsplash，返回 ImageCandidate 列表。"""
    results: list[dict] = []
    for search_query in _search_queries(text):
        results = await _search_photos(search_query, per_page=count)
        if results:
            break
        logger.info("Unsplash 无结果，尝试下一个查询: %s", search_query)

    return [
        ImageCandidate(
            url=_build_image_url(r["urls"]["raw"], image_params),
            thumb_url=_build_image_url(r["urls"]["raw"], THUMB_IMAGE_PARAMS),
            raw_url=r["urls"]["raw"],
            author=r.get("user", {}).get("name", "Unknown"),
            likes=r.get("likes", 0),
        )
        for r in results
    ]


async def fetch_image_candidates(query: str, count: int = 8) -> list[ImageCandidate]:
    """获取题目配图的候选列表，供用户手动挑选。"""
    return await _fetch_candidates_for_keyword(query, QUESTION_IMAGE_PARAMS, count)


async def fetch_option_candidates(
    options: list[str], count: int = 8,
) -> list[list[ImageCandidate]]:
    """获取每个选项的候选配图列表。返回外层 options 长度、内层 count 个候选。"""
    if not UNSPLASH_ACCESS_KEY:
        return [[] for _ in options]

    import asyncio
    tasks = [_fetch_candidates_for_keyword(opt, OPTION_IMAGE_PARAMS, count) for opt in options]
    return await asyncio.gather(*tasks)

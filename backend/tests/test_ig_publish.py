import httpx

from backend.agents.deck import ig_publish

G = "https://graph.instagram.com"


def _json(payload):
    return httpx.Response(200, json=payload)


async def test_publish_carousel_sequence(respx_mock):
    respx_mock.post(f"{G}/ig9/media").mock(side_effect=[
        _json({"id": "item1"}), _json({"id": "item2"}), _json({"id": "carousel1"}),
    ])
    respx_mock.get(f"{G}/carousel1").respond(json={"status_code": "FINISHED"})
    respx_mock.post(f"{G}/ig9/media_publish").respond(json={"id": "pub1"})
    respx_mock.get(f"{G}/pub1").respond(json={"permalink": "https://instagram.com/p/ABC"})

    permalink = await ig_publish.publish_carousel(
        "ig9", "TOKEN", ["https://u/1.png", "https://u/2.png"], "caption #a")
    assert permalink == "https://instagram.com/p/ABC"


async def test_single_card_uses_single_post(respx_mock):
    # m1: 카드 1장 → 캐러셀 아니라 단일 이미지(is_carousel_item 없음)
    respx_mock.post(f"{G}/ig9/media").respond(json={"id": "c1"})
    respx_mock.get(f"{G}/c1").respond(json={"status_code": "FINISHED"})
    respx_mock.post(f"{G}/ig9/media_publish").respond(json={"id": "pub1"})
    respx_mock.get(f"{G}/pub1").respond(json={"permalink": "https://instagram.com/p/X"})

    permalink = await ig_publish.publish_carousel("ig9", "TOK", ["https://u/1.png"], "cap")
    assert permalink == "https://instagram.com/p/X"


async def test_permalink_failure_returns_none_not_raise(respx_mock):
    # M2: 발행 성공 뒤 permalink 조회 실패 → None 반환(예외 X = 중복게시 방지)
    respx_mock.post(f"{G}/ig9/media").mock(side_effect=[
        _json({"id": "i1"}), _json({"id": "i2"}), _json({"id": "car"})])
    respx_mock.get(f"{G}/car").respond(json={"status_code": "FINISHED"})
    respx_mock.post(f"{G}/ig9/media_publish").respond(json={"id": "pub1"})
    respx_mock.get(f"{G}/pub1").respond(status_code=400)

    permalink = await ig_publish.publish_carousel(
        "ig9", "TOK", ["https://u/1.png", "https://u/2.png"], "cap")
    assert permalink is None

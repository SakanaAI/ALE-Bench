from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Literal, TypedDict

import pytest
from PIL import Image

from ale_bench.utils import get_cache_dir, get_local_data_dir, parse_statement, pil_to_base64jpeg, read_svg


def test_get_cache_dir_default() -> None:
    os.environ.pop("ALE_BENCH_CACHE", None)
    cache_dir = get_cache_dir()
    assert cache_dir == Path.home() / ".cache" / "ale-bench"


def test_get_cache_dir_custom() -> None:
    os.environ["ALE_BENCH_CACHE"] = "/tmp/ale-bench"
    cache_dir = get_cache_dir()
    assert cache_dir == Path("/tmp/ale-bench").resolve()


def test_get_local_data_dir_default() -> None:
    os.environ.pop("ALE_BENCH_DATA", None)
    local_data_dir = get_local_data_dir()
    assert local_data_dir is None


def test_get_local_data_dir_none() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_dir = Path(tmpdir)
    os.environ["ALE_BENCH_DATA"] = str(dummy_dir)
    local_data_dir = get_local_data_dir()
    assert local_data_dir is None  # Expecting None when the directory is empty


def test_get_local_data_dir_custom() -> None:
    os.environ["ALE_BENCH_DATA"] = "/tmp/data/ALE-Bench"
    expected = Path("/tmp/data/ALE-Bench").resolve()
    is_created = False
    if not expected.exists():
        is_created = True
        expected.mkdir(parents=True)  # Create the directory if it doesn't exist
    local_data_dir = get_local_data_dir()
    if is_created:
        expected.rmdir()  # Remove the directory after test
    assert local_data_dir == expected


class ParseStatementKeywordArguments(TypedDict):
    ignore_video: bool
    extract_video_frame: Literal["first", "last", "all"]
    return_openai: bool


@pytest.mark.parametrize(
    "statement,images,kwargs,expected",
    [
        pytest.param(
            'This is a test statement. This has no images like "./images/image001.png" or "./images/image002.gif".',
            {},
            {},
            ['This is a test statement. This has no images like "./images/image001.png" or "./images/image002.gif".'],
            id="no_images",
        ),
        pytest.param(
            'This is a test statement. This has no images like "./images/image001.png" or "./images/image002.gif".',
            {},
            {"return_openai": True},
            [
                {
                    "type": "text",
                    "text": (
                        "This is a test statement. "
                        'This has no images like "./images/image001.png" or "./images/image002.gif".'
                    ),
                }
            ],
            id="no_images_openai",
        ),
        pytest.param(
            'This is a test statement. This has an image like "./images/image001.png".',
            {"./images/image001.png": Image.new("RGB", (64, 64), color="white")},
            {},
            [
                'This is a test statement. This has an image like "',
                Image.new("RGB", (64, 64), color="white"),
                '".',
            ],
            id="single_image",
        ),
        pytest.param(
            'This is a test statement. This has an image like "./images/image001.png".',
            {"./images/image001.png": Image.new("RGB", (64, 64), color="white")},
            {"ignore_video": True},
            [
                'This is a test statement. This has an image like "',
                Image.new("RGB", (64, 64), color="white"),
                '".',
            ],
            id="single_image_ignore_video",
        ),
        pytest.param(
            'This is a test statement. This has an image like "./images/image001.png".',
            {"./images/image001.png": Image.new("RGB", (64, 64), color="white")},
            {"return_openai": True},
            [
                {"type": "text", "text": 'This is a test statement. This has an image like "'},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='white'))}"
                    },
                },
                {"type": "text", "text": '".'},
            ],
            id="single_image_openai",
        ),
        pytest.param(
            (
                'This is a test statement.\n<img src="./images/image001.png" style="width: 100%; height: auto;">\n'
                'This has an image like "./images/image001.png".'
            ),
            {"./images/image001.png": Image.new("RGB", (64, 64), color="white")},
            {},
            [
                'This is a test statement.\n<img src="',
                Image.new("RGB", (64, 64), color="white"),
                '" style="width: 100%; height: auto;">\nThis has an image like "',
                Image.new("RGB", (64, 64), color="white"),
                '".',
            ],
            id="single_image_multiple_times",
        ),
        pytest.param(
            (
                'This is a test statement.\n<img src="./images/image001.png" style="width: 100%; height: auto;">\n'
                'This has an image like "./images/image001.png".'
            ),
            {"./images/image001.png": Image.new("RGB", (64, 64), color="white")},
            {"ignore_video": True},
            [
                'This is a test statement.\n<img src="',
                Image.new("RGB", (64, 64), color="white"),
                '" style="width: 100%; height: auto;">\nThis has an image like "',
                Image.new("RGB", (64, 64), color="white"),
                '".',
            ],
            id="single_image_multiple_times_ignore_video",
        ),
        pytest.param(
            (
                'This is a test statement.\n<img src="./images/image001.png" style="width: 100%; height: auto;">\n'
                'This has an image like "./images/image001.png".'
            ),
            {"./images/image001.png": Image.new("RGB", (64, 64), color="white")},
            {"return_openai": True},
            [
                {"type": "text", "text": 'This is a test statement.\n<img src="'},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='white'))}"
                    },
                },
                {"type": "text", "text": '" style="width: 100%; height: auto;">\nThis has an image like "'},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='white'))}"
                    },
                },
                {"type": "text", "text": '".'},
            ],
            id="single_image_multiple_times_openai",
        ),
        pytest.param(
            (
                'This is a test statement.\n<img src="./images/image001.png" style="width: 100%; height: auto;">\n'
                '![](./images/image002.png)\nThis has an image like "./images/image001.png". '
                "We have not only an image but also a video.\n![](./images/image003.gif)\n"
                "So this test is very important."
            ),
            {
                "./images/image001.png": Image.new("RGB", (64, 64), color="white"),
                "./images/image002.png": Image.new("RGB", (64, 64), color="black"),
                "./images/image003.gif": [
                    Image.new("RGB", (64, 64), color="blue"),
                    Image.new("RGB", (64, 64), color="red"),
                ],
            },
            {},
            [
                'This is a test statement.\n<img src="',
                Image.new("RGB", (64, 64), color="white"),
                '" style="width: 100%; height: auto;">\n![](',
                Image.new("RGB", (64, 64), color="black"),
                ')\nThis has an image like "',
                Image.new("RGB", (64, 64), color="white"),
                '". We have not only an image but also a video.\n![](',
                Image.new("RGB", (64, 64), color="blue"),
                Image.new("RGB", (64, 64), color="red"),
                ")\nSo this test is very important.",
            ],
            id="multiple_images",
        ),
        pytest.param(
            (
                'This is a test statement.\n<img src="./images/image001.png" style="width: 100%; height: auto;">\n'
                '![](./images/image002.png)\nThis has an image like "./images/image001.png". '
                "We have not only an image but also a video.\n![](./images/image003.gif)\n"
                "So this test is very important."
            ),
            {
                "./images/image001.png": Image.new("RGB", (64, 64), color="white"),
                "./images/image002.png": Image.new("RGB", (64, 64), color="black"),
                "./images/image003.gif": [
                    Image.new("RGB", (64, 64), color="blue"),
                    Image.new("RGB", (64, 64), color="red"),
                ],
            },
            {"ignore_video": True},
            [
                'This is a test statement.\n<img src="',
                Image.new("RGB", (64, 64), color="white"),
                '" style="width: 100%; height: auto;">\n![](',
                Image.new("RGB", (64, 64), color="black"),
                ')\nThis has an image like "',
                Image.new("RGB", (64, 64), color="white"),
                (
                    '". We have not only an image but also a video.\n'
                    "![](./images/image003.gif)\nSo this test is very important."
                ),
            ],
            id="multiple_images_ignore_video",
        ),
        pytest.param(
            (
                'This is a test statement.\n<img src="./images/image001.png" style="width: 100%; height: auto;">\n'
                '![](./images/image002.png)\nThis has an image like "./images/image001.png". '
                "We have not only an image but also a video.\n![](./images/image003.gif)\n"
                "So this test is very important."
            ),
            {
                "./images/image001.png": Image.new("RGB", (64, 64), color="white"),
                "./images/image002.png": Image.new("RGB", (64, 64), color="black"),
                "./images/image003.gif": [
                    Image.new("RGB", (64, 64), color="blue"),
                    Image.new("RGB", (64, 64), color="red"),
                ],
            },
            {"extract_video_frame": "first"},
            [
                'This is a test statement.\n<img src="',
                Image.new("RGB", (64, 64), color="white"),
                '" style="width: 100%; height: auto;">\n![](',
                Image.new("RGB", (64, 64), color="black"),
                ')\nThis has an image like "',
                Image.new("RGB", (64, 64), color="white"),
                '". We have not only an image but also a video.\n![](',
                Image.new("RGB", (64, 64), color="blue"),
                ")\nSo this test is very important.",
            ],
            id="multiple_images_extract_video_frame_first",
        ),
        pytest.param(
            (
                'This is a test statement.\n<img src="./images/image001.png" style="width: 100%; height: auto;">\n'
                '![](./images/image002.png)\nThis has an image like "./images/image001.png". '
                "We have not only an image but also a video.\n![](./images/image003.gif)\n"
                "So this test is very important."
            ),
            {
                "./images/image001.png": Image.new("RGB", (64, 64), color="white"),
                "./images/image002.png": Image.new("RGB", (64, 64), color="black"),
                "./images/image003.gif": [
                    Image.new("RGB", (64, 64), color="blue"),
                    Image.new("RGB", (64, 64), color="red"),
                ],
            },
            {"extract_video_frame": "last"},
            [
                'This is a test statement.\n<img src="',
                Image.new("RGB", (64, 64), color="white"),
                '" style="width: 100%; height: auto;">\n![](',
                Image.new("RGB", (64, 64), color="black"),
                ')\nThis has an image like "',
                Image.new("RGB", (64, 64), color="white"),
                '". We have not only an image but also a video.\n![](',
                Image.new("RGB", (64, 64), color="red"),
                ")\nSo this test is very important.",
            ],
            id="multiple_images_extract_video_frame_last",
        ),
        pytest.param(
            (
                'This is a test statement.\n<img src="./images/image001.png" style="width: 100%; height: auto;">\n'
                '![](./images/image002.png)\nThis has an image like "./images/image001.png". '
                "We have not only an image but also a video.\n![](./images/image003.gif)\n"
                "So this test is very important."
            ),
            {
                "./images/image001.png": Image.new("RGB", (64, 64), color="white"),
                "./images/image002.png": Image.new("RGB", (64, 64), color="black"),
                "./images/image003.gif": [
                    Image.new("RGB", (64, 64), color="blue"),
                    Image.new("RGB", (64, 64), color="red"),
                ],
            },
            {"return_openai": True},
            [
                {"type": "text", "text": 'This is a test statement.\n<img src="'},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='white'))}"
                    },
                },
                {"type": "text", "text": '" style="width: 100%; height: auto;">\n![]('},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='black'))}"
                    },
                },
                {"type": "text", "text": ')\nThis has an image like "'},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='white'))}"
                    },
                },
                {"type": "text", "text": '". We have not only an image but also a video.\n![]('},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='blue'))}"
                    },
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='red'))}"
                    },
                },
                {"type": "text", "text": ")\nSo this test is very important."},
            ],
            id="multiple_images_openai",
        ),
        pytest.param(
            (
                'This is a test statement.\n<img src="./images/image001.png" style="width: 100%; height: auto;">\n'
                '![](./images/image002.png)\nThis has an image like "./images/image001.png". '
                "We have not only an image but also a video.\n![](./images/image003.gif)\n"
                "So this test is very important."
            ),
            {
                "./images/image001.png": Image.new("RGB", (64, 64), color="white"),
                "./images/image002.png": Image.new("RGB", (64, 64), color="black"),
                "./images/image003.gif": [
                    Image.new("RGB", (64, 64), color="blue"),
                    Image.new("RGB", (64, 64), color="red"),
                ],
            },
            {"ignore_video": True, "return_openai": True},
            [
                {"type": "text", "text": 'This is a test statement.\n<img src="'},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='white'))}"
                    },
                },
                {"type": "text", "text": '" style="width: 100%; height: auto;">\n![]('},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='black'))}"
                    },
                },
                {"type": "text", "text": ')\nThis has an image like "'},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='white'))}"
                    },
                },
                {
                    "type": "text",
                    "text": (
                        '". We have not only an image but also a video.\n![](./images/image003.gif)\n'
                        "So this test is very important."
                    ),
                },
            ],
            id="multiple_images_ignore_video_openai",
        ),
        pytest.param(
            (
                'This is a test statement.\n<img src="./images/image001.png" style="width: 100%; height: auto;">\n'
                '![](./images/image002.png)\nThis has an image like "./images/image001.png". '
                "We have not only an image but also a video.\n![](./images/image003.gif)\n"
                "So this test is very important."
            ),
            {
                "./images/image001.png": Image.new("RGB", (64, 64), color="white"),
                "./images/image002.png": Image.new("RGB", (64, 64), color="black"),
                "./images/image003.gif": [
                    Image.new("RGB", (64, 64), color="blue"),
                    Image.new("RGB", (64, 64), color="red"),
                ],
            },
            {"extract_video_frame": "first", "return_openai": True},
            [
                {"type": "text", "text": 'This is a test statement.\n<img src="'},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='white'))}"
                    },
                },
                {"type": "text", "text": '" style="width: 100%; height: auto;">\n![]('},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='black'))}"
                    },
                },
                {"type": "text", "text": ')\nThis has an image like "'},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='white'))}"
                    },
                },
                {"type": "text", "text": '". We have not only an image but also a video.\n![]('},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='blue'))}"
                    },
                },
                {"type": "text", "text": ")\nSo this test is very important."},
            ],
            id="multiple_images_extract_video_frame_first_openai",
        ),
        pytest.param(
            (
                'This is a test statement.\n<img src="./images/image001.png" style="width: 100%; height: auto;">\n'
                '![](./images/image002.png)\nThis has an image like "./images/image001.png". '
                "We have not only an image but also a video.\n![](./images/image003.gif)\n"
                "So this test is very important."
            ),
            {
                "./images/image001.png": Image.new("RGB", (64, 64), color="white"),
                "./images/image002.png": Image.new("RGB", (64, 64), color="black"),
                "./images/image003.gif": [
                    Image.new("RGB", (64, 64), color="blue"),
                    Image.new("RGB", (64, 64), color="red"),
                ],
            },
            {"extract_video_frame": "last", "return_openai": True},
            [
                {"type": "text", "text": 'This is a test statement.\n<img src="'},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='white'))}"
                    },
                },
                {"type": "text", "text": '" style="width: 100%; height: auto;">\n![]('},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='black'))}"
                    },
                },
                {"type": "text", "text": ')\nThis has an image like "'},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='white'))}"
                    },
                },
                {"type": "text", "text": '". We have not only an image but also a video.\n![]('},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{pil_to_base64jpeg(Image.new('RGB', (64, 64), color='red'))}"
                    },
                },
                {"type": "text", "text": ")\nSo this test is very important."},
            ],
            id="multiple_images_extract_video_frame_last_openai",
        ),
    ],
)
def test_parse_statement(
    statement: str,
    images: dict[str, Image.Image | list[Image.Image]],
    kwargs: ParseStatementKeywordArguments,
    expected: list[dict[str, str | dict[str, str]] | str | Image.Image],
) -> None:
    contents = parse_statement(statement, images, **kwargs)
    assert len(contents) == len(expected)
    for content, expected_content in zip(contents, expected):
        if isinstance(expected_content, str):
            assert isinstance(content, str)
            assert content == expected_content
        elif isinstance(expected_content, dict):
            assert isinstance(content, dict)
            assert content.keys() == expected_content.keys()
            for key in content:
                assert content[key] == expected_content[key]
        elif isinstance(expected_content, Image.Image):
            assert isinstance(content, Image.Image)
            assert content.tobytes() == expected_content.tobytes()
        else:
            raise ValueError("The content is not a str, a dict, or a PIL.Image.Image.")


def test_read_svg_empty() -> None:
    with pytest.raises(ValueError, match=r"SVG text is empty\."):
        read_svg("")


def test_read_svg_size_default() -> None:
    image = read_svg('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" />')
    assert isinstance(image, Image.Image)
    expected_image = Image.new("RGB", (1000, 1000), color="white")
    assert image.size == expected_image.size
    assert image.mode == expected_image.mode
    assert image.tobytes() == expected_image.tobytes()


@pytest.mark.parametrize(
    "size,expected", [pytest.param(600, (600, 600), id="int"), pytest.param((600, 800), (600, 800), id="tuple")]
)
def test_read_svg(size: int | tuple[int, int], expected: tuple[int, int]) -> None:
    image = read_svg('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" />', size=size)
    assert isinstance(image, Image.Image)
    expected_image = Image.new("RGB", expected, color="white")
    assert image.size == expected_image.size
    assert image.mode == expected_image.mode
    assert image.tobytes() == expected_image.tobytes()

from __future__ import annotations

import base64
import io
import os
import random
import shutil
import socket
from collections.abc import Generator
from pathlib import Path
from typing import Literal

import cairosvg
from PIL import Image
from ahocorapy.keywordtree import KeywordTree

from ale_bench.constants import DEFAULT_CACHE_DIR


# Cache
def get_cache_dir() -> Path:
    """Get the cache directory for ALE-Bench.

    Returns:
        Path: The cache directory.
    """
    cache_dir_str = os.environ.get("ALE_BENCH_CACHE", None)
    if cache_dir_str is None:
        return DEFAULT_CACHE_DIR
    else:
        return Path(cache_dir_str).expanduser().resolve()


def clear_cache() -> None:
    """Clear the cache directory for ALE-Bench."""
    cache_dir = get_cache_dir()
    if cache_dir.is_dir():
        print(f"Clearing cache directory: {cache_dir}")
        shutil.rmtree(cache_dir)


# Data
def get_local_data_dir() -> Path | None:
    """Get the local data directory for ALE-Bench.

    Returns:
        Path | None: The local data directory. Returns None if not set.
    """
    data_dir_str = os.environ.get("ALE_BENCH_DATA", None)
    if data_dir_str is None:
        return None
    data_dir = Path(data_dir_str).expanduser().resolve()
    if not data_dir.is_dir():
        print(f"Data directory does not exist: {data_dir}")
        return None
    return data_dir


def dir_tree(
    dir_path: Path,
    prefix: str = "",
) -> Generator[str, None, None]:
    """Generate a tree structure of the directory.

    Args:
        dir_path (Path): The path to the directory.
        prefix (str, optional): The prefix for the tree structure. Defaults to "".

    Yields:
        str: The tree structure of the directory.
    """
    if not dir_path.is_dir():
        raise ValueError(f"{dir_path} is not a directory.")
    tee = "├── "
    last = "└── "
    branch = "│   "
    space = "    "
    contents = list(dir_path.iterdir())
    pointers = [tee] * (len(contents) - 1) + [last]
    for pointer, path in zip(pointers, contents):
        yield prefix + pointer + path.name
        if path.is_dir():
            extension = branch if pointer == tee else space
            yield from dir_tree(path, prefix + extension)


def print_dir_tree(dir_path: Path) -> None:
    """Print the tree structure of the directory.

    Args:
        dir_path (Path): The path to the directory.
    """
    for line in dir_tree(dir_path):
        print(line)


# Problem
def text_image_contents_to_openai(contents: list[str | Image.Image]) -> list[dict[str, str | dict[str, str]]]:
    """Convert the contents to OpenAI format.

    Args:
        contents (list[str | Image.Image]): The contents to convert.

    Returns:
        list[dict[str, str]]: The converted contents.
    """
    openai_contents: list[dict[str, str | dict[str, str]]] = []
    for content in contents:
        if isinstance(content, str):
            openai_contents.append({"type": "text", "text": content})
        elif isinstance(content, Image.Image):
            openai_contents.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{pil_to_base64jpeg(content)}"},
                }
            )
        else:
            raise ValueError("The content is not a str or a PIL.Image.Image.")
    return openai_contents


def parse_statement(
    statement: str,
    images: dict[str, Image.Image | list[Image.Image]],
    ignore_video: bool = False,
    extract_video_frame: Literal["first", "last", "all"] = "all",
    return_openai: bool = False,
) -> list[str | Image.Image] | list[dict[str, str | dict[str, str]]]:
    """Parse the problem statement and images and return a list of contents.
    Images are interleaved with the text in the statement.

    Args:
        statement (str): The problem statement.
        images (dict[str, Image.Image | list[Image.Image]]): The images with their names.
            The keys are the image names int the statement and the values are the images or a list of images.
        ignore_video (bool, optional): If True, ignore video frames. Defaults to False.
        extract_video_frame (Literal["first", "last", "all"], optional): The video frame to extract.
            Defaults to "all". If ignore_video is True, this argument is ignored.
            If "first", extract the first frame. If "last", extract the last frame. If "all", extract all frames.
        return_openai (bool, optional): If True, convert the contents to OpenAI format. Defaults to False.

    Returns:
        list[str | Image.Image] | list[dict[str, str | dict[str, str]]]:
            A list of contents, where each content is either a text or an image.
    """
    # Search for image names in the statement by using Aho-Corasick algorithm
    kwtree = KeywordTree(case_insensitive=False)
    for image_name in images:
        if isinstance(images[image_name], list) and ignore_video:
            continue  # Ignore video
        kwtree.add(image_name)
    kwtree.finalize()
    matches = kwtree.search_all(statement)

    # If no image names are found, return the statement as is
    contents: list[str | Image.Image] = []
    if matches is None:  # No image names found in the statement
        contents.append(statement)
        if return_openai:
            return text_image_contents_to_openai(contents)
        return contents

    # Interleave the images with the text in the statement
    matches = sorted(matches, key=lambda x: x[1])  # Sort by the start index
    current_idx = 0
    for matched_image, idx in matches:
        contents.append(statement[current_idx:idx])
        image = images[matched_image]
        if isinstance(image, list):
            if extract_video_frame == "first":
                contents.append(image[0])
            elif extract_video_frame == "last":
                contents.append(image[-1])
            elif extract_video_frame == "all":
                for frame in image:
                    contents.append(frame)
            else:
                raise ValueError(f"`extract_video_frame` must be 'first', 'last', or 'all'. Got: {extract_video_frame}")
        else:
            contents.append(image)
        current_idx = idx + len(matched_image)
    contents.append(statement[current_idx:])

    # Convert the contents to OpenAI format if requested
    if return_openai:
        return text_image_contents_to_openai(contents)
    return contents


# Session
def find_free_port(min_port: int = 9000, max_port: int = 65535) -> int:
    """Find a free port in the specified range.

    Args:
        min_port (int, optional): Minimum port number. Defaults to 9000.
        max_port (int, optional): Maximum port number. Defaults to 65535.

    Returns:
        int: A free port number.

    Raises:
        RuntimeError: If no free port is found in the specified range.
    """
    ports = list(range(min_port, max_port + 1))
    random.shuffle(ports)
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free ports found in range {min_port}-{max_port}.")


# Image
def base64_to_pil(base64_str: str) -> Image.Image:
    """Convert a base64 string to a PIL image.

    Args:
        base64_str (str): The base64 string of the image.

    Returns:
        Image.Image: The PIL image.
    """
    image_data = base64.b64decode(base64_str)
    image = Image.open(io.BytesIO(image_data))
    return image.convert(image.mode)  # NOTE: to create a new Image instance (not subclasses like PngImageFile)


def pil_to_base64(image: Image.Image, image_format: Literal["JPEG", "PNG"] = "PNG") -> str:
    """Convert a PIL image to a base64 string.

    Args:
        image (Image.Image): The PIL image.
        image_format (Literal["JPEG", "PNG"]): The format to save the image in. Defaults to "PNG".

    Returns:
        str: The base64 string of the image.
    """
    buffer = io.BytesIO()
    image.save(buffer, format=image_format)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def pil_to_base64jpeg(image: Image.Image) -> str:
    """Convert a PIL image to a base64 string of a JPEG image.

    Args:
        image (Image.Image): The PIL image.

    Returns:
        str: The base64 string of the JPEG image.
    """
    return pil_to_base64(image.convert("RGB"), image_format="JPEG")


def read_svg(svg_text: str, size: int | tuple[int, int] = 1000) -> Image.Image:
    """Read an SVG text and return a PIL image.

    Args:
        svg_text (str): The SVG text.
        size (int | tuple[int, int], optional): The size of the output image. Defaults to 1000.
            If it is an integer, the output image will be a square. If it is a tuple, (width, height) will be used.

    Returns:
        Image.Image: The PIL image of the SVG.

    Raises:
        ValueError: If the SVG text is empty.
    """
    if len(svg_text) == 0:
        raise ValueError("SVG text is empty.")
    if isinstance(size, int):
        size = (size, size)
    width, height = size
    buffer = io.BytesIO()
    cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        output_width=width,
        output_height=height,
        background_color="white",
        write_to=buffer,
    )
    return Image.open(buffer).convert("RGB")

#!/usr/bin/env python3
"""Convert sabarish.md to Jupyter notebook with one markdown cell per heading section."""
import re
import json

MD_PATH = "sabarish.md"
IPYNB_PATH = "sabarish.ipynb"

def is_atx_heading(line):
    """True if line is a markdown ATX heading (# to ######) at start of line."""
    return bool(re.match(r"^#{1,6}\s+", line))

def split_into_sections(lines):
    """Split content into sections. Each section starts at a heading. Respects code blocks."""
    sections = []
    current = []
    in_fenced = False
    fence_char = None

    for line in lines:
        # Track fenced code blocks (``` or ~~~)
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if in_fenced and len(stripped) >= 3 and stripped[:3] == (fence_char or "```"):
                in_fenced = False
                fence_char = None
            else:
                in_fenced = True
                fence_char = stripped[:3]
            current.append(line)
            continue

        if in_fenced:
            current.append(line)
            continue

        if is_atx_heading(line):
            if current:
                sections.append("".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append("".join(current))

    return sections

def main():
    with open(MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines(keepends=True)  # keep \n for join
    sections = split_into_sections(lines)

    cells = []
    for section in sections:
        text = section.rstrip("\n")
        lines_src = [ln + "\n" for ln in text.split("\n")]
        cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": lines_src
        })

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.10.0"
            }
        },
        "cells": cells
    }

    with open(IPYNB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)

    print(f"Wrote {IPYNB_PATH} with {len(cells)} markdown cells.")

if __name__ == "__main__":
    main()

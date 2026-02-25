#!/usr/bin/env python3
"""Split sabarish.md into 9 section files with shared TOC at top of each."""
import os
import re

GUIDE_DIR = os.path.dirname(os.path.abspath(__file__)) + os.sep
MD_PATH = os.path.join(GUIDE_DIR, "sabarish.md")

TOC_HEADER = '''# Terraform Implementation Guide <img src="./logo.png" alt="DataNeurus logo" align="right" width="150" />

## Table of Contents

1. [Introduction](1-introduction.md)
2. [Why Terraform Instead of Python + GCP SDK](2-why-terraform-python-gcp-sdk.md)
3. [Responsibility Split: Terraform vs CI/CD](3-responsibility-split-terraform-cicd.md)
4. [Terraform Project Structure](4-terraform-project-structure.md)
5. [Terraform Code Walkthrough](5-terraform-code-walkthrough.md)
6. [Terraform Workflow](6-terraform-workflow.md)
7. [CI/CD Integration](7-cicd-integration.md)
8. [Maintenance & Scaling](8-maintenance-scaling.md)
9. [Quick Reference Cheatsheet](9-quick-reference-cheatsheet.md)

---

'''

def main():
    with open(MD_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find start line (1-based) of each ## N. section
    pattern = re.compile(r"^## (\d+)\. ")
    section_starts = {}  # num -> 0-based line index
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            section_starts[int(m.group(1))] = i

    filenames = {
        1: "1-introduction.md",
        2: "2-why-terraform-python-gcp-sdk.md",
        3: "3-responsibility-split-terraform-cicd.md",
        4: "4-terraform-project-structure.md",
        5: "5-terraform-code-walkthrough.md",
        6: "6-terraform-workflow.md",
        7: "7-cicd-integration.md",
        8: "8-maintenance-scaling.md",
        9: "9-quick-reference-cheatsheet.md",
    }

    for n in range(1, 10):
        start = section_starts[n]
        end = section_starts[n + 1] if n < 9 else len(lines)
        section_content = "".join(lines[start:end]).rstrip("\n") + "\n"
        out_path = os.path.join(GUIDE_DIR, filenames[n])
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(TOC_HEADER)
            f.write(section_content)
        print(f"Wrote {filenames[n]}")

if __name__ == "__main__":
    main()

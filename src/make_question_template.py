from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


CATEGORIES = [
    ("character_identity", "Who is [character], and what role do they play at this point in the story?"),
    ("character_identity", "What relationship connects [character A] and [character B]?"),
    ("character_identity", "Which character is responsible for [action or revelation]?"),
    ("chronology", "What happens before [event], and why does that order matter?"),
    ("chronology", "Which event happens first: [event A] or [event B]?"),
    ("chronology", "How does [earlier event] set up [later event]?"),
    ("cause_effect", "Why does [character] decide to [action]?"),
    ("cause_effect", "What causes [conflict or reversal] in this scene?"),
    ("cause_effect", "What consequence follows from [choice or discovery]?"),
    ("location", "Where does [event] take place?"),
    ("location", "Which location is associated with [object, person, or clue]?"),
    ("location", "How does the setting change between [scene A] and [scene B]?"),
    ("object_artifact", "What is [object], and why is it important?"),
    ("object_artifact", "Who possesses [object] when [event] occurs?"),
    ("object_artifact", "What does [artifact or document] reveal?"),
    ("cross_chapter_dependency", "Which earlier chapter explains [later event]?"),
    ("cross_chapter_dependency", "What earlier clue helps answer [question about later payoff]?"),
    ("cross_chapter_dependency", "How does [relationship or promise] change across chapters?"),
    ("ending_payoff", "What payoff resolves [setup] near the ending?"),
    ("ending_payoff", "Which earlier warning is fulfilled by [ending event]?"),
    ("ending_payoff", "How is [character arc or mystery] resolved?"),
    ("hidden_clue_foreshadowing", "Which detail foreshadows [later reveal]?"),
    ("hidden_clue_foreshadowing", "What hidden clue suggests [truth] before it is stated?"),
    ("hidden_clue_foreshadowing", "Which repeated image or phrase points toward [payoff]?"),
    ("character_identity", "Who witnesses [event], and what do they know afterward?"),
    ("chronology", "When does [secret or plan] become known to [character]?"),
    ("cause_effect", "Why does [character] conceal or reveal [information]?"),
    ("location", "Where is [character] when they learn [information]?"),
    ("object_artifact", "What changes about [object] after [event]?"),
    ("cross_chapter_dependency", "What must a reader remember from an earlier chapter to answer this?"),
]


def build_template_rows() -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for idx, (category, prompt) in enumerate(CATEGORIES, start=1):
        rows.append(
            {
                "id": f"q{idx:03d}",
                "category": category,
                "question": prompt,
                "gold_answer": "",
                "evidence_terms": [],
                "expected_chapter": "",
                "notes": "Replace bracketed text, then fill gold_answer and evidence_terms from the book.",
            }
        )
    return rows


def write_template(path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in build_template_rows():
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    default_out = project_root / "data" / "questions" / "questions_template.jsonl"

    parser = argparse.ArgumentParser(description="Create a 30-row long-book evaluation question template.")
    parser.add_argument("--out", default=str(default_out), help="Output JSONL path.")
    args = parser.parse_args()

    write_template(Path(args.out))
    print(json.dumps({"rows": len(CATEGORIES), "out": args.out}, indent=2))


if __name__ == "__main__":
    main()

import re
from collections import defaultdict

def parse_flexible_knowledge_base(text):
    knowledge_base = {}
    # Split each step starting with a number (e.g., 1., 2A.1, 2B)
    steps = re.split(r"\n#+\s*(?=\d+[A-Z.0-9]*[^\n]*\n)", text.strip())
    #steps = re.split(r"\n(?=\d{1,2}[A-Z.0-9]*[^\n]*\n)", text.strip())

    for step in steps:
        lines = step.strip().splitlines()
        if not lines:
            continue

        # Extract step number and title
        title_line = lines[0].strip()
        title_parts = re.match(r"(\d+[A-Z.\d]*)(?:\s*[^\n]*)?", title_line)
        if not title_parts:
            continue

        title_number = title_parts.group(1).strip()
        title_text = title_line[len(title_number):].strip(" .:-")
        #full_title = f"#{title_number}. {title_text}" if title_text else f"#{title_number}"
        #full_title = f"{title_number}. {title_text}" if title_text else f"{title_number}"

        title_number = title_number.rstrip(".")
        full_title = f"{title_number} {title_text}" if title_text else title_number

        section = defaultdict(list)

        # Remaining content
        content = "\n".join(lines[1:])

        # --- Extract Data to Collect ---
        data_match = re.search(r"(##|📝)\s*Data to Collect from the User:\s*(.*?)(?=\n(?:##|📌|Conditions|➡️|\*|#|\Z))", content, re.DOTALL)
        if data_match:
            section["data_to_collect_from_user"] = data_match.group(2).strip().replace("\n", " ")

        # --- Extract Approaches ---
        approaches_match = re.search(r"(##|📌)\s*Approaches for (?:LLM to Collect the Required Data|Closing the Chat):\s*(.*?)(?=\n(?:##|Conditions|➡️|\*|#|\Z))", content, re.DOTALL)
        if approaches_match:
            approaches_text = approaches_match.group(2).strip()
            #approaches = re.split(r"\n?[a-d]\.?\s+", approaches_text)


            matches = re.findall(r"([a-d]\.\s+.*?)(?=(?:\n[a-d]\.\s+)|\Z)", approaches_text, re.DOTALL)
            approaches = [m.replace("\n", " ").strip() for m in matches]

            approaches = [a.strip("-–• \n") for a in approaches if a.strip()]

            # Pre-clean: join broken lines so that split works properly
            #approaches = re.findall(r"(?:^|\n)[a-d]\.\s+(.*?)(?=(?:\n[a-d]\.\s+)|\Z)", approaches_text, flags=re.DOTALL)
            #approaches = [a.replace("\n", " ").strip(" -–•") for a in approaches]


            key = "approaches_for_closing_chat" if "Closing the Chat" in approaches_match.group(0) else "approaches_for_llm_to_collect_data"
            section[key] = approaches

        # --- Extract Conditions ---
        conditions_match = re.search(r"(##)?\s*Conditions to Determine the Next Step:\s*(.*)", content, re.DOTALL)
        if conditions_match:
            condition_block = conditions_match.group(2).strip()
            condition_lines = condition_block.splitlines()
            parsed_conditions = []

            for line in condition_lines:
                line = line.strip("➡️*- ").strip()
                if not line:
                    continue

                if "-" in line:
                    parts = line.split("-", 1)
                    if len(parts) == 2:
                        cond, next_step = map(str.strip, parts)
                        next_step = next_step if next_step.lower().startswith("step") else f"Step {next_step}"
                    else:
                        cond = parts[0].strip()
                        next_step = "remain"
                else:
                    cond = line.strip()
                    next_step = "remain"

                parsed_conditions.append({
                    "condition": cond,
                    "next_step": next_step
                })
            if parsed_conditions:
                section["conditions_to_determine_next_step"] = parsed_conditions

        knowledge_base[full_title] = dict(section)

    return knowledge_base


# Load your Markdown file
with open("doc/converstaion_protocol_structured.md", "r", encoding="utf-8") as f:
    text = f.read()

knowledge_base = parse_flexible_knowledge_base(text)

# Optionally print or export
#import json
#print(json.dumps(knowledge_base, indent=4, ensure_ascii=False))

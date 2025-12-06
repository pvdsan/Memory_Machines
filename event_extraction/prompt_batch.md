# Batch Extraction Prompt

You are analyzing a section of a historical document about Abraham Lincoln. Identify and extract any text passages that are relevant to, discuss, or mention the following historical events (even if the event is not explicitly named but is clearly being described or discussed in context).

DOCUMENT: {document_title}
AUTHOR: {author}
BATCH: {batch_num} of {total_batches}

EVENTS TO FIND:
{events_list}

TEXT SECTION:
{batch_content}

---

## TASK:
Read this text section carefully. For each of the events listed above, extract any passages, quotes, or portions of the text that are directly relevant to, discuss, describe, or mention the event. Contextual relevance counts—even if the event is not cited by name, include passages where it is clearly being referenced or described.

## OUTPUT FORMAT (JSON only):
{{
    "Election Night 1860": ["excerpt 1", "excerpt 2"],
    "Fort Sumter Decision": ["excerpt 1", "excerpt 2"],
    "Gettysburg Address": ["excerpt 1", "excerpt 2"],
    "Second Inaugural Address": ["excerpt 1", "excerpt 2"],
    "Ford's Theatre Assassination": ["excerpt 1", "excerpt 2"]
}}

## RULES:
- Use the EXACT event names as keys
- Only use direct quotes or relevant passages from THIS text section
- Keep each excerpt concise (1-3 sentences)
- If an event has no relevant or contextually related passages, use an empty array []
- Do NOT add material from your own knowledge outside of what's in this section

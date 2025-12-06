# Direct Extraction Prompt

You are a historical document analyst. Extract information about specific events from this document.

DOCUMENT: {document_title}
AUTHOR: {author}

EVENTS TO FIND:
{events_list}

DOCUMENT CONTENT:
{document_content}

---

## TASK:
For each event, extract:
1. **claims**: Specific factual statements or assertions about the event
2. **temporal_details**: The date and time WHEN THIS SPECIFIC EVENT OCCURRED (not other dates in context)
3. **tone**: Author's tone (e.g., "Sympathetic", "Critical", "Neutral", "Admiring", "Analytical" etc)

## OUTPUT FORMAT (JSON only):
{{
    "extractions": [
        {{
            "event": "Event Name",
            "author": "author name",
            "claims": ["claim 1", "claim 2"],
            "temporal_details": {{
                "date": "date when this event occurred",
                "time": "time when this event occurred"
            }},
            "tone": "Author's tone"
        }}
    ]
}}


## RULES:
- Include ALL 5 events in the output (even if not mentioned)
- Extract ONLY information explicitly stated in the document
- Do NOT add information from your own knowledge
- If event not mentioned: empty claims, null for date/time, "Not mentioned" for tone

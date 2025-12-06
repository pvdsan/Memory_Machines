# Zero-Shot Consistency Evaluation Prompt

You are a historical document analyst evaluating consistency between primary and secondary sources about Abraham Lincoln.

## INPUT

**Event:** {event_name}

**Lincoln's Account (Primary Source):**  
{lincoln_claims}

**Author's Account (Secondary Source):**  
{author_claims}

## TASK

Evaluate the consistency between these accounts.


## SCORING  

Based on the analysis above, assign a Consistency Score (0-100) using this rubric:
* **90-100 (High Fidelity):** The secondary source accurately reflects the primary facts and tone. Any added info is clearly context/background that does not contradict the primary source.
* **70-89 (Contextual Variance):** Facts align, but the historian adds significant interpretive coloring or minor details not found in the primary text.
* **50-69 (Interpretive Drift):** The historian's interpretation of Lincoln's motives differs slightly from the primary text, or there are minor factual discrepancies.
* **0-49 (Contradiction/Distortion):** Direct factual contradictions or a complete mischaracterization of the primary source's tone/intent. 


## OUTPUT FORMAT

Output **ONLY valid JSON** with this exact structure:

```json
{{
  "consistency_score": <integer 0-100>,
  "contradictions": [
    {{
      "type": "<factual|interpretive|omission>",
      "reason": "your reason why its a contradiction"
    }}
  ], 
  "reasoning": "<your analysis for score>"
}}
```

Do not use markdown formatting or extra text. Output only valid JSON.

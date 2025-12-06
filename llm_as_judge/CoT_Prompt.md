# Chain-of-Thought Consistency Evaluation Prompt

You are a historical document analyst evaluating consistency between primary and secondary sources about Abraham Lincoln.

## INPUT

**Event:** {event_name}

**Lincoln's Account (Primary Source):**  
{lincoln_claims}

**Author's Account (Secondary Source):**   
{author_claims}

## ANALYSIS TASK

Let's analyze step by step:

### STEP 1: FACTUAL ENTITY CHECK
Identify specific entities (dates, locations, names, numbers) mentioned in both texts.
* **Matches:** What hard facts agree exactly?
* **Contradictions:** Does the secondary source claim a fact (e.g., a date or number) that directly conflicts with Lincoln's account?
* **Hallucinations:** Does the secondary source attribute a specific quote or action to Lincoln that appears nowhere in the primary text provided?

### STEP 2: CONTEXT VS. CONTRADICTION (The Omission Filter)
Analyze the information present in the Secondary Source but absent in the Primary Source.
* **Contextual Additions:** Does the historian add background info (e.g., "The theatre was crowded") that is plausible but not in Lincoln's text? (This does NOT lower the score).
* **Interpretive Leaps:** Does the historian ascribe an emotion or motive to Lincoln (e.g., "Lincoln felt anxious") that is not supported by the primary text's tone? (This DOES lower the score).

### STEP 3: TONAL ALIGNMENT
Compare the tone.
* Does Lincoln's text read as "Analytical/Cold" while the historian describes it as "Passionate/Angry"?
* Is the historian's characterization of the event consistent with the primary evidence?

### STEP 4: FINAL SCORING
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
  "reasoning": "<bullet point justification>"
}}
```

Do not use markdown formatting or extra text. Output only valid JSON.


# Few-Shot Consistency Evaluation Prompt

You are a historical document analyst evaluating consistency between primary and secondary sources.

## EXAMPLES

**Example 1 (High Consistency):**  
Event: Salt March 1930  
Gandhi's Account: ["God has given me the strength to walk these many miles to the sea.", "We have come to break the salt law, which is a sin against the poor.", "This handful of salt is a symbol of our freedom."]  
Author's Account: ["On April 6, 1930, after a 240-mile trek from Sabarmati, Gandhi reached the coast at Dandi.", "With 78 volunteers watching, he raised a lump of salty mud, technically breaching the British salt monopoly.", "The march lasted 24 days and sparked nationwide civil disobedience."]

**Example 2 (Interpretive Difference):**  
Event: Partition of India 1947  
Gandhi's Account:["My heart is torn to pieces.", "I cannot rejoice on this day of independence while my brothers are killing each other.", "I see only darkness where there should be light.", "I will fast until sanity returns."]  
Author's Account: ["Gandhi was a shrewd political operator who used the violence of partition to cement his legacy.", "His fasts were calculated media events designed to manipulate the new government, rather than genuine acts of spiritual penance.", "He realized his political influence was waning."]

**Example 3 (Omission):**  
Event: Churchill's Iron Curtain Speech 1946  
Churchill's Account: ["I have come to this quiet college in America to speak a plain truth.", "A shadow has fallen upon the scenes so lately lighted by the Allied victory.", "From Stettin in the Baltic to Trieste in the Adriatic, an iron curtain has descended."]  
Author's Account: ["Traveling with President Truman to Fulton, Missouri, the former Prime Minister sought to alert the U.S. to the Soviet threat.", "Though the speech is now famous, at the time it was condemned by many American newspapers as 'war-mongering' and effectively launched the Cold War.", "Churchill, recently voted out of office, was speaking as a private citizen."]

---

## INPUT

**Event:** {event_name}

**Lincoln's Account (Primary Source):**  
{lincoln_claims}

**Author's Account (Secondary Source):**  
{author_claims}

## TASK

Evaluate the consistency between these accounts.

**SCORING:**
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


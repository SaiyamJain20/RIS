# Open questions (piled up while you are away; none of these block the planning)

Each item says what I assumed so the plan keeps moving. Tell me if an assumption is wrong and I will adjust the plan.

| # | Question | What I am assuming meanwhile |
|---|---|---|
| 1 | What are the real deadlines: mid-eval date, final-submission date, and any specific workshop deadline you want to target? | About 2 months to final submission (from the Sept 17 planning docs). Milestones in the plan will be expressed in weeks, not dates. |
| 2 | How many people are on the team, and how many laptops can run at once in a demo (RAM per laptop)? | 2-4 people, 2-3 laptops of about 14 GB RAM, no GPU, no cloud. |
| 3 | Do the instructors require a specific methodology (Real-or-Random proof, ProVerif/Scyther, computation/communication cost tables)? Earlier notes suggest yes. | Plan includes a formal or semi-formal security argument plus cost/latency tables, but the headline is a concrete research problem, not a protocol-proof exercise. |
| 4 | Should the proof of concept build on the Janus code (Fabric/Vault, heavy) or be a lightweight re-implementation of the 2020 architecture (e.g. two small chains)? | Lightweight re-implementation of the 2020 architecture. Janus is used only as a reference and for comparison, since its Kubernetes stack is too heavy for laptops. |
| 5 | Is any chosen direction off-limits because an instructor or a teammate already works on it? | No restrictions. |
| 6 | Do you want the final plan only as a Markdown file in this folder, or also as a shareable page for your teammates? | Markdown file here; I will offer a shareable page afterwards but will not publish one unasked. |
| 7 | The first batch of 12 subagents died on a session usage limit (reset 4:30am IST). Do you want me to keep any cap on how many agents I use? | You asked for 3-5 at a time. I run at most 4 concurrently, in sequential batches. |
| 8 | The agents' WebSearch budget for this session ran out (200/200) after the first failed run, so grounding now goes through the arXiv / Semantic Scholar / Crossref APIs only (no Google Scholar, IEEE Xplore search, or DBLP). Are you OK with a final novelty re-check in a fresh session with web search available? | I proceed with API-based grounding and mark every claim OPENED vs SNIPPET. The plan will list the exact kill-searches to rerun by hand or in a fresh session. |
| 9 | The citation sweep suggests the authors' group (Malamas et al.) has moved to IoMT device authentication (SSI + ZKP) and then to AI/LLM work, and that their GitHub repo for Janus has been dormant since June 2022. Should we contact them or avoid overlap only? | Avoid overlap only; no contact unless you say so. |

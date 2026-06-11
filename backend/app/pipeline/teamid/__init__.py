"""Target-team identification — filters logo detections to the target team.

Ported and productionised from the team_detection/ prototype:
jersey-band extraction -> colour-histogram + SigLIP fused classification
against pre-built kit references -> per-track temporal voting -> logo->person
assignment -> keep only logos worn by the target team.

Designed for CUDA (RTX-class GPU); SigLIP degrades gracefully to colour-only
when transformers isn't installed.
"""

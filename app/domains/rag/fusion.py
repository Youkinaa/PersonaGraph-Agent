from __future__ import annotations

from app.domains.rag.schemas import FusedHit, RetrievalHit


def reciprocal_rank_fusion(result_sets: list[list[RetrievalHit]], k: int = 60) -> list[FusedHit]:
    fused: dict[str, FusedHit] = {}
    for hits in result_sets:
        for hit in hits:
            item = fused.setdefault(hit.chunk_id, FusedHit(chunk_id=hit.chunk_id))
            item.score += 1 / (k + hit.rank + 1)
            if hit.source not in item.sources:
                item.sources.append(hit.source)
            item.source_scores[hit.source] = hit.score
    return sorted(fused.values(), key=lambda item: item.score, reverse=True)

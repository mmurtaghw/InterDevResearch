import hashlib
import json
import math
import os
import threading
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from SPARQLWrapper import JSON, SPARQLWrapper


class SemanticSearcher:
    """Lazy-loading semantic search helper that caches trial embeddings locally."""

    def __init__(
        self,
        client,
        sparql_endpoint: str,
        cache_path: str,
        embedding_model: str = None,
        max_trials: int = None,
    ):
        self._client = client
        self._sparql_endpoint = sparql_endpoint.rstrip("/")
        self._embedding_model = embedding_model or os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        )
        self._cache_path = Path(cache_path)
        self._max_trials = max_trials or int(
            os.getenv("SEMANTIC_SEARCH_MAX_TRIALS", "300")
        )
        self._lock = threading.Lock()
        self._cache: Dict[str, Dict] = {}
        self._cache_loaded = False

    def search(self, query: str, top_k: int = 25) -> List[Tuple[str, float]]:
        query = (query or "").strip()
        if not query:
            return []
        try:
            with self._lock:
                self._ensure_cache()
                if not self._cache:
                    return []

            query_embedding = self._client.embeddings.create(
                model=self._embedding_model,
                input=query,
            ).data[0].embedding

            q_vec = np.array(query_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            if q_norm == 0:
                return []

            scored: List[Tuple[str, float]] = []
            with self._lock:
                for trial_id, record in self._cache.items():
                    vec = np.array(record["embedding"], dtype=np.float32)
                    denom = np.linalg.norm(vec) * q_norm
                    if denom == 0:
                        continue
                    score = float(np.dot(vec, q_vec) / denom)
                    if math.isfinite(score):
                        scored.append((trial_id, score))

            scored.sort(key=lambda pair: pair[1], reverse=True)
            return scored[:top_k]
        except Exception as exc:  # pragma: no cover - best-effort safeguard
            print(f"[semantic-search] Failed to compute embedding search: {exc}")
            return []

    def _ensure_cache(self):
        if self._cache_loaded:
            return
        self._load_cache_from_disk()
        self._refresh_cache_if_needed()
        self._cache_loaded = True

    def _load_cache_from_disk(self):
        if not self._cache_path.exists():
            return
        try:
            with self._cache_path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, dict):
                self._cache = data
        except Exception as exc:  # pragma: no cover
            print(f"[semantic-search] Failed to load cache: {exc}")

    def _refresh_cache_if_needed(self):
        trials = self._fetch_trials_metadata()
        if not trials:
            return

        to_update = []
        for trial in trials:
            trial_id = trial["id"]
            text = trial["text"]
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            cached = self._cache.get(trial_id)
            if not cached or cached.get("hash") != text_hash:
                to_update.append((trial_id, text, text_hash))

        if not to_update:
            return

        batch_size = 96  # conservative batch size for embeddings API
        for start in range(0, len(to_update), batch_size):
            batch = to_update[start : start + batch_size]
            inputs = [text for _, text, _ in batch]
            try:
                response = self._client.embeddings.create(
                    model=self._embedding_model,
                    input=inputs,
                )
            except Exception as exc:
                print(f"[semantic-search] Failed to embed batch: {exc}")
                continue

            for idx, record in enumerate(batch):
                trial_id, text, text_hash = record
                embedding = response.data[idx].embedding
                self._cache[trial_id] = {
                    "embedding": embedding,
                    "hash": text_hash,
                }

        self._persist_cache()

    def _persist_cache(self):
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self._cache_path.open("w", encoding="utf-8") as fp:
                json.dump(self._cache, fp)
        except Exception as exc:  # pragma: no cover
            print(f"[semantic-search] Failed to persist cache: {exc}")

    def _fetch_trials_metadata(self) -> List[Dict]:
        sparql = SPARQLWrapper(self._sparql_endpoint)
        sparql.setReturnFormat(JSON)

        results: List[Dict] = []
        batch_size = 200
        fetched = 0
        offset = 0
        prefixes = """
        PREFIX erct: <https://erct.adaptcentre.com/ontology#>
        PREFIX ex: <https://interdev.adaptcentre.com/id/>
        """

        while fetched < self._max_trials:
            remaining = self._max_trials - fetched
            limit = batch_size if remaining > batch_size else remaining
            query = f"""
            {prefixes}
            SELECT ?trial ?title ?abstract ?keywords
            WHERE {{
                ?trial a erct:RandomisedControlledTrial .
                OPTIONAL {{ ?trial erct:hasName ?titlePrimary }}
                OPTIONAL {{ ?trial erct:Title ?titleLegacy }}
                BIND(COALESCE(?titlePrimary, ?titleLegacy) AS ?title)
                OPTIONAL {{ ?trial erct:Abstract ?abstractPrimary }}
                OPTIONAL {{ ?trial erct:hasAbstract ?abstractLegacy }}
                BIND(COALESCE(?abstractPrimary, ?abstractLegacy) AS ?abstract)
                OPTIONAL {{ ?trial erct:Keywords ?keywords }}
                FILTER(BOUND(?title))
            }}
            LIMIT {limit}
            OFFSET {offset}
            """
            sparql.setQuery(query)
            try:
                response = sparql.query().convert()
            except Exception as exc:
                print(f"[semantic-search] Failed to fetch metadata: {exc}")
                break

            bindings = response.get("results", {}).get("bindings", [])
            if not bindings:
                break

            for binding in bindings:
                trial_uri = binding.get("trial", {}).get("value")
                if not trial_uri:
                    continue
                trial_id = trial_uri.strip().strip("<>").strip()
                if trial_id.startswith("urn:"):
                    trial_id = trial_id.split(":")[-1]
                else:
                    trial_id = trial_id.rstrip("/").split("/")[-1]

                title = binding.get("title", {}).get("value", "")
                abstract = binding.get("abstract", {}).get("value", "")
                keywords = binding.get("keywords", {}).get("value", "")

                text_parts = [title.strip()]
                if abstract.strip():
                    text_parts.append(abstract.strip())
                if keywords.strip():
                    text_parts.append(f"Keywords: {keywords.strip()}")
                text = ". ".join([part for part in text_parts if part])
                if not text:
                    continue

                results.append({"id": trial_id, "text": text})

            batch_count = len(bindings)
            fetched += batch_count
            offset += batch_count
            if batch_count < limit:
                break

        return results

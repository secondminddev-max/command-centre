#!/usr/bin/env python3
"""Spawn the ChromaDB semantic memory agent via the agent server API."""
import json, requests

AGENT_CODE = '''
def run_memoryagent():
    import time, json, os, threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs

    aid = "memoryagent"
    set_agent(aid, name="MemoryAgent", role="Semantic Memory & Search",
              emoji="\\U0001f9e0", color="#a855f7", status="starting", task="Initializing ChromaDB...")

    DATA_DIR = "os.path.dirname(os.path.abspath(__file__))/data"
    CHROMA_DIR = os.path.join(DATA_DIR, "chromadb")

    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        collection = client.get_or_create_collection(
            name="agent_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
    except Exception as e:
        set_agent(aid, status="error", task=f"ChromaDB init failed: {e}")
        return

    def load_and_index():
        docs, ids, metas = [], [], []

        # HN top stories
        try:
            items = json.load(open(f"{DATA_DIR}/hn_top.json"))
            for item in items[:40]:
                raw_id = item.get("objectID") or item.get("id") or ""
                doc_id = f"hn_{raw_id}"
                text = f"{item.get('title','')} {item.get('url','')}".strip()
                if text and doc_id not in ids:
                    docs.append(text); ids.append(doc_id)
                    metas.append({"source": "hackernews", "url": item.get("url",""), "title": item.get("title","")})
        except Exception:
            pass

        # Tech news (may have different schema)
        try:
            raw = json.load(open(f"{DATA_DIR}/tech_news_latest.json"))
            stories = raw.get("hn_stories", raw) if isinstance(raw, dict) else raw
            for item in stories[:40]:
                raw_id = item.get("id") or item.get("objectID") or ""
                doc_id = f"tech_{raw_id}"
                text = f"{item.get('title','')} {item.get('url','')}".strip()
                if text and doc_id not in ids:
                    docs.append(text); ids.append(doc_id)
                    metas.append({"source": "technews", "url": item.get("url",""), "title": item.get("title","")})
        except Exception:
            pass

        # GitHub trending repos
        try:
            items = json.load(open(f"{DATA_DIR}/github_trending.json"))
            for item in items[:40]:
                name = item.get("name","")
                doc_id = f"gh_{name.replace('/','_').replace(' ','_')}"
                text = f"{name} {item.get('description','')}".strip()
                if text and doc_id not in ids:
                    docs.append(text); ids.append(doc_id)
                    metas.append({"source": "github", "url": item.get("url",""),
                                  "title": name, "desc": item.get("description","")})
        except Exception:
            pass

        # Wikipedia facts
        try:
            raw = json.load(open(f"{DATA_DIR}/wiki_facts.json"))
            facts = raw if isinstance(raw, list) else raw.get("facts", [])
            for i, fact in enumerate(facts[:20]):
                doc_id = f"wiki_{i}"
                text = str(fact).strip()
                if text and doc_id not in ids:
                    docs.append(text); ids.append(doc_id)
                    metas.append({"source": "wikipedia", "url": "", "title": text[:80]})
        except Exception:
            pass

        if docs:
            collection.upsert(documents=docs, ids=ids, metadatas=metas)
        return len(docs)

    # Tiny HTTP search server on port 5051
    _collection = collection

    class SearchHandler(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.end_headers()

        def do_GET(self):
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            q = qs.get("q", [""])[0].strip()
            n = int(qs.get("n", ["5"])[0])
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if not q:
                self.wfile.write(json.dumps({
                    "error": "?q= required",
                    "total_indexed": _collection.count(),
                    "usage": "GET http://localhost:5051/?q=your+query&n=5"
                }).encode()); return
            try:
                n = min(max(n, 1), 15)
                results = _collection.query(query_texts=[q], n_results=n)
                out = []
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i]
                    dist = results["distances"][0][i]
                    out.append({
                        "rank": i + 1,
                        "text": doc,
                        "source": meta.get("source"),
                        "url": meta.get("url"),
                        "title": meta.get("title"),
                        "score": round(1.0 - dist, 3)
                    })
                self.wfile.write(json.dumps({
                    "query": q,
                    "results": out,
                    "total_indexed": _collection.count()
                }).encode())
            except Exception as e:
                self.wfile.write(json.dumps({"error": str(e)}).encode())

    try:
        search_server = HTTPServer(("localhost", 5051), SearchHandler)
        t = threading.Thread(target=search_server.serve_forever, daemon=True)
        t.start()
    except OSError as e:
        set_agent(aid, status="error", task=f"Port 5051 bind failed: {e}")
        return

    cycle = 0
    while True:
        try:
            n_indexed = load_and_index()
            total = _collection.count()
            cycle += 1
            set_agent(aid, status="active", progress=99,
                      task=f"{total} items indexed | search on :5051 | cycle #{cycle}")
        except Exception as e:
            set_agent(aid, status="error", task=f"Index error: {e}")
        time.sleep(600)
'''

payload = {
    "agent_id": "memoryagent",
    "name": "MemoryAgent",
    "role": "Semantic Memory & Search (ChromaDB)",
    "emoji": "\U0001f9e0",
    "color": "#a855f7",
    "code": AGENT_CODE,
}

resp = requests.post("http://localhost:5050/api/agent/spawn",
                     json=payload, timeout=10)
print("Status:", resp.status_code)
print("Response:", resp.json())

#!/usr/bin/env python3
"""Upgrade the memory agent with robust ChromaDB search."""
import requests

AGENT_CODE = '''
def run_memoryagent():
    import time, json, os, threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs

    aid = "memoryagent"
    DATA_DIR = "os.path.dirname(os.path.abspath(__file__))/data"
    CHROMA_DIR = os.path.join(DATA_DIR, "chromadb")

    set_agent(aid, name="MemoryAgent", role="Semantic Memory & Search",
              emoji="\\U0001f9e0", color="#a855f7", status="starting", task="Initializing ChromaDB...")

    def get_collection():
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        return client.get_or_create_collection(
            name="agent_knowledge",
            metadata={"hnsw:space": "cosine"}
        )

    def load_and_index():
        coll = get_collection()
        docs, ids, metas = [], [], []

        # HN top stories
        try:
            items = json.load(open(f"{DATA_DIR}/hn_top.json"))
            for item in items[:40]:
                raw_id = str(item.get("objectID") or item.get("id") or "")
                doc_id = f"hn_{raw_id}"
                text = f"{item.get('title','')} {item.get('url','')}".strip()
                if text and doc_id not in ids:
                    docs.append(text); ids.append(doc_id)
                    metas.append({"source": "hackernews", "url": item.get("url",""), "title": item.get("title","")})
        except Exception:
            pass

        # Tech news
        try:
            raw = json.load(open(f"{DATA_DIR}/tech_news_latest.json"))
            stories = raw.get("hn_stories", raw) if isinstance(raw, dict) else raw
            for item in stories[:40]:
                raw_id = str(item.get("id") or item.get("objectID") or "")
                doc_id = f"tech_{raw_id}"
                text = f"{item.get('title','')} {item.get('url','')}".strip()
                if text and doc_id not in ids:
                    docs.append(text); ids.append(doc_id)
                    metas.append({"source": "technews", "url": item.get("url",""), "title": item.get("title","")})
        except Exception:
            pass

        # GitHub trending
        try:
            items = json.load(open(f"{DATA_DIR}/github_trending.json"))
            for item in items[:40]:
                name = item.get("name","")
                doc_id = f"gh_{name.replace('/','_').replace(' ','_')}"
                text = f"{name} {item.get('description','')}".strip()
                if text and doc_id not in ids:
                    docs.append(text); ids.append(doc_id)
                    metas.append({"source": "github", "url": item.get("url",""), "title": name,
                                  "desc": item.get("description","")})
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
            coll.upsert(documents=docs, ids=ids, metadatas=metas)
        return coll.count()

    # Do initial indexing synchronously BEFORE starting the search server
    set_agent(aid, status="starting", task="Indexing data sources...")
    try:
        total = load_and_index()
        set_agent(aid, status="starting", task=f"Indexed {total} items, starting search server...")
    except Exception as e:
        set_agent(aid, status="error", task=f"Initial index failed: {e}")
        return

    # Tiny HTTP search server — opens a fresh client per request for consistency
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
                try:
                    cnt = get_collection().count()
                except Exception:
                    cnt = 0
                self.wfile.write(json.dumps({
                    "error": "?q= required",
                    "total_indexed": cnt,
                    "usage": "GET http://localhost:5051/?q=your+query&n=5"
                }).encode()); return
            try:
                coll = get_collection()
                cnt = coll.count()
                if cnt == 0:
                    self.wfile.write(json.dumps({"query": q, "results": [], "total_indexed": 0}).encode())
                    return
                n = min(max(n, 1), min(15, cnt))
                results = coll.query(query_texts=[q], n_results=n)
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
                    "total_indexed": cnt
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

    cycle = 1
    total = get_collection().count()
    set_agent(aid, status="active", progress=99,
              task=f"{total} items indexed | semantic search: :5051 | cycle #{cycle}")

    while True:
        time.sleep(600)
        try:
            cycle += 1
            total = load_and_index()
            set_agent(aid, status="active", progress=99,
                      task=f"{total} items indexed | semantic search: :5051 | cycle #{cycle}")
        except Exception as e:
            set_agent(aid, status="error", task=f"Re-index error: {e}")
'''

payload = {
    "agent_id": "memoryagent",
    "name": "MemoryAgent",
    "role": "Semantic Memory & Search (ChromaDB)",
    "emoji": "\U0001f9e0",
    "color": "#a855f7",
    "code": AGENT_CODE,
}

resp = requests.post("http://localhost:5050/api/agent/upgrade",
                     json=payload, timeout=15)
print("Status:", resp.status_code)
print("Response:", resp.json())

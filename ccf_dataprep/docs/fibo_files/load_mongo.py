#!/usr/bin/env python3
import json
from pathlib import Path
from pymongo import MongoClient

client = MongoClient("mongodb://192.168.4.76:27017")
db = client["fibo"]

def load_jsonl(path, collection_name):
    coll = db[collection_name]
    coll.drop()
    docs = []
    with Path(path).open() as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    if docs:
        coll.insert_many(docs)
    print(f"{collection_name}: inserted {len(docs)} docs")

load_jsonl("mongo-entities.json", "entities")
load_jsonl("mongo-relationships.json", "relationships")

print("entities count:", db.entities.count_documents({}))
print("relationships count:", db.relationships.count_documents({}))
print("sample entity:", db.entities.find_one())
print("sample relationship:", db.relationships.find_one())

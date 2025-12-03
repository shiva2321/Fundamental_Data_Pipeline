from __future__ import annotations

import logging
from typing import Optional, Any, Dict, Iterable, List
from datetime import datetime, timezone

try:
    from pymongo import MongoClient, ASCENDING, errors
except ImportError as e:
    raise ImportError("pymongo is required for MongoDB functionality. Install with `pip install pymongo`") from e

logger = logging.getLogger("pipeline")


class MongoConnectionError(Exception):
    pass


class MongoWrapper:
    """
    Thin convenience wrapper around pymongo for this pipeline.

    Features:
      - Lazy connection
      - Optional index helpers
      - Upsert helpers
      - Simple bulk write abstraction
    """
    def __init__(
        self,
        uri: str,
        database: str,
        app_name: str = "polygon-pipeline",
        connect_timeout_ms: int = 10_000,
        server_selection_timeout_ms: int = 10_000,
    ):
        self.uri = uri
        self.database_name = database
        self.app_name = app_name
        self._client: Optional[MongoClient] = None
        self._db = None
        self._opts = {
            "appname": app_name,
            "connectTimeoutMS": connect_timeout_ms,
            "serverSelectionTimeoutMS": server_selection_timeout_ms,
        }

    # --- internal ---
    def _ensure(self):
        if self._client is None:
            logger.info("Connecting to MongoDB %s", self.uri)
            try:
                self._client = MongoClient(self.uri, **self._opts)
                # Trigger a lightweight server selection
                self._client.admin.command("ping")
            except errors.PyMongoError as e:
                raise MongoConnectionError(f"Failed to connect/ping MongoDB: {e}") from e
            self._db = self._client[self.database_name]
        return self._db

    # --- Property to expose database ---
    @property
    def db(self):
        """Get the database instance."""
        return self._ensure()

    # --- public API ---
    def collection(self, name: str):
        return self._ensure()[name]

    def upsert_one(self, collection: str, filter_: Dict[str, Any], doc: Dict[str, Any]):
        col = self.collection(collection)
        doc["_updated_at"] = datetime.now(timezone.utc).isoformat()
        res = col.update_one(filter_, {"$set": doc}, upsert=True)
        logger.debug("Upsert one matched=%s modified=%s upserted=%s",
                     res.matched_count, res.modified_count, res.upserted_id)
        return res

    def insert_many_dedup(
        self,
        collection: str,
        docs: List[Dict[str, Any]],
        dedup_key: Optional[str] = None,
        ordered: bool = False,
        ignore_duplicates: bool = True,
    ):
        """
        Insert many documents with optional in-batch de-duplication and duplicate ignore.
        """
        if not docs:
            return {"inserted": 0}
        col = self.collection(collection)

        # In-batch dedup
        # Build a dict keyed by dedup_key if provided
        if dedup_key:
            tmp = {}
            for d in docs:
                if dedup_key not in d:
                    raise ValueError(f"Document missing dedup_key {dedup_key}: {d}")
                tmp[d[dedup_key]] = d
            docs = list(tmp.values())

        for d in docs:
            d.setdefault("_created_at", datetime.now(timezone.utc).isoformat())

        try:
            res = col.insert_many(docs, ordered=ordered)
            inserted = len(res.inserted_ids)
        except errors.BulkWriteError as e:
            if not ignore_duplicates:
                raise
            # Count only truly inserted docs
            details = e.details or {}
            write_errors = details.get("writeErrors", [])
            dup_codes = {11000, 11001}
            dup_count = sum(1 for we in write_errors if we.get("code") in dup_codes)
            inserted = len(docs) - dup_count
            logger.warning("Bulk insert had %s duplicate key errors (%s inserted).",
                           dup_count, inserted)
        return {"inserted": inserted}

    def find(self, collection: str, filter_: Dict[str, Any], projection: Optional[Dict[str, int]] = None, limit: int = 0):
        col = self.collection(collection)
        return list(col.find(filter_, projection, limit=limit))

    def find_one(self, collection: str, filter_: Dict[str, Any], projection: Optional[Dict[str, int]] = None):
        """Find a single document matching the filter."""
        col = self.collection(collection)
        return col.find_one(filter_, projection)

    def close(self):
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed.")
            self._client = None
            self._db = None

    def replace_one(self, collection: str, query: Dict[str, Any], document: Dict[str, Any], upsert: bool = False):
        col = self.collection(collection)
        document["_updated_at"] = datetime.now(timezone.utc).isoformat()
        res = col.replace_one(query, document, upsert=upsert)
        logger.debug("Replace one matched=%s modified=%s upserted=%s",
                     res.matched_count, res.modified_count, res.upserted_id)
        return res

    def update_one(self, collection: str, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        col = self.collection(collection)
        if "$set" in update:
            update["$set"]["_updated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            update["$set"] = {"_updated_at": datetime.now(timezone.utc).isoformat()}
        res = col.update_one(query, update, upsert=upsert)
        logger.debug("Update one matched=%s modified=%s upserted=%s",
                     res.matched_count, res.modified_count, res.upserted_id)
        return res

    def count_documents(self, collection: str, filter_: Dict[str, Any]):
        """Count documents in a collection that match a filter."""
        col = self.collection(collection)
        return col.count_documents(filter_)

    def distinct(self, collection: str, field: str, filter_: Optional[Dict[str, Any]] = None):
        """Return distinct values for a field in a collection."""
        col = self.collection(collection)
        if filter_:
            return col.distinct(field, filter_)
        return col.distinct(field)

    def aggregate(self, collection: str, pipeline: List[Dict[str, Any]]):
        """Perform an aggregation pipeline on a collection."""
        col = self.collection(collection)
        return list(col.aggregate(pipeline))

    def list_collection_names(self):
        db = self._ensure()
        return db.list_collection_names()

    def create_collection(self, collection_name: str):
        """Create a new collection in the database."""
        db = self._ensure()
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
        return db[collection_name]

    def drop_collection(self, collection_name: str):
        """Drop a collection from the database."""
        db = self._ensure()
        db.drop_collection(collection_name)
        logger.info("Dropped collection %s", collection_name)

    def collection_exists(self, collection_name: str):
        db = self._ensure()
        return collection_name in db.list_collection_names()

    def delete_one(self, collection_name: str, filter_: Dict[str, Any]):
        """Delete a single document matching the filter."""
        col = self.collection(collection_name)
        res = col.delete_one(filter_)
        logger.debug("Delete one deleted=%s", res.deleted_count)
        return res

    def delete_many(self, collection_name: str, filter_: Dict[str, Any]):
        """Delete multiple documents matching the filter."""
        col = self.collection(collection_name)
        res = col.delete_many(filter_)
        logger.debug("Delete many deleted=%s", res.deleted_count)
        return res

    def insert_one(self, collection: str, document: Dict[str, Any]):
        """Insert a single document."""
        col = self.collection(collection)
        document.setdefault("_created_at", datetime.now(timezone.utc).isoformat())
        res = col.insert_one(document)
        logger.debug("Insert one inserted_id=%s", res.inserted_id)
        return res

    def insert_many(self, collection: str, documents: List[Dict[str, Any]], ordered: bool = False):
        """Insert multiple documents."""
        if not documents:
            return {"inserted": 0}
        col = self.collection(collection)
        for d in documents:
            d.setdefault("_created_at", datetime.now(timezone.utc).isoformat())
        res = col.insert_many(documents, ordered=ordered)
        return {"inserted": len(res.inserted_ids)}

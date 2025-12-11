"""
Migration helper: copy documents from old collection 'profiles' to new collection name set in config.

Usage:
    python tools/migrate_profiles_collection.py --dry-run
    python tools/migrate_profiles_collection.py --commit

It reads `config/config.yaml` to get MongoDB URI and target collection name.
"""
import argparse
import yaml
from pymongo import MongoClient

CONFIG_PATH = "config/config.yaml"
OLD_COLLECTION = "profiles"


def load_config(path=CONFIG_PATH):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def migrate(dry_run=True):
    cfg = load_config()
    mongo_cfg = cfg.get('mongodb', {})
    uri = mongo_cfg.get('uri', 'mongodb://localhost:27017')
    db_name = mongo_cfg.get('db_name', 'Entities')
    target = cfg.get('collections', {}).get('profiles', 'Fundamental_Data_Pipeline')

    client = MongoClient(uri)
    db = client[db_name]

    src = db[OLD_COLLECTION]
    dst = db[target]

    total = src.count_documents({})
    print(f"Found {total} documents in source collection '{OLD_COLLECTION}'.")
    if total == 0:
        print("Nothing to migrate.")
        return

    if dry_run:
        sample = src.find().limit(5)
        print("Sample documents (first 5):")
        for d in sample:
            print(d)
        print("Dry run: no changes made.")
        return

    # Perform migration in batches
    batch_size = 1000
    copied = 0
    cursor = src.find({})
    batch = []
    for doc in cursor:
        # Remove _id to avoid duplicates when inserting into new collection
        old_id = doc.pop('_id', None)
        batch.append(doc)
        if len(batch) >= batch_size:
            dst.insert_many(batch)
            copied += len(batch)
            print(f"Copied {copied}/{total}")
            batch = []

    if batch:
        dst.insert_many(batch)
        copied += len(batch)
        print(f"Copied {copied}/{total}")

    print(f"Migration complete. Copied {copied} documents to '{target}' collection.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate profiles collection to new collection name')
    parser.add_argument('--commit', action='store_true', help='Perform migration (default is dry-run)')
    args = parser.parse_args()

    migrate(dry_run=not args.commit)


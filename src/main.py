# Standard Packages
import sys
import pathlib
from typing import Optional

# External Packages
import uvicorn
from fastapi import FastAPI

# Internal Packages
from search_type import asymmetric, symmetric_ledger, image_search
from utils.helpers import get_from_dict
from utils.cli import cli


app = FastAPI()


@app.get('/search')
def search(q: str, n: Optional[int] = 5, t: Optional[str] = None):
    if q is None or q == '':
        print(f'No query param (q) passed in API call to initiate search')
        return {}

    user_query = q
    results_count = n

    if (t == 'notes' or t == None) and notes_search_enabled:
        # query notes
        hits = asymmetric.query_notes(
            user_query,
            corpus_embeddings,
            entries,
            bi_encoder,
            cross_encoder,
            top_k)

        # collate and return results
        return asymmetric.collate_results(hits, entries, results_count)

    if (t == 'music' or t == None) and music_search_enabled:
        # query music library
        hits = asymmetric.query_notes(
            user_query,
            song_embeddings,
            songs,
            song_encoder,
            song_cross_encoder,
            song_top_k)

        # collate and return results
        return asymmetric.collate_results(hits, songs, results_count)

    if (t == 'ledger' or t == None) and ledger_search_enabled:
        # query transactions
        hits = symmetric_ledger.query_transactions(
            user_query,
            transaction_embeddings,
            transactions,
            symmetric_encoder,
            symmetric_cross_encoder)

        # collate and return results
        return symmetric_ledger.collate_results(hits, transactions, results_count)

    if (t == 'image' or t == None) and image_search_enabled:
        # query transactions
        hits = image_search.query_images(
            user_query,
            image_embeddings,
            image_metadata_embeddings,
            image_encoder,
            results_count,
            args.verbose)

        # collate and return results
        return image_search.collate_results(
            hits,
            image_names,
            image_config['input-directory'],
            results_count)

    else:
        return {}


@app.get('/regenerate')
def regenerate(t: Optional[str] = None):
    if (t == 'notes' or t == None) and notes_search_enabled:
        # Extract Entries, Generate Embeddings
        global corpus_embeddings
        global entries
        entries, corpus_embeddings, _, _, _ = asymmetric.setup(
            org_config['input-files'],
            org_config['input-filter'],
            pathlib.Path(org_config['compressed-jsonl']),
            pathlib.Path(org_config['embeddings-file']),
            regenerate=True,
            verbose=args.verbose)

    if (t == 'music' or t == None) and music_search_enabled:
        # Extract Entries, Generate Song Embeddings
        global song_embeddings
        global songs
        songs, song_embeddings, _, _, _ = asymmetric.setup(
            song_config['input-files'],
            song_config['input-filter'],
            pathlib.Path(song_config['compressed-jsonl']),
            pathlib.Path(song_config['embeddings-file']),
            regenerate=True,
            verbose=args.verbose)

    if (t == 'ledger' or t == None) and ledger_search_enabled:
        # Extract Entries, Generate Embeddings
        global transaction_embeddings
        global transactions
        transactions, transaction_embeddings, _, _, _ = symmetric_ledger.setup(
            ledger_config['input-files'],
            ledger_config['input-filter'],
            pathlib.Path(ledger_config['compressed-jsonl']),
            pathlib.Path(ledger_config['embeddings-file']),
            regenerate=True,
            verbose=args.verbose)

    if (t == 'image' or t == None) and image_search_enabled:
        # Extract Images, Generate Embeddings
        global image_embeddings
        global image_metadata_embeddings
        global image_names

        image_names, image_embeddings, image_metadata_embeddings, _ = image_search.setup(
            pathlib.Path(image_config['input-directory']),
            pathlib.Path(image_config['embeddings-file']),
            regenerate=True,
            verbose=args.verbose)

    return {'status': 'ok', 'message': 'regeneration completed'}


if __name__ == '__main__':
    args = cli(sys.argv[1:])

    # Initialize Org Notes Search
    org_config = get_from_dict(args.config, 'content-type', 'org')
    notes_search_enabled = False
    if org_config and ('input-files' in org_config or 'input-filter' in org_config):
        notes_search_enabled = True
        entries, corpus_embeddings, bi_encoder, cross_encoder, top_k = asymmetric.setup(
            org_config['input-files'],
            org_config['input-filter'],
            pathlib.Path(org_config['compressed-jsonl']),
            pathlib.Path(org_config['embeddings-file']),
            args.regenerate,
            args.verbose)

    # Initialize Org Music Search
    song_config = get_from_dict(args.config, 'content-type', 'music')
    music_search_enabled = False
    if song_config and ('input-files' in song_config or 'input-filter' in song_config):
        music_search_enabled = True
        songs, song_embeddings, song_encoder, song_cross_encoder, song_top_k = asymmetric.setup(
            song_config['input-files'],
            song_config['input-filter'],
            pathlib.Path(song_config['compressed-jsonl']),
            pathlib.Path(song_config['embeddings-file']),
            args.regenerate,
            args.verbose)

    # Initialize Ledger Search
    ledger_config = get_from_dict(args.config, 'content-type', 'ledger')
    ledger_search_enabled = False
    if ledger_config and ('input-files' in ledger_config or 'input-filter' in ledger_config):
        ledger_search_enabled = True
        transactions, transaction_embeddings, symmetric_encoder, symmetric_cross_encoder, _ = symmetric_ledger.setup(
            ledger_config['input-files'],
            ledger_config['input-filter'],
            pathlib.Path(ledger_config['compressed-jsonl']),
            pathlib.Path(ledger_config['embeddings-file']),
            args.regenerate,
            args.verbose)

    # Initialize Image Search
    image_config = get_from_dict(args.config, 'content-type', 'image')
    image_search_enabled = False
    if image_config and 'input-directory' in image_config:
        image_search_enabled = True
        image_names, image_embeddings, image_metadata_embeddings, image_encoder = image_search.setup(
            pathlib.Path(image_config['input-directory']),
            pathlib.Path(image_config['embeddings-file']),
            batch_size=image_config['batch-size'],
            regenerate=args.regenerate,
            use_xmp_metadata={'yes': True, 'no': False}[image_config['use-xmp-metadata']],
            verbose=args.verbose)

    # Start Application Server
    uvicorn.run(app)

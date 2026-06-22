"""Load knowledge_base/ files into ChromaDB with BGE-M3 embeddings.

Collection: ``psychology_kb_bgem3`` (1024-dim BGE-M3).

The old ``psychology_kb`` collection (1536-dim OpenAI vectors) is left in
place so a rollback is one env-var flip away — see
``CHROMA_COLLECTION_NAME`` in settings.
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Load .txt and .pdf files from knowledge_base/ into ChromaDB (BGE-M3 embeddings)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Drop the target collection before re-loading',
        )
        parser.add_argument(
            '--device',
            default='cpu',
            help='Inference device for BGE-M3 (cpu / cuda). Default: cpu.',
        )

    def handle(self, *args, **options):
        from langchain_chroma import Chroma
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain.schema import Document

        from api.services.llm.embeddings import BgeM3Embeddings

        kb_dir = os.path.join(settings.BASE_DIR, 'knowledge_base')
        if not os.path.exists(kb_dir):
            self.stderr.write(self.style.ERROR(f'knowledge_base/ not found at {kb_dir}'))
            return

        collection_name = getattr(settings, 'CHROMA_COLLECTION_NAME', 'psychology_kb_bgem3')
        device = options['device']

        documents = []
        for filename in os.listdir(kb_dir):
            filepath = os.path.join(kb_dir, filename)
            if filename.endswith('.txt'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()
                documents.append(Document(page_content=text, metadata={'source': filename}))
                self.stdout.write(f'Loaded: {filename}')

            elif filename.endswith('.pdf'):
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(filepath)
                    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
                    documents.append(Document(page_content=text, metadata={'source': filename}))
                    self.stdout.write(f'Loaded: {filename}')
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f'Failed to load {filename}: {e}'))

        if not documents:
            self.stderr.write(self.style.WARNING('No documents found in knowledge_base/'))
            return

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(documents)
        self.stdout.write(f'Split into {len(chunks)} chunks')

        embeddings = BgeM3Embeddings(device=device)

        if options['reset']:
            try:
                import chromadb
                client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
                client.delete_collection(collection_name)
                self.stdout.write(self.style.WARNING(f'Reset: deleted collection {collection_name}'))
            except Exception as e:
                self.stdout.write(f'Reset skipped ({e})')

        self.stdout.write(f'Embedding {len(chunks)} chunks with BGE-M3 (device={device})…')
        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_name=collection_name,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Successfully loaded {len(chunks)} chunks into ChromaDB collection {collection_name}'
        ))

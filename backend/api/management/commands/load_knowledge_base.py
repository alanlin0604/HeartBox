import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Load .txt and .pdf files from knowledge_base/ into ChromaDB'

    def handle(self, *args, **options):
        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain.schema import Document

        kb_dir = os.path.join(settings.BASE_DIR, 'knowledge_base')
        if not os.path.exists(kb_dir):
            self.stderr.write(self.style.ERROR(f'knowledge_base/ not found at {kb_dir}'))
            return

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

        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(documents)
        self.stdout.write(f'Split into {len(chunks)} chunks')

        # Store in ChromaDB
        embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_name='psychology_kb',
        )
        self.stdout.write(self.style.SUCCESS(
            f'Successfully loaded {len(chunks)} chunks into ChromaDB'
        ))

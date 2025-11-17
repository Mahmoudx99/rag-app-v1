"""
PDF processing service - extracts and chunks text from PDFs
Adapted from enhanced_pdf_extractor.py (plain mode only)
"""
import re
import hashlib
import logging
from typing import List, Dict, Any, Optional, Iterator, Generator
from pathlib import Path
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.layout import LAParams, LTTextContainer

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF text extraction and chunking"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize PDF processor

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract metadata from PDF

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with metadata
        """
        metadata = {
            "title": None,
            "author": None,
            "num_pages": 0,
            "file_size": 0
        }

        try:
            with open(pdf_path, 'rb') as fh:
                parser = PDFParser(fh)
                document = PDFDocument(parser)

                metadata["num_pages"] = len(list(PDFPage.create_pages(document)))
                metadata["file_size"] = Path(pdf_path).stat().st_size

                if document.info:
                    info = document.info[0] if document.info else {}

                    if 'Title' in info:
                        title = info['Title']
                        if isinstance(title, bytes):
                            title = title.decode('utf-8', errors='ignore')
                        metadata["title"] = title

                    if 'Author' in info:
                        author = info['Author']
                        if isinstance(author, bytes):
                            author = author.decode('utf-8', errors='ignore')
                        metadata["author"] = author

            logger.info(f"Extracted metadata: {metadata['num_pages']} pages")
            return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return metadata

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract plain text from PDF

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        try:
            logger.info(f"Extracting text from: {pdf_path}")
            raw_text = extract_text(pdf_path, laparams=LAParams())
            processed_text = self._post_process_text(raw_text)
            logger.info(f"Extracted {len(processed_text)} characters")
            return processed_text
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            raise

    def extract_text_with_pages(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF page by page

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dicts with page_number and text for each page
        """
        try:
            logger.info(f"Extracting text page-by-page from: {pdf_path}")
            pages_text = []

            for page_num, page_layout in enumerate(extract_pages(pdf_path, laparams=LAParams()), start=1):
                page_text = []

                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        page_text.append(element.get_text())

                text = ''.join(page_text)
                processed_text = self._post_process_text(text)

                if processed_text.strip():
                    pages_text.append({
                        "page_number": page_num,
                        "text": processed_text
                    })

            logger.info(f"Extracted text from {len(pages_text)} pages")
            return pages_text

        except Exception as e:
            logger.error(f"Error extracting text with pages: {e}")
            raise

    def _post_process_text(self, text: str) -> str:
        """Post-process extracted text"""
        if not text:
            return ""

        paragraphs = []
        current_paragraph = []

        for line in text.split('\n'):
            line = line.strip()
            if not line:
                if current_paragraph:
                    paragraph = ' '.join(current_paragraph).strip()
                    if len(paragraph) >= 50:
                        paragraphs.append(paragraph)
                    current_paragraph = []
            else:
                # Clean up line
                line = re.sub(r'\s+', ' ', line)
                line = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', line)
                if line:
                    current_paragraph.append(line)

        if current_paragraph:
            paragraph = ' '.join(current_paragraph).strip()
            if len(paragraph) >= 50:
                paragraphs.append(paragraph)

        return '\n\n'.join(paragraphs)

    def chunk_text(self, text: str, source: str) -> List[Dict[str, Any]]:
        """
        Chunk text into paragraphs

        Args:
            text: Text to chunk
            source: Source filename

        Returns:
            List of chunks with metadata
        """
        if not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []

        for para in paragraphs:
            para_length = len(para)

            if para_length <= self.chunk_size:
                # Paragraph fits in one chunk
                chunks.append({
                    "text": para,
                    "char_count": para_length,
                    "word_count": len(para.split())
                })
            else:
                # Split large paragraph by sentences
                sentences = self._split_sentences(para)
                current_chunk = []
                current_length = 0

                for sentence in sentences:
                    sentence_length = len(sentence)

                    if current_length + sentence_length > self.chunk_size and current_chunk:
                        # Save current chunk
                        chunk_text = ' '.join(current_chunk)
                        chunks.append({
                            "text": chunk_text,
                            "char_count": len(chunk_text),
                            "word_count": len(chunk_text.split())
                        })
                        current_chunk = []
                        current_length = 0

                    current_chunk.append(sentence)
                    current_length += sentence_length

                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append({
                        "text": chunk_text,
                        "char_count": len(chunk_text),
                        "word_count": len(chunk_text.split())
                    })

        # Add IDs and metadata
        final_chunks = []
        source_hash = hashlib.md5(source.encode()).hexdigest()[:8]

        for i, chunk in enumerate(chunks):
            content_hash = hashlib.md5(chunk["text"].encode()).hexdigest()[:12]
            chunk_id = f"chunk_{source_hash}_{i:04d}_{content_hash}"

            final_chunks.append({
                "id": chunk_id,
                "content": chunk["text"],
                "metadata": {
                    "chunk_index": i,
                    "char_count": chunk["char_count"],
                    "word_count": chunk["word_count"],
                    "source": source
                }
            })

        logger.info(f"Created {len(final_chunks)} chunks")
        return final_chunks

    def chunk_text_with_pages(self, pages_text: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
        """
        Chunk text from pages while maintaining page number information

        Args:
            pages_text: List of dicts with page_number and text
            source: Source filename

        Returns:
            List of chunks with metadata including page numbers
        """
        if not pages_text:
            logger.warning("Empty pages_text provided for chunking")
            return []

        all_chunks = []
        source_hash = hashlib.md5(source.encode()).hexdigest()[:8]
        global_chunk_index = 0

        for page_data in pages_text:
            page_num = page_data["page_number"]
            text = page_data["text"]

            if not text.strip():
                continue

            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

            for para in paragraphs:
                para_length = len(para)

                if para_length <= self.chunk_size:
                    # Paragraph fits in one chunk
                    chunk_text = para
                    content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:12]
                    chunk_id = f"chunk_{source_hash}_{global_chunk_index:04d}_{content_hash}"

                    all_chunks.append({
                        "id": chunk_id,
                        "content": chunk_text,
                        "metadata": {
                            "chunk_index": global_chunk_index,
                            "page_number": page_num,
                            "char_count": para_length,
                            "word_count": len(chunk_text.split()),
                            "source": source
                        }
                    })
                    global_chunk_index += 1

                else:
                    # Split large paragraph by sentences
                    sentences = self._split_sentences(para)
                    current_chunk = []
                    current_length = 0

                    for sentence in sentences:
                        sentence_length = len(sentence)

                        if current_length + sentence_length > self.chunk_size and current_chunk:
                            # Save current chunk
                            chunk_text = ' '.join(current_chunk)
                            content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:12]
                            chunk_id = f"chunk_{source_hash}_{global_chunk_index:04d}_{content_hash}"

                            all_chunks.append({
                                "id": chunk_id,
                                "content": chunk_text,
                                "metadata": {
                                    "chunk_index": global_chunk_index,
                                    "page_number": page_num,
                                    "char_count": len(chunk_text),
                                    "word_count": len(chunk_text.split()),
                                    "source": source
                                }
                            })
                            global_chunk_index += 1
                            current_chunk = []
                            current_length = 0

                        current_chunk.append(sentence)
                        current_length += sentence_length

                    if current_chunk:
                        chunk_text = ' '.join(current_chunk)
                        content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:12]
                        chunk_id = f"chunk_{source_hash}_{global_chunk_index:04d}_{content_hash}"

                        all_chunks.append({
                            "id": chunk_id,
                            "content": chunk_text,
                            "metadata": {
                                "chunk_index": global_chunk_index,
                                "page_number": page_num,
                                "char_count": len(chunk_text),
                                "word_count": len(chunk_text.split()),
                                "source": source
                            }
                        })
                        global_chunk_index += 1

        logger.info(f"Created {len(all_chunks)} chunks from {len(pages_text)} pages")
        return all_chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Handle common abbreviations
        text = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr|Inc|Ltd|Co)\.\s', r'\1<PERIOD> ', text)

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        # Restore abbreviations
        sentences = [s.replace('<PERIOD>', '.').strip() for s in sentences if s.strip()]
        return sentences

    def process_pdf(self, pdf_path: str, preserve_page_numbers: bool = True) -> Dict[str, Any]:
        """
        Process PDF: extract metadata, text, and create chunks

        Args:
            pdf_path: Path to PDF file
            preserve_page_numbers: If True, extract page-by-page and preserve page numbers in chunks

        Returns:
            Dictionary with metadata, text, and chunks
        """
        try:
            filename = Path(pdf_path).name

            # Extract metadata
            metadata = self.extract_metadata(pdf_path)

            if preserve_page_numbers:
                # Extract text page by page
                pages_text = self.extract_text_with_pages(pdf_path)

                # Combine all page text for backward compatibility
                text = '\n\n'.join([page["text"] for page in pages_text])

                # Create chunks with page numbers
                chunks = self.chunk_text_with_pages(pages_text, filename)
            else:
                # Extract text all at once (old method)
                text = self.extract_text(pdf_path)

                # Create chunks without page numbers
                chunks = self.chunk_text(text, filename)

            return {
                "success": True,
                "metadata": metadata,
                "text": text,
                "chunks": chunks,
                "num_chunks": len(chunks)
            }

        except Exception as e:
            logger.error(f"Error processing PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def process_pdf_streaming(self, pdf_path: str) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
        """
        Process PDF with streaming: yields chunks progressively as pages are processed.

        This allows embeddings to start processing chunks before the entire PDF is done.

        Args:
            pdf_path: Path to PDF file

        Yields:
            Individual chunk dictionaries with id, content, and metadata

        Returns:
            Final summary dict with metadata and statistics (via generator return)
        """
        try:
            filename = Path(pdf_path).name
            source_hash = hashlib.md5(filename.encode()).hexdigest()[:8]

            # Extract metadata first
            metadata = self.extract_metadata(pdf_path)
            logger.info(f"Starting streaming processing of {filename} ({metadata['num_pages']} pages)")

            global_chunk_index = 0
            total_text_length = 0

            # Process PDF page by page, yielding chunks as we go
            for page_num, page_layout in enumerate(extract_pages(pdf_path, laparams=LAParams()), start=1):
                # Extract text from this page
                page_text = []
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        page_text.append(element.get_text())

                text = ''.join(page_text)
                processed_text = self._post_process_text(text)

                if not processed_text.strip():
                    continue

                total_text_length += len(processed_text)

                # Chunk this page's text
                paragraphs = [p.strip() for p in processed_text.split('\n\n') if p.strip()]

                for para in paragraphs:
                    para_length = len(para)

                    if para_length <= self.chunk_size:
                        # Paragraph fits in one chunk
                        chunk_text = para
                        content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:12]
                        chunk_id = f"chunk_{source_hash}_{global_chunk_index:04d}_{content_hash}"

                        chunk = {
                            "id": chunk_id,
                            "content": chunk_text,
                            "metadata": {
                                "chunk_index": global_chunk_index,
                                "page_number": page_num,
                                "char_count": para_length,
                                "word_count": len(chunk_text.split()),
                                "source": filename
                            }
                        }
                        yield chunk
                        global_chunk_index += 1

                    else:
                        # Split large paragraph by sentences
                        sentences = self._split_sentences(para)
                        current_chunk = []
                        current_length = 0

                        for sentence in sentences:
                            sentence_length = len(sentence)

                            if current_length + sentence_length > self.chunk_size and current_chunk:
                                # Yield current chunk
                                chunk_text = ' '.join(current_chunk)
                                content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:12]
                                chunk_id = f"chunk_{source_hash}_{global_chunk_index:04d}_{content_hash}"

                                chunk = {
                                    "id": chunk_id,
                                    "content": chunk_text,
                                    "metadata": {
                                        "chunk_index": global_chunk_index,
                                        "page_number": page_num,
                                        "char_count": len(chunk_text),
                                        "word_count": len(chunk_text.split()),
                                        "source": filename
                                    }
                                }
                                yield chunk
                                global_chunk_index += 1
                                current_chunk = []
                                current_length = 0

                            current_chunk.append(sentence)
                            current_length += sentence_length

                        if current_chunk:
                            chunk_text = ' '.join(current_chunk)
                            content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:12]
                            chunk_id = f"chunk_{source_hash}_{global_chunk_index:04d}_{content_hash}"

                            chunk = {
                                "id": chunk_id,
                                "content": chunk_text,
                                "metadata": {
                                    "chunk_index": global_chunk_index,
                                    "page_number": page_num,
                                    "char_count": len(chunk_text),
                                    "word_count": len(chunk_text.split()),
                                    "source": filename
                                }
                            }
                            yield chunk
                            global_chunk_index += 1

                logger.debug(f"Processed page {page_num}, total chunks so far: {global_chunk_index}")

            logger.info(f"Streaming processing complete: {global_chunk_index} chunks from {metadata['num_pages']} pages")

            # Return final summary (accessible via generator.send() or as StopIteration value)
            return {
                "success": True,
                "metadata": metadata,
                "num_chunks": global_chunk_index,
                "total_text_length": total_text_length
            }

        except Exception as e:
            logger.error(f"Error in streaming PDF processing: {e}", exc_info=True)
            raise

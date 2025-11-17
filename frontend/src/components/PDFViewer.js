import React, { useState, useEffect, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './PDFViewer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

function PDFViewer({ isOpen, onClose, documentId, pageNumber, highlightText }) {
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(pageNumber || 1);
  const [scale, setScale] = useState(1.0);
  const [pdfDocument, setPdfDocument] = useState(null);
  const [highlights, setHighlights] = useState([]);
  const [pageRendered, setPageRendered] = useState(false);

  const pdfUrl = documentId
    ? `${process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1'}/documents/${documentId}/pdf`
    : null;

  // Reset state when opening with new document or page
  useEffect(() => {
    if (isOpen && pageNumber) {
      setCurrentPage(pageNumber);
      setPageRendered(false); // Reset to trigger re-render and highlighting
      setHighlights([]); // Clear old highlights
    }
  }, [isOpen, pageNumber, documentId]);

  // Also reset when the viewer is closed
  useEffect(() => {
    if (!isOpen) {
      setPageRendered(false);
      setHighlights([]);
      setPdfDocument(null);
    }
  }, [isOpen]);

  const findAndHighlightText = useCallback(async () => {
    if (!pdfDocument || !highlightText || !currentPage || !pageRendered) {
      return; // Don't clear highlights, just wait for conditions to be met
    }

    try {
      // Get first few words - try more words for better matching
      const words = highlightText.trim().split(/\s+/);
      const searchText = words.slice(0, Math.min(5, words.length)).join(' ').toLowerCase();

      if (!searchText || searchText.length < 3) {
        setHighlights([]);
        return;
      }

      const page = await pdfDocument.getPage(currentPage);
      const textContent = await page.getTextContent();
      const viewport = page.getViewport({ scale });

      // Build text from items
      let fullText = '';
      const items = textContent.items;

      items.forEach((item) => {
        fullText += item.str + ' ';
      });

      const fullTextLower = fullText.toLowerCase();

      // Try to find match with decreasing word count for better robustness
      let index = -1;
      let actualSearchText = searchText;

      // Try with 5 words, then 4, 3, 2
      for (let wordCount = Math.min(5, words.length); wordCount >= 2; wordCount--) {
        actualSearchText = words.slice(0, wordCount).join(' ').toLowerCase();
        index = fullTextLower.indexOf(actualSearchText);
        if (index !== -1) break;
      }

      if (index === -1) {
        console.log('No match found for:', actualSearchText);
        setHighlights([]);
        return;
      }

      // Find matching text items
      let charCount = 0;
      const endIndex = index + actualSearchText.length;
      const matchingItems = [];

      for (const item of items) {
        const itemStart = charCount;
        const itemEnd = charCount + item.str.length;

        // Check if this item overlaps with our search text
        if (itemEnd > index && itemStart < endIndex) {
          matchingItems.push(item);
        }

        charCount += item.str.length + 1; // +1 for space
      }

      if (matchingItems.length === 0) {
        console.log('No matching items found in PDF text layer');
        setHighlights([]);
        return;
      }

      // Create highlight rectangles
      const rects = matchingItems.map((item) => {
        const tx = item.transform[4];
        const ty = item.transform[5];
        const itemHeight = item.height;
        const itemWidth = item.width;

        return {
          left: tx,
          top: viewport.height - ty - itemHeight,
          width: itemWidth,
          height: itemHeight,
        };
      });

      setHighlights(rects);
    } catch (error) {
      console.error('Error highlighting:', error);
      setHighlights([]);
    }
  }, [pdfDocument, highlightText, currentPage, scale, pageRendered]);

  useEffect(() => {
    findAndHighlightText();
  }, [findAndHighlightText]);

  const onDocumentLoadSuccess = (pdf) => {
    setNumPages(pdf.numPages);
    setPdfDocument(pdf);
    // Don't reset pageRendered here - let onPageRenderSuccess handle it
  };

  const onPageRenderSuccess = () => {
    // Small delay to ensure PDF.js has finished rendering text layer
    setTimeout(() => {
      setPageRendered(true);
    }, 150);
  };

  // Retry highlighting if it hasn't happened after document loads
  useEffect(() => {
    if (pdfDocument && highlightText && currentPage && highlights.length === 0) {
      // Retry after a delay if no highlights found
      const retryTimer = setTimeout(() => {
        setPageRendered(prev => {
          // Toggle to trigger re-render
          if (prev) {
            findAndHighlightText();
          }
          return prev;
        });
      }, 300);
      return () => clearTimeout(retryTimer);
    }
  }, [pdfDocument, highlightText, currentPage, highlights.length, findAndHighlightText]);

  const goToPrevPage = () => {
    setPageRendered(false);
    setCurrentPage((prev) => Math.max(prev - 1, 1));
  };

  const goToNextPage = () => {
    setPageRendered(false);
    setCurrentPage((prev) => Math.min(prev + 1, numPages));
  };

  const zoomIn = () => {
    setPageRendered(false);
    setScale((prev) => Math.min(prev + 0.2, 3.0));
  };

  const zoomOut = () => {
    setPageRendered(false);
    setScale((prev) => Math.max(prev - 0.2, 0.5));
  };

  if (!isOpen) return null;

  return (
    <div className="pdf-viewer-overlay" onClick={onClose}>
      <div className="pdf-viewer-modal" onClick={(e) => e.stopPropagation()}>
        <div className="pdf-viewer-header">
          <div className="pdf-viewer-controls">
            <button onClick={goToPrevPage} disabled={currentPage <= 1}>
              Previous
            </button>
            <span className="page-info">
              Page {currentPage} of {numPages || '...'}
            </span>
            <button onClick={goToNextPage} disabled={currentPage >= numPages}>
              Next
            </button>

            <div className="zoom-controls">
              <button onClick={zoomOut} disabled={scale <= 0.5}>-</button>
              <span className="zoom-level">{Math.round(scale * 100)}%</span>
              <button onClick={zoomIn} disabled={scale >= 3.0}>+</button>
            </div>
          </div>

          <button className="close-button" onClick={onClose}>✕</button>
        </div>

        <div className="pdf-viewer-content">
          {pdfUrl ? (
            <div className="pdf-container">
              <Document
                file={pdfUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                loading={<div className="loading">Loading PDF...</div>}
                error={<div className="error">Failed to load PDF</div>}
              >
                <div className="page-wrapper">
                  <Page
                    pageNumber={currentPage}
                    scale={scale}
                    renderTextLayer={true}
                    renderAnnotationLayer={true}
                    onRenderSuccess={onPageRenderSuccess}
                  />

                  {/* Highlight overlay */}
                  {highlights.length > 0 && (
                    <div className="highlight-overlay">
                      {highlights.map((rect, idx) => (
                        <div
                          key={idx}
                          className="highlight-box"
                          style={{
                            position: 'absolute',
                            left: `${rect.left}px`,
                            top: `${rect.top}px`,
                            width: `${rect.width}px`,
                            height: `${rect.height}px`,
                            backgroundColor: 'yellow',
                            opacity: 0.4,
                            pointerEvents: 'none',
                          }}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </Document>
            </div>
          ) : (
            <div className="error">No document selected</div>
          )}
        </div>

        {highlightText && (
          <div className="highlight-info">
            <strong>Chunk found:</strong> {highlightText}
          </div>
        )}
      </div>
    </div>
  );
}

export default PDFViewer;

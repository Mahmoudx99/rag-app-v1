import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './PDFViewer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

function PDFViewer({ isOpen, onClose, documentId, pageNumber, highlightText }) {
  const [numPages, setNumPages] = useState(null);
  const [scale, setScale] = useState(1.0);
  const [pdfDocument, setPdfDocument] = useState(null);
  const [highlights, setHighlights] = useState({});
  const [renderedPages, setRenderedPages] = useState(new Set());
  const [currentVisiblePage, setCurrentVisiblePage] = useState(pageNumber || 1);
  const containerRef = useRef(null);
  const pageRefs = useRef({});

  const pdfUrl = documentId
    ? `${process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1'}/documents/${documentId}/pdf`
    : null;

  // Scroll to target page when opening
  useEffect(() => {
    if (isOpen && pageNumber && numPages && pageRefs.current[pageNumber]) {
      // Wait for pages to render before scrolling
      const scrollTimer = setTimeout(() => {
        const targetPage = pageRefs.current[pageNumber];
        if (targetPage && containerRef.current) {
          targetPage.scrollIntoView({ behavior: 'auto', block: 'start' });
          setCurrentVisiblePage(pageNumber);
        }
      }, 500);
      return () => clearTimeout(scrollTimer);
    }
  }, [isOpen, pageNumber, numPages]);

  // Reset state when opening with new document
  useEffect(() => {
    if (isOpen) {
      setHighlights({});
      setRenderedPages(new Set());
      setCurrentVisiblePage(pageNumber || 1);
    }
  }, [isOpen, documentId, pageNumber]);

  // Also reset when the viewer is closed
  useEffect(() => {
    if (!isOpen) {
      setHighlights({});
      setRenderedPages(new Set());
      setPdfDocument(null);
      setNumPages(null);
      pageRefs.current = {};
    }
  }, [isOpen]);

  // Track current visible page on scroll
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !numPages) return;

    const handleScroll = () => {
      const containerTop = container.scrollTop;
      const containerHeight = container.clientHeight;
      const viewCenter = containerTop + containerHeight / 3; // Use top third for better UX

      for (let i = 1; i <= numPages; i++) {
        const pageEl = pageRefs.current[i];
        if (pageEl) {
          const pageTop = pageEl.offsetTop - container.offsetTop;
          const pageBottom = pageTop + pageEl.offsetHeight;

          if (pageTop <= viewCenter && pageBottom > viewCenter) {
            setCurrentVisiblePage(i);
            break;
          }
        }
      }
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [numPages]);

  const findAndHighlightTextOnPage = useCallback(async (targetPage) => {
    if (!pdfDocument || !highlightText || !targetPage) {
      return;
    }

    try {
      // Get first few words - try more words for better matching
      const words = highlightText.trim().split(/\s+/);
      const searchText = words.slice(0, Math.min(5, words.length)).join(' ').toLowerCase();

      if (!searchText || searchText.length < 3) {
        return;
      }

      const page = await pdfDocument.getPage(targetPage);
      const textContent = await page.getTextContent();
      const viewport = page.getViewport({ scale });

      // Build text from items with position tracking
      let fullText = '';
      const items = textContent.items;
      const itemPositions = []; // Track start position of each item in fullText

      items.forEach((item) => {
        itemPositions.push(fullText.length);
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
        return;
      }

      const endIndex = index + actualSearchText.length;

      // Find matching text items and calculate partial highlights
      const rects = [];

      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        const itemStart = itemPositions[i];
        const itemEnd = itemStart + item.str.length;

        // Check if this item overlaps with our search text
        if (itemEnd > index && itemStart < endIndex) {
          const tx = item.transform[4];
          const ty = item.transform[5];
          const itemHeight = item.height;
          const itemWidth = item.width;

          // Calculate partial highlight if text starts or ends within this item
          let highlightLeft = tx;
          let highlightWidth = itemWidth;

          if (item.str.length > 0 && itemWidth > 0) {
            const charWidth = itemWidth / item.str.length;

            // If search text starts within this item
            if (index > itemStart) {
              const charsToSkip = index - itemStart;
              highlightLeft = tx + (charsToSkip * charWidth);
              highlightWidth = itemWidth - (charsToSkip * charWidth);
            }

            // If search text ends within this item
            if (endIndex < itemEnd) {
              const charsToInclude = endIndex - Math.max(index, itemStart);
              highlightWidth = charsToInclude * charWidth;
            }
          }

          rects.push({
            left: highlightLeft,
            top: viewport.height - ty - itemHeight,
            width: Math.max(highlightWidth, 0),
            height: itemHeight,
          });
        }
      }

      if (rects.length === 0) {
        return;
      }

      setHighlights(prev => ({ ...prev, [targetPage]: rects }));
    } catch (error) {
      console.error('Error highlighting page', targetPage, ':', error);
    }
  }, [pdfDocument, highlightText, scale]);

  // Highlight target page when document loads
  useEffect(() => {
    if (pdfDocument && highlightText && pageNumber && renderedPages.has(pageNumber)) {
      findAndHighlightTextOnPage(pageNumber);
    }
  }, [pdfDocument, highlightText, pageNumber, renderedPages, findAndHighlightTextOnPage]);

  const onDocumentLoadSuccess = (pdf) => {
    setNumPages(pdf.numPages);
    setPdfDocument(pdf);
  };

  const onPageRenderSuccess = (pageNum) => {
    setRenderedPages(prev => new Set(prev).add(pageNum));

    // Highlight target page after it renders
    if (pageNum === pageNumber && highlightText) {
      setTimeout(() => {
        findAndHighlightTextOnPage(pageNum);
      }, 150);
    }
  };

  const scrollToPage = (page) => {
    const pageNum = Math.max(1, Math.min(page, numPages || 1));
    if (pageRefs.current[pageNum]) {
      pageRefs.current[pageNum].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const handlePageInputChange = (e) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 1 && value <= numPages) {
      scrollToPage(value);
    }
  };

  const handleSliderChange = (e) => {
    scrollToPage(parseInt(e.target.value, 10));
  };

  const zoomIn = () => {
    setHighlights({});
    setRenderedPages(new Set());
    setScale((prev) => Math.min(prev + 0.2, 3.0));
  };

  const zoomOut = () => {
    setHighlights({});
    setRenderedPages(new Set());
    setScale((prev) => Math.max(prev - 0.2, 0.5));
  };

  if (!isOpen) return null;

  return (
    <div className="pdf-viewer-overlay" onClick={onClose}>
      <div className="pdf-viewer-modal" onClick={(e) => e.stopPropagation()}>
        <div className="pdf-viewer-header">
          <div className="pdf-viewer-controls">
            <div className="page-input-wrapper">
              <span className="page-label">Page</span>
              <input
                type="number"
                min="1"
                max={numPages || 1}
                value={currentVisiblePage}
                onChange={handlePageInputChange}
                className="page-input"
              />
              <span className="page-total">/ {numPages || '...'}</span>
            </div>

            {numPages && numPages > 1 && (
              <div className="page-slider-wrapper">
                <input
                  type="range"
                  min="1"
                  max={numPages}
                  value={currentVisiblePage}
                  onChange={handleSliderChange}
                  className="page-slider"
                />
              </div>
            )}

            <div className="zoom-controls">
              <button onClick={zoomOut} disabled={scale <= 0.5}>−</button>
              <span className="zoom-level">{Math.round(scale * 100)}%</span>
              <button onClick={zoomIn} disabled={scale >= 3.0}>+</button>
            </div>
          </div>

          <button className="close-button" onClick={onClose}>✕</button>
        </div>

        <div className="pdf-viewer-content" ref={containerRef}>
          {pdfUrl ? (
            <div className="pdf-container continuous">
              <Document
                file={pdfUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                loading={<div className="loading">Loading PDF...</div>}
                error={<div className="error">Failed to load PDF</div>}
              >
                {numPages && Array.from({ length: numPages }, (_, index) => {
                  const pageNum = index + 1;
                  return (
                    <div
                      key={pageNum}
                      className="page-wrapper"
                      ref={(el) => (pageRefs.current[pageNum] = el)}
                    >
                      <div className="page-number-label">Page {pageNum}</div>
                      <div className="page-content-wrapper">
                        <Page
                          pageNumber={pageNum}
                          scale={scale}
                          renderTextLayer={true}
                          renderAnnotationLayer={true}
                          onRenderSuccess={() => onPageRenderSuccess(pageNum)}
                        />

                        {/* Highlight overlay for this page */}
                        {highlights[pageNum] && highlights[pageNum].length > 0 && (
                          <div className="highlight-overlay">
                            {highlights[pageNum].map((rect, idx) => (
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
                    </div>
                  );
                })}
              </Document>
            </div>
          ) : (
            <div className="error">No document selected</div>
          )}
        </div>

        {highlightText && (
          <div className="highlight-info">
            <strong>Highlighted chunk on page {pageNumber}:</strong> {highlightText.substring(0, 100)}...
          </div>
        )}
      </div>
    </div>
  );
}

export default PDFViewer;

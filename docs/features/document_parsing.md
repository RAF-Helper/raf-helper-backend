# Document Parsing Pipeline

## Overview
The document parsing pipeline is designed to extract textual content and structural metadata from various educational file formats to enable high-quality RAG (Retrieval-Augmented Generation). Instead of treating documents as flat text, the pipeline organizes content into a hierarchy, allowing the system to retrieve not just small chunks, but entire logical sections (articles, chapters).

## Supported Formats and Parsing Logic

### 1. Microsoft Word (.docx)
- **Structural Detection**: Uses paragraph styles. Paragraphs with styles starting with 'Heading 1', 'Heading 2', or 'Heading 3' are mapped to `level1`, `level2`, and `level3` respectively.
- **Fallback**: If no styles are detected, the parser uses regex patterns to identify numbered sections (e.g., "1. Introduction", "Глава 1") and assigns them to structural levels.
- **Language Support**: Supports English, Russian, and Belarusian.

### 2. PDF (.pdf)
- **Font Analysis**: Uses `pdfplumber` to analyze font sizes and weights. Larger fonts are heuristically mapped to higher structural levels.
- **Document Type Detection**:
    - **Slides**: Detected via aspect ratio (wide) and high image-to-text ratio. Parsed slide-by-slide, treating the first significant text block as the slide title (`level1`).
    - **Books/Articles**: Parsed using font-size analysis to detect headings and section boundaries.
- **Structure**: Continuous text is grouped under the last detected heading.

### 3. Markdown (.md)
- **Structural Detection**: Uses standard Markdown heading syntax (`#`, `##`, `###`) to populate `level1`, `level2`, and `level3`.
- **Implementation**: Explicit markup makes this the most precise structural parser.

### 4. Presentations (.pptx)
- **Structure**: Each slide is treated as a primary unit. The slide title (identified via placeholder shapes) is mapped to `level1`.
- **Content**: All text within the slide is captured as the chunk content.

### 5. Plain Text (.txt)
- **Fallback**: Treats the document as a single structural entity.

## Structural Metadata Model
Each extracted chunk of text is associated with a hierarchy:
- `level1`: Highest level (e.g., Chapter, Section, Slide Title).
- `level2`: Middle level (e.g., Article, Subsection).
- `level3`: Lowest level (e.g., Point, Sub-point).

This metadata is stored in both the Elasticsearch index (for filtering and boosting) and the `DocumentChunk` model.

## Retrieval Pipeline

### `get_materials_fragments` Tool
The tool provides a high-level interface for agents to retrieve materials.

1. **Internal Search**:
    - The system performs a hybrid search (vector similarity + fuzzy text match) in the `Materials Index`.
    - It filters by `document_id`s present in the current chat context.
2. **Web Search Integration**:
    - If `use_web_search` is enabled, the tool concurrently calls the Tavily API with the same query.
3. **Union Logic**:
    - Results from the internal knowledge base and web search are combined into a structured response, clearly separated by headers (`[Internal Knowledge Base]` and `[Web Search Results]`).

### Full Document Retrieval (`return_chunks=False`)
To avoid storing duplicate full-text copies of documents in the database, the system implements a "re-parse on demand" strategy:
- When the agent requests full documents instead of chunks, the system identifies the matching `document_id`s.
- It retrieves the original file from server storage and re-runs the appropriate parser.
- The entire concatenated text of the document is then returned.

## Chunking Strategy
After initial parsing into structural blocks, the `ChunkingService` further refines the content:
- **Recursive Splitting**: Large sections are split into smaller chunks based on a maximum word count.
- **Overlapping**: Each chunk overlaps with its neighbor to preserve semantic context across boundaries.
- **Metadata Preservation**: All structural levels (`level1-3`) and page numbers are preserved for every sub-chunk.

## Future Improvements
- **Summarization**: Implement automated summarization for full documents that exceed the LLM's context window.
- **OCR**: Integrate OCR for PDFs and images to extract text from scanned documents.
- **TOC Extraction**: Use Table of Contents in PDFs to precisely map structural levels.

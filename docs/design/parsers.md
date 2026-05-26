# Parser design

## Overview

Right now we have simplest parsers to test out the system and they don't do any structural parsing.

Current implementation only allows for the simplest document chunking based on the word count.

And capable of supplying references only by pages.

### Supported formats
- Word files (.docx, .doc);
- PDFs (.pdf);
- Slides (.ppt, .pptx);
- Plain text (.txt and default fallback).
_TODO: LaTex, ODF, Markdown_

## Requirements

The system must be able to handle all kinds of educational documents, including, but not limited to:
- Books of all kinds;
- Slides from lectures;
- Papers, articles and abstracts;
- Practical classes support materials;
- Class notes.

For all of that, it must have a way to organize the content into sections (chapters, articles, etc.) to:
- Better data retrieval, so we can supply the whole article instead of just the chunk, but not the whole file;
- Ease the search when the title represents the queried topic;
- Make better references when constructing responses.

The system must provide the most general approach for most docs, using any kind of techniques (font size, styles, regex). But, must:
- Support Russian, Belarusan and English languages;
- Don't mess up the structure if it is not used in the file, so decide based on the documents contents and not the parser involved;
- Use appropriate technique based on the contents, not file extensions (e. g. PDFs and PPTs both can hold slides, but PDF also can hold books, articles or other supplement materials).

## Parser logic description

### DocxParser

Only parses page numbers and treats the whole content as one section. Requires core logic for general docs.

### PDFParser

Only parses page numbers and treats the whole content as one section. Requires core logic for general docs. But slides also may be in form of a PDF. So distinction mechanism is needed.

### PptxParser

Parses the whole text and divides only by slides as 1st level.

This is acceptable approach for PoC. But slides may have more structure to them, adding sections, review of many topics in one file and that may be really helpful.

### TextParser

Parses the whole document as 1 structural entity.

This is acceptable behavior for text and fallback parser and for now doesn't require modification.


## Planned improvements to the parsers

### Overall Strategy

The goal is to move from "whole document as one section" to a structured approach where content is organized into a hierarchy (level1, level2, level3). This improves retrieval (returning relevant articles instead of whole files) and reference quality.

**General approach for all parsers:**
1.  **Detect Structure**: Analyze the document to find headings, chapters, sections.
2.  **Assign Levels**: Map detected headings to `level1` (chapter/section), `level2` (article/subsection), `level3` (point/sub-subsection).
3.  **Handle Language**: Use Unicode-aware regex and avoid language-specific stopword lists that might not cover Russian/Belarusian/English equally.

---

### 1. DocxParser Improvements

**Current State:** Treats paragraphs as individual chunks, no structural awareness.

**Proposed Improvements:**
- **Heading Detection via Styles**: Iterate through `document.paragraphs`. Check `paragraph.style.name`. If it starts with 'Heading' (e.g., 'Heading 1', 'Heading 2'), treat it as a structural level.
    - Map 'Heading 1' $\rightarrow$ `level1`
    - Map 'Heading 2' $\rightarrow$ `level2`
    - Map 'Heading 3' $\rightarrow$ `level3`
- **Content Aggregation**: Group subsequent non-heading paragraphs under the last encountered heading.
- **Page Numbers**: Use `python-docx` section properties or approximate based on paragraph runs if absolute accuracy isn't critical for PoC.
- **Regex Fallback**: If no styles are used, use regex to detect patterns like `^Chapter \d+`, `^\d+\.\d+`, etc., supporting Cyrillic characters (`[Ѐ-ӿ]`).

### 2. PDFParser Improvements

**Current State:** Splits by page. No structural awareness. Cannot distinguish between books, articles, and slides.

**Proposed Improvements:**
- **Font Analysis**: Use `pypdf` (or `pdfplumber` for better text extraction) to analyze font sizes and weights.
    - Larger fonts $\rightarrow$ Higher levels (level1).
    - Bold text $\rightarrow$ Potential headings.
- **Layout Analysis**: Use `pdfplumber` to get bounding boxes. Headings are often centered or at the start of a page/column.
- **Slide Detection**: Check for PDF metadata or specific layouts (many images, little text, wide aspect ratio) to identify if a PDF is actually a slide deck. If so, treat it similarly to `PptxParser`.
- **TOC Extraction**: Try to extract the Table of Contents to map sections to pages.
- **Regex for Structure**: Apply similar regex patterns as Docx for headings (e.g., "1. Introduction", "Глава 1").

### 3. PptxParser Improvements

**Current State:** Treats slides as level1, but doesn't look inside slides for further structure.

**Proposed Improvements:**
- **Title Detection**: Identify the "Title" placeholder shape. Use its text as `level1` (Slide title).
- **Content Structure**: Within a slide, shapes are often ordered. Look for bulleted lists or text with larger font sizes to assign `level2` or `level3`.
- **Section Zoom/Grouping**: If the presentation uses sections (available in newer PPTX formats), map them to `level1`.
- **Notes**: Optionally parse slide notes for additional context, though usually not indexed as main content.

### 4. TextParser Improvements

**Current State:** Treats the whole file as one chunk.

**Proposed Improvements:**
- **Markdown/ReStructuredText Detection**: Detect markdown headings (`#`, `##`, `###`) or RST headings (`===`, `---`) to build structure.
- **Indentation/Whitespace**: For plain text, significant indentation or spacing might indicate structure.
- **Regex Patterns**: Look for common academic patterns:
    - `Chapter/Глава \d+`
    - `Article/Статья \d+`
    - Numbered sections (`1.1`, `1.1.1`).
- **Fallback**: If no structure is detected, behave as it currently does (one section).

### 5. New Parser: Markdown (MdParser)

**Requirement:** Support `.md` files.

**Proposed Implementation:**
- Use a library like `markdown` or `mistune` to parse the AST.
- Map `H1` $\rightarrow$ `level1`, `H2` $\rightarrow$ `level2`, `H3` $\rightarrow$ `level3`.
- This is the most straightforward parser to implement given the explicit markup.

### 6. New Parser: ODF (OdtParser)

**Requirement:** Support OpenDocument Text (`.odt`).

**Proposed Implementation:**
- Use `odfpy` or `lxml` to parse the XML structure.
- Look for `<text:h>` (heading) tags with `text:outline-level` attributes to determine structure.

### 7. Distinguishing Document Types (PDF especially)

For PDFs, we need a heuristic to decide if it's a Book, Article, or Slide deck:
- **Slides**: High image-to-text ratio, specific aspect ratio (16:9 or 4:3 detected via MediaBox), large font sizes for titles.
- **Articles/Books**: Continuous text flow, standard page sizes (A4, Letter), presence of a Table of Contents.

**Implementation:**
- Add a method `_detect_pdf_type(artifact)` that returns `"slides"`, `"book"`, or `"article"`.
- In `parse()`, branch the logic based on this type.

### 8. Language Support Notes

- **Regex**: Use `\b` (word boundary) with Unicode flag `re.UNICODE` or `\w` which matches `[a-zA-Z0-9_]` by default. For Cyrillic, use character ranges `[Ѐ-ӿ]` in regex patterns.
- **Libraries**: Ensure `pypdf`, `python-docx`, `python-pptx` handle UTF-8/Unicode correctly (they generally do).
- **Stopwords**: Avoid removing stopwords during parsing; let the chunking/embedding handle semantic meaning.

### 9. Chunking Service Interaction

- The `ChunkingService` currently respects `level1/2/3` and `metadata`.
- Parsers should populate these fields during `parse()`.
- The `ChunkingService` will then split large sections (e.g., a huge Chapter with many sub-articles) into smaller overlapping chunks while preserving the structural metadata.

### 10. Implementation Priority

1.  **DocxParser**: Highest impact, styles are easy to detect.
2.  **PDFParser**: Most complex, start with font-size analysis.
3.  **MdParser**: Easy win, explicit markup.
4.  **PptxParser**: Moderate improvement (slide internal structure).
5.  **TextParser**: Low priority, regex-based.
6.  **OdtParser**: Low priority, fewer users.

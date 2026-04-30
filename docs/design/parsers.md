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

_TODO_

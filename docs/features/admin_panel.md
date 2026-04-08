# Admin Panel (Streamlit)

**Location:** `src/app/chat/test_ui/admin/panel.py`

## Overview

The Admin Panel is a Streamlit-based web UI for managing the **Staff** and **Events** indexes. It provides a user-friendly interface for university staff members to add, edit, view, and delete records without needing to interact with the API directly.

## Features

- **Dual-index management** - Staff and Events in separate tabs
- **Full CRUD operations**:
  - ✨ Create new staff/events with all fields
  - 📋 List all records with search and filtering
  - ✏️ Edit existing records inline
  - 🗑️ Delete records with confirmation
- **Real-time embedding generation** - Vector fields are automatically created when adding/updating text fields
- **Connection validation** - Checks backend health on startup
- **Responsive layout** - Two-column forms and expandable detail cards

## Prerequisites

1. Backend API must be running (default: `http://localhost:8000`)
2. Admin endpoints must be accessible and enabled
3. Embedding service must be available (sentence-transformers model loaded)

## Installation

```bash
# Install dependencies (including streamlit)
uv sync
```

## Usage

### Starting the admin panel:

```bash
# Using the provided script
./scripts/start_admin_panel.sh

# Or manually
export SERVICE_URL=http://localhost:8000
streamlit run src/app/chat/test_ui/admin/panel.py --server.port 8501
```

The panel will be available at `http://localhost:8501`.

### Connecting to a different backend:

Set `SERVICE_URL` environment variable:

```bash
export SERVICE_URL=https://your-backend.example.com
./scripts/start_admin_panel.sh
```

## Interface Overview

### Staff Management Tab (`👥 Staff`)

**Fields:**
- First Name (required)
- Last Name (required)
- Father's Name (optional, patronymic)
- Position (required)
- Room (required, string - e.g., "619a", "A-101")
- Department (required)
- Competences (optional) - skills, subjects taught
- Description (optional) - short biography

**Actions:**
- **Search** - Filter by name/surname (full-text fuzzy)
- **Filter** - By department, position, room
- **Add** - Create new staff member with embedding generation
- **Edit** - Modify existing staff (includes re-embedding if text fields changed)
- **Delete** - Remove staff member

### Events Management Tab (`📅 Events`)

**Fields:**
- Event Name (required)
- Description (required)
- Participant Requirements (optional)
- Start Date (required)
- End Date (required)
- Bonus Amount (optional, numeric)
- Maximum Participants (optional, default 1)

**Actions:**
- **Search** - Filter by event name
- **Date Filter** - Show events within date range
- **Bonus Filter** - Minimum bonus amount
- **Add** - Create event with embeddings
- **Edit** - Modify event (re-embeds text fields if changed)
- **Delete** - Remove event

## API Integration

The panel communicates with the backend via REST API:

- `GET /admin/staff?q=...&department=...&position=...&room=...` - List staff
- `POST /admin/staff/` - Create staff with auto-generated embeddings
- `PATCH /admin/staff/{id}` - Update staff (re-embeds changed text fields)
- `DELETE /admin/staff/{id}` - Delete staff

- `GET /admin/events?q=...&date_from=...&date_to=...&bonus_amount=...` - List events
- `POST /admin/events/` - Create event with auto-generated embeddings
- `PATCH /admin/events/{id}` - Update event (re-embeds changed text fields)
- `DELETE /admin/events/{id}` - Delete event

## Embedding Behavior

- Text fields are embedded **asynchronously** using `sentence-transformers` (BGE-M3, 1024 dims)
- If a text field is **empty**, its vector field is **omitted** (can be added later via re-embedding)
- Embedding happens **server-side** during create/update operations
- The admin panel sends plain text; backend handles vector generation and storage

## Security Notes

⚠️ **The admin endpoints are NOT protected by authentication in the current implementation.**

In production, you should:
- Add `Depends(verify_firebase_token)` to all endpoints
- Implement role-based access control (only admin users allowed)
- Add rate limiting to prevent abuse
- Use HTTPS for production deployments

See the note in `src/app/api/routers/admin/staff.py` line 13-16.

## Troubleshooting

### "Cannot connect to backend"
- Verify the backend API is running at `SERVICE_URL`
- Check that the admin routers are included in the main FastAPI app
- Ensure CORS allows requests from Streamlit's origin (if needed)

### "Failed to add staff" / 400 errors
- Check that all required fields are filled
- Ensure field types are correct (room should be string like "619a", not number)
- Check backend logs for detailed errors

### Embeddings not appearing
- The EmbeddingService uses `sentence-transformers` which downloads ~1.4GB on first use
- First embedding request may take longer while the model loads
- Check that `sentence-transformers` is installed and the model is downloadable

### Search not returning results
- Staff search is a hybrid of BM25 (keyword) and kNN (semantic) over `competences` and `description`
- If you haven't embedded those fields, only keyword search will work
- Try adding some competences/description to improve semantic matching

## Future Improvements

- Add **bulk import** via CSV/Excel upload (like the original staff import)
- Add **export** functionality (CSV/JSON)
- Show embedding status (whether vector fields exist)
- Bulk edit/delete operations
- Pagination for large datasets
- Sorting by columns
- Audit log of changes
- Admin authentication/authorization
- User feedback forms/messages

## See Also

- [Staff Admin API](../api/routers/admin/staff.py)
- [Events Admin API](../api/routers/admin/events.py)
- [Embedding Service](../services/embedding_service.py)
- [Elasticsearch Repository](../repositories/elasticsearch_repository.py)
- [Test UI](../chat/test_ui.md) - Chainlit chat interface for testing agents

# 📊 Database Schema Documentation

## 🧩 Overview
This schema models a chat system with users, chats, messages, and file attachments. It consists of 5 tables:

- users
- chats
- chat_messages
- file_metadata
- chat_context (join table)

---

# 📁 Tables

## 1. users
Stores application users.

| Column        | Type          |Constraints | Description                |
|---------------|---------------|------------|----------------------------|
| id            | serial8       | PK         | Unique user ID             |
| firebase_id   | varchar(28)   |            | Firebase authentication ID |

---

## 2. chats
Represents chat sessions belonging to users.

| Column   | Type   | Constraints         | Description        |
|----------|--------|---------------------|--------------------|
| id       | serial8| PK                  | Unique chat ID     |
| user_id  | int8   | FK → users.id       | Owner of the chat  |

---

## 3. chat_messages
Stores messages within chats.

| Column        | Type        | Constraints         | Description                  |
|---------------|-------------|---------------------|------------------------------|
| id            | serial8     | PK                  | Unique message ID            |
| chat_id       | int8        | FK → chats.id       | Chat this message belongs to |
| message_type  | varchar(5)  |                     | Type (e.g., user/system)     |
| content       | text        |                     | Message content              |

---

## 4. file_metadata
Stores metadata about files uploaded by users.

| Column   | Type            | Constraints         | Description        |
|----------|-----------------|---------------------|--------------------|
| id       | serial8         | PK                  | Unique file ID     |
| user_id  | int8            | FK → users.id       | Owner of the file  |
| path     | varchar(4096)   |                     | File storage path  |

---

## 5. chat_context
Join table linking chats and files (many-to-many).

| Column   | Type | Constraints                     | Description    |
|----------|------|---------------------------------|----------------|
| chat_id  | int8 | PK, FK → chats.id               | Chat reference |
| file_id  | int8 | PK, FK → file_metadata.id       | File reference |

Composite Primary Key: (chat_id, file_id)

---

# 🔗 Relationships

## 1. User → Chats
Type: One-to-Many  
Definition: One user can have multiple chats.

users.id → chats.user_id

---

## 2. Chat → Messages
Type: One-to-Many  
Definition: One chat can contain multiple messages.

chats.id → chat_messages.chat_id

---

## 3. User → Files
Type: One-to-Many  
Definition: One user can own multiple files.

users.id → file_metadata.user_id

---

## 4. Chat ↔ Files (via chat_context)
Type: Many-to-Many  

- A chat can reference multiple files  
- A file can be used in multiple chats  

chats.id ↔ chat_context.chat_id  
file_metadata.id ↔ chat_context.file_id

---

# 🧠 Conceptual Summary

- A user owns:
  - many chats
  - many files

- A chat contains:
  - many messages
  - many files (via chat_context)

- A file:
  - belongs to a user
  - can be linked to multiple chats

---

# 🧭 Entity Relationship Flow

users
 ├── chats
 │    ├── chat_messages
 │    └── chat_context ─── file_metadata
 └── file_metadata

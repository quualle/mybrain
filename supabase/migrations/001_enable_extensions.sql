-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set up full text search
CREATE TEXT SEARCH CONFIGURATION german_custom (COPY = german);
CREATE TEXT SEARCH CONFIGURATION english_custom (COPY = english);
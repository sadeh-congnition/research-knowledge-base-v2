# Real Database Integration Tests

This document describes the comprehensive test suite that verifies API endpoints using real databases (Django, LM Studio, ChromaDB) without any mocking or patching.

## Overview

The test suite ensures that:
- **API endpoints work correctly** with real database interactions
- **LM Studio integration** functions properly for embeddings
- **ChromaDB persistence and deletion** operations work as expected
- **Data consistency** is maintained across all databases
- **No mocking or patching** - tests verify actual behavior

## Prerequisites

### 1. LM Studio
- Start LM Studio with an embedding model
- Ensure it's running on `http://127.0.0.1:1234/v1`
- Recommended model: `unsloth/embeddinggemma-300m-GGUF` or similar

### 2. Django Environment
```bash
# Install dependencies
uv add Django ninja model-bakery pytest chromadb loguru

# Set up environment
export DJANGO_SETTINGS_MODULE=research_tracker.settings
```

### 3. ChromaDB
- ChromaDB directory (`chroma_db/`) should be writable
- Will be created automatically if it doesn't exist

## Test Files

### 1. `core/test_comprehensive_api.py`
Tests all API endpoints with real database interactions:

**API Endpoint Tests:**
- Autocomplete functionality
- Search with real ChromaDB data
- Question CRUD operations with ChromaDB sync
- Project graph API with interconnected data
- Project operations via API

**ChromaDB Browser Tests:**
- List collections and documents
- Delete collections and documents
- Form data handling (HTMX style)

**LM Studio Integration Tests:**
- Node and question embeddings
- Vector search functionality
- Embedding updates after content changes

**Data Consistency Tests:**
- Soft delete removes ChromaDB embeddings
- Data matching between Django and ChromaDB
- Cascade delete effects

### 2. `core/test_views_real_db.py`
Tests all Django views with real database integration:

**View Tests:**
- Project list/detail with node creation
- Node CRUD operations with ChromaDB sync
- Question detail redirects
- Global search with ChromaDB integration
- ChromaDB browser view
- HTMX partial responses
- Error handling for missing data
- Concurrent operations integrity

### 3. `core/tests.py` (Existing)
Original tests that are still valid and run alongside the new comprehensive tests.

## Running Tests

### Quick Start
```bash
# Run all tests
python run_real_db_tests.py

# Run only API tests
python run_real_db_tests.py --type api

# Run only view tests
python run_real_db_tests.py --type views

# Run only existing tests
python run_real_db_tests.py --type existing
```

### Manual Test Execution
```bash
# Run API tests manually
uv run pytest core/test_comprehensive_api.py -v

# Run view tests manually
uv run pytest core/test_views_real_db.py -v

# Run all tests with detailed output
uv run pytest -v --tb=short
```

## Test Coverage

### API Endpoints Tested
- ✅ `GET /api/autocomplete` - Search nodes and questions
- ✅ `GET /api/search/` - Vector search with ChromaDB
- ✅ `POST /api/node/{node_pk}/question` - Create questions
- ✅ `GET /api/question/{question_pk}/edit` - Edit question form
- ✅ `POST /api/question/{question_pk}` - Update questions
- ✅ `DELETE /api/question/{question_pk}` - Delete questions
- ✅ `GET /api/project/{project_pk}/graph` - Project graph data
- ✅ `GET /api/project/{project_pk}/edit` - Edit project
- ✅ `POST /api/project/{project_pk}` - Update project
- ✅ `GET /api/chroma/collections/` - List ChromaDB collections
- ✅ `GET /api/chroma/collections/{name}/documents/` - List documents
- ✅ `DELETE /api/chroma/collections/` - Delete collections
- ✅ `DELETE /api/chroma/collections/{name}/documents/` - Delete documents

### Views Tested
- ✅ Project list, create, delete
- ✅ Project detail with node creation
- ✅ Node CRUD operations
- ✅ Question detail redirects
- ✅ Global search with ChromaDB
- ✅ ChromaDB browser
- ✅ HTMX partial updates
- ✅ Error handling

### Database Operations Verified
- ✅ **Django ORM**: Create, read, update, soft delete
- ✅ **ChromaDB**: Document insertion, querying, deletion
- ✅ **LM Studio**: Text embedding generation
- ✅ **Data Sync**: Django ↔ ChromaDB consistency
- ✅ **Cascade Operations**: Related data handling

## Key Test Features

### No Mocking Policy
All tests use real database connections:
- Real Django database operations
- Real LM Studio API calls for embeddings
- Real ChromaDB document storage and retrieval
- No monkey patching or test doubles

### Data Persistence Verification
Each test verifies that:
1. Data is correctly persisted to Django database
2. Embeddings are created in ChromaDB via LM Studio
3. Updates sync properly between databases
4. Deletions remove data from all systems
5. Soft deletes work correctly

### Error Handling
Tests cover error scenarios:
- Missing or deleted resources
- Invalid data formats
- Network failures (LM Studio)
- Database constraint violations
- HTMX vs regular request handling

## Test Data Management

### Automatic Cleanup
- Test collections in ChromaDB are automatically cleaned up
- Test data in Django uses transaction rollback
- No manual cleanup required

### Test Isolation
- Each test runs in isolation
- ChromaDB collections use unique names (`test_*`)
- Django transactions ensure clean state

## Troubleshooting

### LM Studio Issues
```bash
# Check if LM Studio is running
curl http://127.0.0.1:1234/v1/models

# Should return JSON with model information
```

### ChromaDB Issues
```bash
# Check ChromaDB directory permissions
ls -la chroma_db/

# Clear corrupted ChromaDB data
rm -rf chroma_db/
```

### Test Timeouts
- Increase timeout in `run_real_db_tests.py` if needed
- Some embedding operations can be slow with large models

## Continuous Integration

### GitHub Actions Example
```yaml
name: Real DB Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      lm-studio:
        image: lmstudio/lm-studio
        ports: ["1234:1234"]
    steps:
      - uses: actions/checkout@v3
      - name: Run Real DB Tests
        run: python run_real_db_tests.py
```

## Performance Considerations

### Test Duration
- API tests: ~2-3 minutes
- View tests: ~1-2 minutes
- Total: ~5 minutes (depends on LM Studio speed)

### Resource Usage
- Memory: ~500MB (Django + ChromaDB)
- Disk: ~100MB for test data
- Network: Local LM Studio calls only

## Best Practices

1. **Always run tests before deployment**
2. **Ensure LM Studio is running** before test execution
3. **Monitor test execution time** for performance regression
4. **Check test output** for any database inconsistencies
5. **Run cleanup manually** if tests are interrupted

## Future Enhancements

- Add performance benchmarks
- Include load testing scenarios
- Add database migration testing
- Implement parallel test execution
- Add test result reporting dashboard

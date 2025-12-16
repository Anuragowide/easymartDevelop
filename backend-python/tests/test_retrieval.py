import pytest
from app.modules.retrieval.product_search import ProductSearcher
from app.modules.retrieval.spec_search import SpecSearcher

@pytest.mark.asyncio
class TestRetrieval:
    async def test_product_searcher_initialization(self):
        searcher = ProductSearcher()
        assert searcher.catalog is not None

    async def test_spec_searcher_initialization(self):
        searcher = SpecSearcher()
        assert searcher.catalog is not None

    async def test_product_search_execution(self):
        """Test that search runs without error (even if results are empty)"""
        searcher = ProductSearcher()
        results = await searcher.search("chair", limit=1)
        assert isinstance(results, list)

    async def test_spec_search_execution(self):
        """Test that spec search runs without error"""
        searcher = SpecSearcher()
        results = await searcher.search("dimensions", limit=1)
        assert isinstance(results, list)

"""
Tests for Response and Error Helpers

Tests for Response and Error wrapper classes.
"""

import pytest
from pydantic import BaseModel

from conduit.response import Response, Error
from conduit.response.error import ErrorCode


class SampleModel(BaseModel):
    """Sample Pydantic model for testing."""
    name: str
    value: int


class TestResponse:
    """Tests for Response class."""
    
    def test_wrap_dict(self):
        """Test wrapping a dict."""
        response = Response()
        result = response({"key": "value"})
        
        assert result["success"] is True
        assert result["data"] == {"key": "value"}
    
    def test_wrap_pydantic_model(self):
        """Test wrapping a Pydantic model."""
        response = Response()
        model = SampleModel(name="test", value=42)
        result = response(model)
        
        assert result["success"] is True
        assert result["data"] == {"name": "test", "value": 42}
    
    def test_wrap_with_metadata(self):
        """Test wrapping with metadata."""
        response = Response()
        result = response(
            {"data": "value"},
            metadata={"processed_at": "2024-01-01"}
        )
        
        assert result["success"] is True
        assert result["metadata"] == {"processed_at": "2024-01-01"}
    
    def test_ok_method(self):
        """Test ok() convenience method."""
        response = Response()
        result = response.ok(message="Operation completed")
        
        assert result["success"] is True
        assert result["message"] == "Operation completed"
    
    def test_ok_with_data(self):
        """Test ok() with data."""
        response = Response()
        result = response.ok(data={"id": 123}, message="Created")
        
        assert result["success"] is True
        assert result["data"] == {"id": 123}
        assert result["message"] == "Created"
    
    def test_pagination(self):
        """Test paginated response."""
        response = Response()
        items = [{"id": i} for i in range(10)]
        
        result = response.with_pagination(
            data=items,
            total=100,
            page=1,
            page_size=10
        )
        
        assert result["success"] is True
        assert len(result["data"]) == 10
        assert result["pagination"]["total"] == 100
        assert result["pagination"]["total_pages"] == 10
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is False


class TestError:
    """Tests for Error class."""
    
    def test_simple_error(self):
        """Test creating simple error."""
        error = Error()
        result = error("Something went wrong")
        
        assert result["success"] is False
        assert result["error"] == "Something went wrong"
    
    def test_error_with_code(self):
        """Test error with code."""
        error = Error()
        result = error("Validation failed", code=ErrorCode.VALIDATION)
        
        assert result["success"] is False
        assert result["error"] == "Validation failed"
        assert result["code"] == ErrorCode.VALIDATION
    
    def test_error_with_details(self):
        """Test error with details."""
        error = Error()
        result = error(
            "Multiple errors",
            details={"field1": "error1", "field2": "error2"}
        )
        
        assert result["details"]["field1"] == "error1"
    
    def test_validation_error(self):
        """Test validation error helper."""
        error = Error()
        result = error.validation(
            "Invalid field",
            field="email",
            expected="valid email",
            received="not-an-email"
        )
        
        assert result["success"] is False
        assert result["code"] == ErrorCode.VALIDATION
        assert result["details"]["field"] == "email"
    
    def test_not_found_error(self):
        """Test not found error helper."""
        error = Error()
        result = error.not_found("User", identifier="user123")
        
        assert "not found" in result["error"]
        assert "user123" in result["error"]
    
    def test_permission_denied_error(self):
        """Test permission denied error helper."""
        error = Error()
        result = error.permission_denied("delete_user")
        
        assert result["success"] is False
        assert result["code"] == ErrorCode.PERMISSION_DENIED
        assert "delete_user" in result["error"]
    
    def test_internal_error(self):
        """Test internal error helper."""
        error = Error()
        result = error.internal()
        
        assert result["code"] == ErrorCode.INTERNAL
        assert "Internal server error" in result["error"]
    
    def test_timeout_error(self):
        """Test timeout error helper."""
        error = Error()
        result = error.timeout("database_query")
        
        assert result["code"] == ErrorCode.TIMEOUT
        assert "database_query" in result["error"]
    
    def test_rate_limited_error(self):
        """Test rate limited error helper."""
        error = Error()
        result = error.rate_limited(retry_after=60)
        
        assert result["code"] == ErrorCode.RATE_LIMITED
        assert result["details"]["retry_after"] == 60


class TestErrorCodes:
    """Tests for ErrorCode enum."""
    
    def test_error_code_values(self):
        """Test error code values are in expected ranges."""
        # General errors 1xxx
        assert 1000 <= ErrorCode.UNKNOWN < 2000
        assert 1000 <= ErrorCode.INTERNAL < 2000
        
        # Validation errors 2xxx
        assert 2000 <= ErrorCode.VALIDATION < 3000
        
        # Auth errors 3xxx
        assert 3000 <= ErrorCode.AUTH_REQUIRED < 4000
        
        # RPC errors 4xxx
        assert 4000 <= ErrorCode.METHOD_NOT_FOUND < 5000
        
        # Connection errors 5xxx
        assert 5000 <= ErrorCode.CONNECTION_ERROR < 6000
        
        # Rate limiting 6xxx
        assert 6000 <= ErrorCode.RATE_LIMITED < 7000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

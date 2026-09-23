import pytest
from scorm.validate import safe_relpath

def test_blocks_traversal():
    with pytest.raises(ValueError):
        safe_relpath("../evil.txt")

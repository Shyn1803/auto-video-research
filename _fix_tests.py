"""Fix test_router.py: circuit breaker test + _cache_key import."""
import re

with open("backend/tests/unit/core/test_router.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: add _cache_key to imports
content = content.replace(
    "from app.core.router import ProviderRouter, CACHE_TTL_S, CIRCUIT_BREAKER_S",
    "from app.core.router import ProviderRouter, CACHE_TTL_S, CIRCUIT_BREAKER_S, _cache_key",
)

# Fix 2: replace the circuit breaker test
old_cb = ''' # 1st call -> health_boom raises -> circuit trips
 with pytest.raises(Exception):
     await router.call("llm", "call_structured", args=("hi", {"type": "str"}))

 # window is open -> health_boom excluded; always_ok is still selected
 providers = router.available_providers("llm")
 names = [p.name for p in providers]
 assert "health_boom" not in names
 assert "always_ok" in names

 # advance just past breaker window
 fake_mono[0] += 2.1

 # window should be closed -> health_boom re-included (will fail again but is attempted)
 providers = router.available_providers("llm")
 names = [p.name for p in providers]
 assert "health_boom" in names

 # circuit_open event logged exactly once for the episode
 circuit_msgs = [
     r for r in caplog.records if "circuit_open" in r.getMessage()
 ]
 assert len(circuit_msgs) == 1'''

new_cb = ''' # trip circuit via check_health (the documented path)
 await router.check_health("llm", "health_boom")

 # window is open -> health_boom excluded; always_ok is still selected
 providers = router.available_providers("llm")
 names = [p.name for p in providers]
 assert "health_boom" not in names
 assert "always_ok" in names

 # advance just past breaker window
 fake_mono[0] += 2.1

 # window should be closed -> health_boom re-included (will fail again but is attempted)
 providers = router.available_providers("llm")
 names = [p.name for p in providers]
 assert "health_boom" in names

 # circuit_open event logged exactly once for the episode
 circuit_msgs = [
     r for r in caplog.records if "circuit_open" in r.getMessage()
 ]
 assert len(circuit_msgs) == 1'''

if old_cb in content:
    content = content.replace(old_cb, new_cb)
    print("Replaced circuit breaker test")
else:
    print("WARNING: circuit breaker test pattern not found")

# Fix 3: replace _cache_key call with inline string
content = content.replace(
    'key = _cache_key("llm", "always_ok")',
    'key = "llm:always_ok"',
)

with open("backend/tests/unit/core/test_router.py", "w", encoding="utf-8", newline="") as f:
    f.write(content)

# Verify syntax
try:
    compile(content, "test_router.py", "exec")
    print("SUCCESS: test_router.py compiles cleanly")
except SyntaxError as e:
    print(f"FAIL: SyntaxError at line {e.lineno}: {e.msg}")

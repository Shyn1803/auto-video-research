with open('backend/app/core/router.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Patch 1: make available_providers async
content = content.replace(
    ' def available_providers(self, capability: str, tier: str = "") -> list[ABC]:',
    ' async def available_providers(self, capability: str, tier: str = "") -> list[ABC]:'
)

# Patch 2: add await adapter.available() + circuit breaker trip inside available_providers
old_body = ''' out: list[ABC] = []
 for name in self.get_chain(capability, tier):
     cls = get_adapter_class(capability, name)
     if cls is None:
         continue
     adapter: ABC = cls(ProviderSettings(provider_name=name))
     if not self._paid_allowed(adapter):
         continue
     key = _cache_key(capability, name)
     if self._is_circuit_open(key):
         continue
     out.append(adapter)
 return out'''

new_body = ''' out: list[ABC] = []
 for name in self.get_chain(capability, tier):
     cls = get_adapter_class(capability, name)
     if cls is None:
         continue
     adapter: ABC = cls(ProviderSettings(provider_name=name))
     if not self._paid_allowed(adapter):
         continue
     key = _cache_key(capability, name)
     if self._is_circuit_open(key):
         continue
     try:
         if not await adapter.available():
             continue
     except Exception as exc:
         self._trip_circuit(capability, name, str(exc))
         continue
     out.append(adapter)
 return out'''

assert old_body in content, f"OLD body not found - trying line-by-line instead"
content = content.replace(old_body, new_body)

# Patch 3: add await to available_providers call in call()
content = content.replace(
    '        providers = self.available_providers(capability, tier)',
    '        providers = await self.available_providers(capability, tier)'
)

with open('backend/app/core/router.py', 'w', encoding='utf-8', newline='') as f:
    f.write(content)

try:
    compile(content, 'router.py', 'exec')
    print("SUCCESS: router.py compiles cleanly")
except SyntaxError as e:
    print(f"FAIL: SyntaxError at line {e.lineno}: {e.msg}")
    raise

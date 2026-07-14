with open('backend/app/core/router.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 109 (index 108) is ' async def available_providers...' with 1 space
# Inside class everything uses 1 space. Let's just populate it correctly.

block = [
    ' async def available_providers(self, capability: str, tier: str = "") -> list[ABC]:\n',
    '  out: list[ABC] = []\n',
    '  for name in self.get_chain(capability, tier):\n',
    '   cls = get_adapter_class(capability, name)\n',
    '   if cls is None:\n',
    '    continue\n',
    '   adapter: ABC = cls(ProviderSettings(provider_name=name))\n',
    '   if not self._paid_allowed(adapter):\n',
    '    continue\n',
    '   key = _cache_key(capability, name)\n',
    '   if self._is_circuit_open(key):\n',
    '    continue\n',
    '   try:\n',
    '    ok = await adapter.available()\n',
    '   except Exception as exc:\n',
    '    self._trip_circuit(capability, name, str(exc))\n',
    '    continue\n',
    '   if not ok:\n',
    '    continue\n',
    '   out.append(adapter)\n',
    '  return out\n',
]

new_lines = lines[:108] + block + lines[129:]
with open('backend/app/core/router.py', 'w', encoding='utf-8', newline='') as f:
    f.writelines(new_lines)

try:
    compile(''.join(new_lines), 'router.py', 'exec')
    print("Syntax OK")
except SyntaxError as e:
    print(f"SyntaxError line {e.lineno}: {e.msg}")
    # show context
    for i in range(max(0,e.lineno-3), min(len(new_lines), e.lineno+2)):
        print(f"  {i+1}: {repr(new_lines[i][:80])}")

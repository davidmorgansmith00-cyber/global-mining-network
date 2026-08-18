# Content

This folder will contain validated data-driven content definitions for hardware, research, facilities, events, and related game systems.

For GMN-EC-02, hardware and facility definitions are server-authoritative inputs for effective hashrate:

- `power_throttle_multiplier = 1.0` when `power_consumed <= power_capacity`
- Otherwise, `power_throttle_multiplier = max(0.1, 1.0 - (((power_consumed - power_capacity) / power_capacity) ^ 1.5))`
- `effective_hashrate = base_hashrate × power_throttle_multiplier × clamp(cooling_efficiency, 0.0, 1.0)`

Hardware content should provide:
- `id`
- `name`
- `category`
- `tier`
- `base_hashrate`
- `base_power_consumption`
- `heat_generation`

Facility content should provide:
- `id`
- `name`
- `tier`
- `power_capacity`
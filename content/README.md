# Content

This folder will contain validated data-driven content definitions for hardware, research, facilities, events, and related game systems.

For GMN-EC-01, hardware definitions are server-authoritative inputs for effective hashrate:

`effective_hashrate = base_hashrate × clamp(power_available / power_capacity, 0.0, 1.0) × clamp(cooling_efficiency, 0.0, 1.0)`

Hardware content should provide:
- `id`
- `name`
- `category`
- `tier`
- `base_hashrate`
- `base_power_consumption`
- `heat_generation`
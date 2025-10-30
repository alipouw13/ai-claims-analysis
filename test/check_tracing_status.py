#!/usr/bin/env python3

import sys
import os
sys.path.append('backend')
os.environ['PYTHONPATH'] = 'backend'

try:
    from backend.app.core.observability import observability

    # Get current traces from the observability manager
    print('Checking observability metrics storage after enabling real tracing:')
    print()

    # Check all storage types
    for storage_type in observability.metrics_storage.keys():
        data = observability.metrics_storage[storage_type]
        print(f'{storage_type}: {len(data)} items')
        if data:
            print(f'  Most recent: {data[-1]}')
        print()

    print('OpenTelemetry status:')
    print(f'  Tracer available: {observability.tracer is not None}')
    print(f'  Meter available: {observability.meter is not None}')
    print(f'  Telemetry enabled: {observability.telemetry_enabled}')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
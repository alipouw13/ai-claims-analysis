#!/usr/bin/env python3

import sys
import os
sys.path.append('backend')
os.environ['PYTHONPATH'] = 'backend'

from backend.app.core.observability import observability

# Get current traces from the observability manager
print('Current observability metrics storage:')
print()

# Check request traces
requests = observability.metrics_storage.get('requests', [])
print(f'Stored requests: {len(requests)}')
if requests:
    print('Recent requests:')
    for req in requests[-5:]:
        endpoint = req.get('endpoint', 'unknown endpoint')
        timestamp = req.get('timestamp', 'no timestamp')
        print(f'  - {timestamp}: {endpoint}')

print()

# Check response times (these would show as traces)
response_times = observability.metrics_storage.get('response_times', [])
print(f'Stored response times: {len(response_times)}')
if response_times:
    print('Recent response times:')
    for rt in response_times[-5:]:
        endpoint = rt.get('endpoint', 'unknown')
        duration = rt.get('duration', 0)
        timestamp = rt.get('timestamp', 'no timestamp')
        print(f'  - {timestamp}: {endpoint} - {duration}s')

print()

# Check agent operations
agent_ops = observability.metrics_storage.get('agent_operations', [])
print(f'Stored agent operations: {len(agent_ops)}')
if agent_ops:
    print('Recent agent operations:')
    for op in agent_ops[-5:]:
        agent_type = op.get('agent_type', 'unknown')
        operation = op.get('operation', 'unknown')
        timestamp = op.get('timestamp', 'no timestamp')
        print(f'  - {timestamp}: {agent_type} - {operation}')

print()

# Check Azure AI Foundry operations
foundry_ops = observability.metrics_storage.get('azure_ai_foundry_operations', [])
print(f'Stored foundry operations: {len(foundry_ops)}')
if foundry_ops:
    print('Recent foundry operations:')
    for op in foundry_ops[-5:]:
        operation_type = op.get('operation_type', 'unknown')
        timestamp = op.get('timestamp', 'no timestamp')
        print(f'  - {timestamp}: {operation_type}')

print()

# Check for any other trace-like data
errors = observability.metrics_storage.get('errors', [])
print(f'Stored errors: {len(errors)}')
if errors:
    print('Recent errors:')
    for err in errors[-3:]:
        error_type = err.get('error_type', 'unknown')
        endpoint = err.get('endpoint', 'unknown')
        timestamp = err.get('timestamp', 'no timestamp')
        print(f'  - {timestamp}: {error_type} - {endpoint}')
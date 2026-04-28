from pipeline import generate_pipeline
import json

TRIALS = 10
results = []

# Use single difficulty to reduce LLM calls and speed up experiments
TEST_SPECS = ["easy"]

for i in range(TRIALS):
    print(f"Run {i+1}/{TRIALS}...", flush=True)
    res = generate_pipeline(specs=TEST_SPECS, questions_per_spec=1)
    results.append(res)
    # Save intermediate progress so partial results aren't lost
    with open('experiment_results_partial.json', 'w', encoding='utf-8') as pf:
        json.dump({'completed': i+1, 'results': results}, pf, ensure_ascii=False, indent=2)

# Aggregate
total_generated = sum(r.get('generated', 0) for r in results)
total_valid = sum(r.get('valid', 0) for r in results)
total_failed = sum(r.get('failed', 0) for r in results)

print('\n=== Summary ===')
print(f'Trials: {TRIALS}')
print(f'Total generated: {total_generated}')
print(f'Total valid: {total_valid}')
print(f'Total failed: {total_failed}')
valid_rate = (total_valid / total_generated) if total_generated > 0 else 0.0
print(f'Valid rate (valid/generated): {valid_rate:.2%}')

with open('experiment_results.json', 'w', encoding='utf-8') as f:
    json.dump({'trials': TRIALS, 'results': results, 'summary': {
        'total_generated': total_generated,
        'total_valid': total_valid,
        'total_failed': total_failed,
        'valid_rate': valid_rate,
    }}, f, ensure_ascii=False, indent=2)

print('\nWrote experiment_results.json')

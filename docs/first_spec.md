First Spec
---

# Goal

Create a cli using [typer](https://typer.tiangolo.com/) to slice an audio using [PyAV](https://pypi.org/project/av/) following the rules defined bellow.

- Only `uv` to add dependencies and run scripts
- Use `pydantic` to manage data structures
- Check types with `ruff`
- Create tests at `tests`
	- Test with `a_ia_ta_ai-1min.yaml` (using `default_rule.yaml`) and `samples_agro1.yaml` (using `samples_agro1.yaml`)
- 

Input:
- `audio_name:str` (the audio MUST be at `samples`)
- `chunks_dirname:Path|str`: Chunks dir name (default: same as `audio_name`)
- `chunks_rules_yaml:Path` (default: `default_rule.yaml`)
- `sampling_rule: [Random|Continuous]` (default: Random)

```python
import pydantic
class ChunksRule(pydantic.BaseModel):
	chunk_size_seconds: int
	amount: int = -1
		# -1: Means slice all audio, i.e. range(0,duration,chunks_size_seconds)
		# i > 0: i chunks
	remove_seconds: Optional[list[tuple]]
		# Range tuple(start,end) of seconds that must be removed.
		# E.g. [(0,10)], the sampling must start of the second 10.
```

```yaml
# default_rule.yaml
version: 1
chunks:
  - chunk_size_seconds: 2
    amount: -1
  - chunk_size_seconds: 10
    amount: -1
  - chunk_size_seconds: 30
    amount: -1
```

Sampling Rules:
- `Random`: can be sampled from anywhere as long as each chunk be disjoint of every other chunk. E.g. if the i-th chunk of 10 seconds covers the second 20 to 30, none of the restants of 10 seconds can cover this interval. `amount=-1` and `Random` are mutually exclusive.
- `Continuous`: the chunks must be in order. Be aware of the `remove_seconds` condition.

# Constrains
- Before sampling, check if the conditions can be satisfied.
- The name of each chunk must be: `f'{start_seconds}-{end_seconds}.wav'`

# Output of `config.yaml`:

```yaml
# samples_agro1.yaml
version: 1
chunks:
  - chunk_size_seconds: 10
    amount: 2
  - chunk_size_seconds: 20
    amount: 2
```

```
.
└── samples/
    ├── samples_agro1/
    │   ├── 10/
    │   │   ├── 20-30.wav
    │   │   └── 2382-2392.wav
    │   └── 20/
    │       ├── 25-45.wav
    │       └── 2372-2392.wav
    └── samples_agro1.wav
```


# CoreMark-Pro

Wrapper for [CoreMark-Pro](https://github.com/eembc/coremark-pro) which is a CPU benchmarking tool that provides a single number score for easy comparison across runs.

## Overview of Operations

- A path to where CoreMark-Pro has been cloned is provided to benchmark-wrapper since there is no install
mechanism.
- Executing the benchmark is done with `make` and also compiles the benchmark if not already done.
- A log folder is created from the exection, where only the `.log` and `.mark` file are processed:

  ```
  coremark-pro/builds/linux64/gcc64/logs
  ├── linux64.gcc64.log       # Raw logs of the CoreMark Pro run
  ├── linux64.gcc64.mark      # Results: both individual workloads and overall score
  ├── progress.log
  ├── zip-test.run.log
  └── zip-test.size.log
  ```
- The results are ingested into two different Elasticsarch indexes:
    - `*-coremark-pro-summary`: Results from the `.mark` file. Provides the calculated results from CoreMark-Pro.
    - `*-coremark-pro-raw`: Raw logs from the `.log` file. Intended for analyzing the logs manually.

## Arguments

### Required

- `-p` / `--path` Directory where CoreMark Pro is located.

### Optional

- `-c` / `--context`: CoreMark Pro's context argument. Defaults to `0`.
- `-w` / `--workload`: CoreMark Pro's workload argument. Defaults to `1`.
- `-s` / `--sample`: Number of samples to run. Defaults to `1`.
- `-r` / `--result-name`: The name of CoreMark Pro's result files. This includes the path relative to `--path` and does not include the extenstion. This only needs to be changed if not running on Linux 64bit. Defaults to `builds/linux64/gcc64/logs/linux64.gcc64`
- `-u` / `--upload`: Parses existing results in a CoreMark-Pro log directory. No support for multiple samples and `sample_starttime` is based on when benchmark-wrapper is run. Mainly used for debugging.


### Example

## Container

## Parsing

This section gives a general idea of how CoreMark-Pro output matches with the Elasticsearch fields.

### Results

These results are calculated by CoreMark-Pro and read from the `*.mark` file. Each row of the table is
ingested as its own record.

#### Example `.mark` file

```
WORKLOAD RESULTS TABLE

                                                 MultiCore SingleCore
Workload Name                                     (iter/s)   (iter/s)    Scaling
----------------------------------------------- ---------- ---------- ----------
cjpeg-rose7-preset                                  178.57     192.31       0.93
....

MARK RESULTS TABLE

Mark Name                                        MultiCore SingleCore    Scaling
----------------------------------------------- ---------- ---------- ----------
CoreMark-PRO                                       5708.35    5714.89       1.00
```

#### Elasticsearch output

```
{
    "_source": {
        "test_config": {
            "workload": 0,                   # `--workload`
            "context": 1                     # `--context`
        },
        "sample_starttime": "2021-10.1..",   # Time when benchmark-wrapper was executed.
        "sample": 1,                         # `--sample`
        "name": "CoreMark-PRO",              # Name of the CoreMark-Pro workload
        "multicore": 5708.35,                 # Multi Core result
        "singlecore": 5714.89,             # Single Core result
        "scaling": 1.00,                     # Scaling result
        "type": "mark",                      # Type of result, determined by the table header
                                             # - `workload`: Data from 'Workload Results Table'
                                             # - `mark`: Data from 'Mark Results Table'
        "cluster_name": "laptop",
        "user": "ed",
        "uuid": "3cc2e4a9-bd7f-4394-8d8c-66415ceeb02f",
        "workload": "coremark-pro",
        "run_id": "NA"
    },
}
```

### Raw logs

These are the raw logs parsed from the `.log` file. The median results are dropped since they can be derived using Elasticsearch.


#### Excerpt of a log file

```
#UID            Suite Name                                     Ctx Wrk Fails       t(s)       Iter     Iter/s  Codesize   Datasize
#Results for verification run started at 21285:10:58:22 XCMD=-c1 -w0
236760500         MLT cjpeg-rose7-preset                         1   1     0      0.010          1     100.00    105616     267544
#Results for performance runs started at 21285:10:58:23 XCMD=-c1 -w0
236760500         MLT cjpeg-rose7-preset                         1   1     0      0.081         10     123.46    105616     267544
```

#### Elasticsearch output

Overall the conversion is self explanatory, the fields are taken from the headings. CoreMark-Pro performs two sets of runs for each workload that are marked by the same `uid`.  Each set of runs has a single verification run and three performance runs. These sets of runs are marked by the same `uid`. A `run_index` field was added to ensure performance runs with the same results are not marked as duplicates.

```
{
    "_source": {
        "test_config": {
            "workload": 0,
            "context": 1
        },
        "sample_starttime": "2021-10.1..",   # Time when benchmark-wrapper was executed.
        "sample": 1,
        "uid": "236760500",           # A UID generated per workload by CoreMark-Pro
        "suite": "MLT",
        "name": "cjpeg-rose7-preset",
        "ctx": 1,
        "wrk": 1,
        "fails": 0,
        "t(s)": 0.01,
        "iter": 1,
        "iter/s": 100.0,
        "codesize": 105616,
        "datasize": 267544,
        "type": "verification",       # Possible types: verification / performance
        "starttime": "2021-10....",   # The start time for the runs as recorded by CoreMark Pro
        "run_index": 0,               # An index of how many runs of the same type. Always
                                      # 0 for verification, between 0-2 for performance runs.
        "cluster_name": "laptop",
        "user": "ed",
        "uuid": "816f7fe9-ab04-45a4-8a1f-ce61c2fe11e6",
        "workload": "coremark-pro",
        "run_id": "NA"
    },
}
```
## Limitations

- Limited ability to visualize the data from `*-coremark-pro-raw`, requires additional fields to aggregate the runs.


## Dockerfile

The Dockerfile has CoreMark-Pro pre-built and is located at `/coremark/`.
